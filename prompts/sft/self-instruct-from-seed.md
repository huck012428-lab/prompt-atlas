---
id: sft/self-instruct-from-seed
title: Self-Instruct — Generate New Instructions from a Seed Bank
version: 0.1.0
status: stable
direction: sft
tags: [instruction-tuning, seed-expansion, generation, data-augmentation, structured-output]
audience: [sft-team, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: seed_instructions
    description: A JSON array of 5 to 10 hand-curated example instructions in the same task family.
    required: true
  - name: task_family_description
    description: One-paragraph description of the task family the seeds represent (e.g. text classification, multi-step QA, code generation). Pass empty string if implicit from seeds.
    required: false
  - name: n_new_instructions
    description: How many new instructions to generate this batch (small integer, typically 3 to 8).
    required: true
---

> 🎯 **场景**：Self-Instruct 技术——从 5-10 条种子指令出发生成同 task family 的**新**指令（不是改写）。SFT 数据从手工种子规模化的横向维度，和 variant-expander 互补。

## Quick Use

**Use when:** You have a small bank of seed instructions and want to generate NEW instructions in the same task family (Self-Instruct technique).
**Fill in:** `{{seed_instructions}}` = JSON array of 5-10 seed examples; `{{task_family_description}}` = optional one-line description; `{{n_new_instructions}}` = how many new ones to generate.
**You'll get:** A list of new instructions each with task-family fit, diversity axes, and a novelty check. Output is JSON.

## Purpose

Generate new, diverse instructions in the same task family as a small
hand-curated seed bank — the Self-Instruct technique. Used to scale a
high-quality seed set (50-200 instructions) into a large SFT instruction
pool (thousands), without the variants being mere rewrites of the
seeds. Distinct from `sft/instruction-variant-expander`: that card
**rephrases one seed**; this card **invents new instructions** in the
seeds' task family. Output is structured so each new instruction can be
filtered for quality before paired with a response.

## Prompt

```text
You generate new instructions in the same task family as a set of seed
examples. Goal: produce diverse, novel instructions that a downstream
SFT pipeline can pair with a response.

Seed instructions:
{{seed_instructions}}

Task family description (may be empty; if so, infer from seeds):
{{task_family_description}}

Generate {{n_new_instructions}} new instructions.

Rules:
1. Each new instruction must belong to the same task family as the seeds
   (the same kind of work, not a different task type).
2. Each new instruction must be NEW — not a rewrite of any seed and not
   a near-duplicate of another newly generated instruction.
3. Vary along at least two of: domain / topic, level of specificity,
   register (formal/casual/terse), length of expected response,
   complexity (single-step vs multi-step).
4. Each instruction must be self-contained and answerable on its own
   without external context that the seeds did not require.
5. Do NOT generate instructions that violate docs/SAFETY.md (no harm
   enabling, no PII, no jailbreak prompts).
6. If the task family is too narrow to support {{n_new_instructions}}
   distinct new instructions without near-duplication, return fewer
   and set "saturated": true.

Return ONLY this JSON object:
{
  "new_instructions": [
    {
      "text": "<the new instruction>",
      "task_family_match": "<one short phrase: how this fits the family>",
      "diversity_axes": ["<axis 1>", "<axis 2>"],
      "novelty_check": "<one short phrase asserting why this is not a duplicate of any seed or other new instruction>"
    }
    /* ... up to {{n_new_instructions}} entries */
  ],
  "saturated": true | false,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
seed_instructions: [
  "Classify the sentiment of the following customer review as positive, negative, or neutral.",
  "Identify whether this email is a phishing attempt or legitimate; explain in one sentence.",
  "Categorize the following news headline into one of: politics, sports, technology, entertainment, business."
]
task_family_description: "Single-input short-text classification with a fixed label set."
n_new_instructions: 3
```

**Expected output:**

```json
{
  "new_instructions": [
    {
      "text": "Determine whether the following code snippet is in Python, JavaScript, or Rust.",
      "task_family_match": "Single-input classification over a fixed label set.",
      "diversity_axes": ["domain: code", "label set size: 3"],
      "novelty_check": "No seed targets code-language identification; differs from sentiment, phishing, news classification."
    },
    {
      "text": "Categorize the following research paper abstract as primarily theoretical, empirical, or survey work, in one word.",
      "task_family_match": "Short-text classification with a fixed three-way label set.",
      "diversity_axes": ["domain: academic", "register: formal"],
      "novelty_check": "No seed addresses paper-type classification; specifies one-word output unlike news headline categorization."
    },
    {
      "text": "Decide whether this support ticket should be routed to billing, technical, or account-management; respond with the team name only.",
      "task_family_match": "Short-text classification used for routing decisions.",
      "diversity_axes": ["domain: support ops", "complexity: routing decision"],
      "novelty_check": "Routing classification differs from sentiment/phishing/news labeling; output convention differs from seeds."
    }
  ],
  "saturated": false,
  "decision_basis": "Three new classifications across distinct domains, each with explicit fixed label set."
}
```

## Failure Modes

- **Family drift** — model produces instructions that look new but
  actually belong to a different task family (e.g. seeds are
  classification; output is summarization). Detect by sampling and
  asking a verifier "is this the same task family as the seeds?";
  drop or re-prompt drifters.
- **Pseudo-novelty** — model swaps surface vocabulary while keeping
  semantic content (sentiment classification → "emotion classification"
  = the same thing). Detect with cheap surface metrics (BLEU / Jaccard
  overlap with seeds and within batch); reject batches with mean
  similarity > 0.8 to existing instructions.
- **Domain monoculture** — all 5 new instructions are in the same
  domain (e.g. all about email). The diversity_axes field is meant
  to surface this; check that domain appears in `diversity_axes` for
  most outputs and that domains differ across the batch.
- **Difficulty drift** — new instructions are systematically easier or
  harder than the seeds. Track average response length / token-level
  complexity and adjust prompt if it drifts.
- **Safety regression** — model invents instructions that probe harm
  (e.g. seeds are benign classifications; output asks to classify
  whether content "should be censored"). Mitigation: rule 5 explicit;
  pass outputs through `eval/safety-output-classifier` before SFT.
- **Saturation under-reporting** — model claims `saturated: false`
  while producing near-duplicates. If duplicate rate is high, force
  `saturated: true` regardless and reduce batch size.

## Tuning Notes

- 模型差异：必须 frontier 模型。Self-instruct 的 diversity 和 novelty
  对模型的 instruction-following + creativity 同时要求高；中档模型
  会快速进入"换标点"或同义词替换模式。
- 温度：`0.7`–`1.0`（多样性优先），后续用 verifier 过滤。
- 种子规模：seed_instructions 建议 5-10 条，每条覆盖一个 sub-family
  的代表样本。少于 5 条会让模型 mode collapse 到第一条；多于 10 条
  浪费 context。
- 与 `sft/instruction-variant-expander` 的关系：variant-expander 把
  1 个 seed 扩成 N 个改写（同任务，不同表面）；本卡把 5-10 个 seeds
  扩成 N 个新任务实例（同 family，不同任务）。两者通常串联使用：
  先 self-instruct 横向扩，再 variant-expander 纵向扩。
- 与 `sft/data-quality-filter` 的关系：本卡产出是 instructions only；
  接下来需要 (1) 用一个 response generator 给每条 instruction 生成
  response，(2) 用 data-quality-filter 过滤 (instruction, response)
  对。本卡产出未过滤前不要直接进入 SFT 训练。
- 安全审计：自动生成 instructions 偶尔会越界；上线前用至少 200
  样本的 manual spot-check + safety-output-classifier 跑一遍。
- 多样性度量：在 batch 完成后对所有 (seed + new) instructions 计算
  pairwise embedding similarity；保留 mean cosine < 0.8 的 batch，
  其余 re-generate。

## Changelog

- `0.1.0` — Initial card.
