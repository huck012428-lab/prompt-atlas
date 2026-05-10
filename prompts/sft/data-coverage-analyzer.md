---
id: sft/data-coverage-analyzer
title: SFT Data Coverage Analyzer
version: 0.1.0
status: experimental
direction: sft
tags: [classification, scoring, structured-output, instruction-tuning]
audience: [sft-team, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: dataset_sample
    description: A JSON array of (instruction, response) pairs from the SFT dataset — typically 50-500 representative samples (you don't need the whole dataset).
    required: true
  - name: target_taxonomy
    description: Optional — a JSON array of topic / skill categories the dataset is supposed to cover (e.g. ["math", "code", "writing", "reasoning", "factual_qa"]). Pass empty array for the model to infer the natural taxonomy from the data.
    required: false
---

> 🎯 **场景**：分析一个 SFT 数据集的覆盖度——按 topic / skill 分类样本，发现"过度集中""完全缺失""分布失衡"等问题。本卡是看"数据缺什么"的工具，配合 self-instruct / variant-expander 补缺。

## Quick Use

**Use when:** You have an SFT dataset (or a sample of it) and want to know whether it covers the topics / skills it's supposed to, or whether it's lopsided.
**Fill in:** `{{dataset_sample}}` = JSON array of (instruction, response) samples; `{{target_taxonomy}}` = optional list of expected categories.
**You'll get:** Per-category counts and percentages, gaps (categories with too few examples), over-represented categories, and suggestions for what to generate to balance. Output is JSON.

## Purpose

Diagnose coverage of an SFT dataset. Categorizes each sample
into a topic / skill bucket, identifies gaps and over-representations,
and suggests what kinds of additional data would balance the set.
Used before training to ensure the dataset matches the target model's
intended capabilities. Output is structured so the gaps can feed
directly into `sft/self-instruct-from-seed` to generate the missing
categories.

## Prompt

```text
You analyze an SFT dataset's coverage and identify gaps.

Dataset sample:
{{dataset_sample}}

Target taxonomy (may be empty — if empty, infer the natural
categories from the sample):
{{target_taxonomy}}

Steps:
1. If target_taxonomy is provided, use those categories. If empty,
   infer 5-10 natural categories from the sample.

2. Classify each sample into one or more categories. Capture
   counts.

3. For each category:
   - count: how many samples
   - share: percentage of total
   - difficulty_distribution: best estimate of "easy / medium /
     hard" within that category
   - representative_example: one short instruction snippet
     representing the category

4. Identify "gaps": categories in target_taxonomy with <5% share
   (or, if no taxonomy, categories with <2 samples that should
   plausibly exist given the others).

5. Identify "over_represented": categories with >35% share.

6. For each gap, suggest: what kind of seed instructions should be
   created to fill it (this can feed into self-instruct).

Return ONLY this JSON object:
{
  "categories": [
    {
      "name": "<category>",
      "count": <integer>,
      "share_percent": <float>,
      "difficulty_distribution": {"easy": <integer>, "medium": <integer>, "hard": <integer>},
      "representative_example": "<short instruction snippet>"
    }
  ],
  "total_samples_analyzed": <integer>,
  "gaps": [
    {"category": "<name>", "current_share": <float>, "target_share": <float>, "fill_suggestion": "<short>"}
  ],
  "over_represented": [
    {"category": "<name>", "current_share": <float>, "concern": "<why this is too much>"}
  ],
  "balance_score": <float 0-1; 1 = perfectly balanced; closer to 0 = severely lopsided>,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
dataset_sample: <100 (instruction, response) pairs>
target_taxonomy: ["math", "code", "writing", "reasoning", "factual_qa"]
```

**Expected output:**

```json
{
  "categories": [
    {"name": "factual_qa", "count": 52, "share_percent": 52.0, "difficulty_distribution": {"easy": 30, "medium": 18, "hard": 4}, "representative_example": "What is the capital of Brazil?"},
    {"name": "writing", "count": 28, "share_percent": 28.0, "difficulty_distribution": {"easy": 12, "medium": 14, "hard": 2}, "representative_example": "Write a short cover letter for..."},
    {"name": "code", "count": 12, "share_percent": 12.0, "difficulty_distribution": {"easy": 8, "medium": 3, "hard": 1}, "representative_example": "Write a Python function that..."},
    {"name": "reasoning", "count": 5, "share_percent": 5.0, "difficulty_distribution": {"easy": 3, "medium": 2, "hard": 0}, "representative_example": "If X then Y; given Y, what about X?"},
    {"name": "math", "count": 3, "share_percent": 3.0, "difficulty_distribution": {"easy": 3, "medium": 0, "hard": 0}, "representative_example": "What is 12 * 7?"}
  ],
  "total_samples_analyzed": 100,
  "gaps": [
    {"category": "math", "current_share": 3.0, "target_share": 20.0, "fill_suggestion": "Add medium and hard math problems (word problems, multi-step calculations) — current 3 samples are all trivial arithmetic."},
    {"category": "reasoning", "current_share": 5.0, "target_share": 20.0, "fill_suggestion": "Add structured reasoning problems (multi-hop deductions, causal chains, logic puzzles)."}
  ],
  "over_represented": [
    {"category": "factual_qa", "current_share": 52.0, "concern": "Over half the dataset is factual QA, mostly easy. Model will be optimized for trivia at the expense of reasoning / problem-solving."}
  ],
  "balance_score": 0.45,
  "decision_basis": "Dataset is 80% factual_qa + writing, with math and reasoning critically under-represented; balance_score 0.45 reflects significant skew."
}
```

## Failure Modes

- **Sample size too small** — analyzing 10 samples when 100+ are
  needed for statistical estimates. The card returns answers
  regardless; track total_samples_analyzed and warn callers if it's
  too low for confidence.
- **Categorization noise** — same kind of instruction labeled
  differently across samples. Track category count distribution; if
  one category is suspiciously specific, the model may be
  splitting unnecessarily.
- **Hallucinated counts** — total_samples_analyzed doesn't match the
  input array length. Validate at parse time.
- **Difficulty estimation drift** — "hard" applied to easy problems
  or vice versa. Without ground truth this is hard to verify; spot-
  check the representative_example in each category.
- **Target taxonomy ignored** — when taxonomy is provided, model
  uses its own anyway. Verify category names match input taxonomy
  (case-insensitive).

## Tuning Notes

- 模型差异：frontier 模型必须的——分析需要稳定的分类 + 估计能力。
  中档模型在 difficulty estimation 上不可靠。
- 温度：`0.0`。
- sample 大小：50-500 是甜点。<50 不够统计；>500 prompt 太长且收益
  递减。**采样**而不是全量分析（用代表性 sample，不要硬塞整个数据集）。
- 与 `sft/self-instruct-from-seed` 的关系：本卡识别 gap，那张卡填
  gap。pipeline：分析覆盖 → 找到 gap → self-instruct 生成对应类
  指令 → 用 response-generator 生成 response → 入数据集。
- 与 `sft/data-quality-filter` 的关系：filter 是逐对评估质量；本卡是
  数据集级评估覆盖。前者每对一次，后者每数据集一次。互补不重叠。
- 与 `sft/instruction-difficulty-classifier` 的关系：本卡产出含
  difficulty_distribution；那张卡是更精细的 per-instruction 难度分类。
  本卡用作 high-level 判断；instruction-difficulty-classifier 用作
  curriculum training data 排序。
- balance_score 的解读：>0.7 算 balanced；0.5-0.7 mild skew；<0.5
  严重 skew 应当采取行动。这是 heuristic，不是统计指标。

## Changelog

- `0.1.0` — Initial card.
