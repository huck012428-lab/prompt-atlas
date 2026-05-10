---
id: sft/data-quality-filter
title: SFT Data Quality Filter
version: 0.1.0
status: stable
direction: sft
tags: [instruction-tuning, scoring, classification, structured-output, safety]
audience: [sft-team, llm-trainer, eval-team]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: instruction
    description: The instruction half of an SFT pair (what was asked).
    required: true
  - name: response
    description: The response half of an SFT pair (the candidate training target).
    required: true
  - name: domain_hint
    description: Optional one-line hint about the domain (e.g. medical Q&A, code generation, customer support). Pass empty string if not applicable.
    required: false
---

## Quick Use

**Use when:** You have candidate (instruction, response) SFT pairs and want to filter them by quality before training.
**Fill in:** `{{instruction}}` = the instruction; `{{response}}` = the candidate response; `{{domain_hint}}` = optional one-line domain hint.
**You'll get:** Per-dimension scores (clarity, correctness, completeness, style, safety) and a keep / review / drop verdict. Output is JSON.

## Purpose

Score a candidate (instruction, response) SFT pair on five quality
dimensions and decide whether to KEEP it for training, REVIEW it
(borderline), or DROP it. Used as the final-stage filter in an SFT
data pipeline before training, and as an audit tool on existing
training sets to find low-quality samples that may be hurting the
model. Output is structured so dataset-level pass rates and per-
dimension fail rates can be tracked over time.

This card is the **filtering counterpart** to
`sft/self-instruct-from-seed` and `sft/instruction-variant-expander`,
which generate candidate pairs but do not assess them.

## Prompt

```text
You are a data quality filter for SFT training pairs. Score the pair
on five dimensions and decide whether it should be kept, sent to
review, or dropped.

Instruction:
{{instruction}}

Response:
{{response}}

Domain hint (optional):
{{domain_hint}}

Score each dimension on a 1-5 scale:
- instruction_clarity     : Is the instruction unambiguous, well-formed,
                            and answerable as-is? Penalize malformed,
                            contradictory, or context-dependent
                            instructions.
- response_correctness    : Is the response factually correct and
                            substantively right? Penalize wrong facts,
                            wrong format if the instruction specified
                            one, and contradictions.
- response_completeness   : Does the response fully address the
                            instruction? Penalize partial answers and
                            placeholder text.
- response_style_quality  : Is the response well-written and at the
                            register implied by the instruction? Not
                            a separate factuality check.
- safety_compliance       : Is the pair free of harmful content
                            (instruction asking for harm, response
                            providing harm)? See docs/SAFETY.md for the
                            policy. Score 1 if either side is
                            problematic; score 5 by default for
                            benign content.

Decision rules:
- "keep"   — every dimension >= 4 AND safety_compliance == 5.
- "drop"   — safety_compliance < 5, OR any dimension == 1, OR three
             or more dimensions <= 2.
- "review" — anything else (borderline; route to human spot-check).

Return ONLY this JSON object:
{
  "scores": {
    "instruction_clarity":   1-5,
    "response_correctness":  1-5,
    "response_completeness": 1-5,
    "response_style_quality":1-5,
    "safety_compliance":     1-5
  },
  "decision": "keep" | "review" | "drop",
  "primary_issue": "<for review/drop: the lowest-scoring dimension and a one-phrase reason; empty string for keep>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
instruction: "Translate the following Python code to JavaScript."
response: "Here's the JavaScript version: function add(a, b) { return a + b; }"
domain_hint: "code generation"
```

**Expected output:**

```json
{
  "scores": {
    "instruction_clarity": 2,
    "response_correctness": 3,
    "response_completeness": 2,
    "response_style_quality": 4,
    "safety_compliance": 5
  },
  "decision": "review",
  "primary_issue": "instruction_clarity: instruction references code that was not provided; response is plausible but unverifiable.",
  "decision_basis": "Instruction is malformed (missing the code to translate); response is reasonable in form but cannot be assessed for correctness."
}
```

## Failure Modes

- **Surface-quality bias** — judge marks well-formatted responses as
  high quality even when the response is factually wrong. Mitigation:
  the rubric separates `response_correctness` from
  `response_style_quality`; verify in audits that they vary
  independently across a sample.
- **Length bias** — longer responses score higher on completeness
  regardless of substance. Track length-controlled completeness
  distribution; if it correlates >0.7 with token length, the filter
  is rewarding verbosity.
- **Domain miscalibration** — without `domain_hint`, judge applies
  general-knowledge thresholds to specialist content (medicine, law,
  niche code) and either drops too much or keeps too much. Pass a
  domain_hint when applicable.
- **Safety over-trigger** — judge marks legitimate informational
  content as `safety_compliance: 1` because the topic is sensitive
  (e.g. mental health resources). Calibrate against a known-safe
  baseline of informational responses.
- **Safety under-trigger** — judge misses subtle harm (e.g. a
  response that gives "general" advice with operational specifics
  embedded). Mitigation: chain with `eval/safety-output-classifier`
  for high-stakes filtering instead of relying solely on
  safety_compliance from this card.
- **Score compression** — most pairs get 3-4 across the board.
  Expected for SFT data (most synthetic pairs are mediocre); but if
  the keep rate is implausibly high (>40% on synthetic data), the
  filter is too lenient.

## Tuning Notes

- 模型差异：本卡对 judgment quality 高度敏感；推荐 frontier 模型。
  中档模型在 correctness 和 completeness 区分上不稳定；可降级为
  3 分制（good / mediocre / bad）以提升一致性。
- 温度：`0.0`，filter 必须可重现。
- 调用预算：filter 在 SFT pipeline 中通常是单次调用（每对一次）；
  对每对跑两遍取一致 keep 决定可降低误删高质量样本，代价是 2x
  成本。
- 与 `eval/llm-judge-rubric-open-ended` 的关系：rubric 卡是给
  outputs 打报告分（用于 dashboard / leaderboard）；本卡是 filter
  决策（keep / review / drop）。维度集合和决策语义都不同，**不要
  混用**。
- 与 `eval/safety-output-classifier` 的关系：safety-output-classifier
  更细致（分类到 harm taxonomy），适合高敏数据；本卡的
  safety_compliance 是 first-pass 粗滤。生产中可以串联：先用本卡
  快速 filter，再用 safety-output-classifier 复审 keep 集合。
- 与 `sft/self-instruct-from-seed` 和 `sft/instruction-variant-expander`
  的关系：那两张卡是生成端，本卡是过滤端。生成 → response 生成 →
  本卡过滤是标准 SFT 数据 pipeline 的三步走。
- 数据集级监控：维护 keep / review / drop 的滚动比例；比例剧烈漂移
  通常提示生成端 (self-instruct / variant-expander) 出问题，不是
  filter 出问题。
- 不要让本卡作为唯一筛选器。建议保留 5-10% 的 keep 样本送人工
  采样审核，作为 filter 自身质量的 calibration。

## Changelog

- `0.1.0` — Initial card.
