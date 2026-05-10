---
id: sft/response-generator
title: SFT Response Generator (instruction → high-quality response)
version: 0.1.0
status: stable
direction: sft
tags: [instruction-tuning, generation, structured-output]
audience: [sft-team, llm-trainer]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: instruction
    description: The instruction that needs a high-quality response.
    required: true
  - name: style_constraints
    description: A short description of the response style — register, length range, format requirements, refusal posture. Pass empty string for general default.
    required: false
  - name: domain_hint
    description: One-line domain hint to help calibrate (e.g. customer support, code generation, medical Q&A). Pass empty string if not applicable.
    required: false
---

## Quick Use

**Use when:** You need to produce the response half of an SFT pair given an instruction.
**Fill in:** `{{instruction}}` = what to respond to; `{{style_constraints}}` = optional style description; `{{domain_hint}}` = optional domain hint.
**You'll get:** The response text plus a `would_refuse` safety flag and a self_assessment of quality / factual risk / length. Output is JSON containing the response_text field.

## Purpose

Produce a high-quality response to a single instruction, intended as
the **target half of an SFT training pair**. The card emphasizes
properties an SFT pipeline cares about (faithful to the instruction,
appropriate length, no padding, no fabrication, calibrated refusal
behavior) over properties a chat-bot cares about (warmth, follow-up
questions). Output is structured so a quality filter can inspect both
the response and the model's self-reported flags before the pair is
admitted to the training set.

This is the **"missing piece"** between instruction generation
(`sft/self-instruct-from-seed`, `sft/instruction-variant-expander`)
and quality filtering (`sft/data-quality-filter`): given an
instruction with no response, this card produces the candidate
response.

## Prompt

```text
You produce a high-quality response intended as the TARGET half of an
SFT training pair. The output will be paired with the instruction and
used as supervised training data; quality matters more than charm.

Instruction:
{{instruction}}

Style constraints (may be empty):
{{style_constraints}}

Domain hint (may be empty):
{{domain_hint}}

Rules:
1. Address the instruction directly. No filler preambles ("Sure, here
   is..."), no closing pleasantries ("Hope that helps!"). The response
   begins with substance.
2. Match the style constraints if provided; otherwise default to:
   neutral register, length proportional to the question's substance,
   plain text unless the instruction asks for code / list / JSON.
3. If the instruction has multiple valid interpretations, pick the
   most likely interpretation and answer it; do NOT ask a clarifying
   question (this is training data, not a chat). Note the ambiguity
   in `disambiguation` so the filter can decide.
4. If the instruction asks for content that violates docs/SAFETY.md
   (harm, jailbreak, hidden CoT extraction, fabricated PII), set
   `would_refuse: true` and produce a brief, principled refusal in
   `response_text` instead of complying.
5. Do NOT fabricate specific facts (names, dates, statistics) you do
   not actually know. If the instruction implies specific knowledge
   you lack, either give a generic high-quality answer that does not
   commit to specifics, or note the limitation.

Return ONLY this JSON object:
{
  "response_text": "<the SFT target response>",
  "would_refuse": true | false,
  "refusal_reason": "<if would_refuse=true: which principle was triggered; else empty>",
  "disambiguation": "<if you picked one of multiple interpretations: which one and why; else empty>",
  "self_assessment": {
    "addresses_instruction": "high" | "medium" | "low",
    "factual_risk": "high" | "medium" | "low",
    "length_appropriate": true | false
  },
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
instruction: "Summarize the difference between supervised and unsupervised learning in 2 sentences."
style_constraints: "neutral, accessible to a CS undergraduate"
domain_hint: ""
```

**Expected output:**

```json
{
  "response_text": "Supervised learning trains a model on input-output pairs, so it learns to predict labels for new inputs based on examples it has seen. Unsupervised learning has no labels — it finds structure (clusters, low-dimensional projections, etc.) in unlabeled data without being told what the right answer is.",
  "would_refuse": false,
  "refusal_reason": "",
  "disambiguation": "",
  "self_assessment": {
    "addresses_instruction": "high",
    "factual_risk": "low",
    "length_appropriate": true
  },
  "decision_basis": "Two-sentence definition contrast at undergraduate register; no specific facts at risk."
}
```

## Failure Modes

- **Filler resurgence** — model leads with "Great question!" or
  "Here's a summary:" despite the no-preamble rule. SFT data with
  consistent filler trains the production model to emit the same
  filler. Detect with a regex / classifier on training pairs;
  re-generate offenders.
- **Length inflation** — model produces 200-word response when 30
  words would suffice. The `length_appropriate` self-flag is a hint;
  also verify with token-count distribution against gold.
- **Fabrication under specificity pressure** — when the instruction
  asks "name three studies that show...", the model invents study
  names. Mitigation: rule 5; if `factual_risk: "high"`, route to a
  reference-based check (or to human review) before adding to
  training data.
- **Over-refusal** — model marks `would_refuse: true` for benign
  instructions because the topic touches a sensitive area
  (mental health, finance, legal). Track refusal rate against a
  benign benchmark; if >5% of benign instructions trigger refusal,
  the safety calibration is too aggressive.
- **Under-refusal** — model complies with instructions that
  docs/SAFETY.md forbids (e.g. produces operational malware
  instructions). Mitigation: route every `would_refuse: false`
  output through `eval/safety-output-classifier` before admitting
  to training data; reject mismatches.
- **Sycophancy in disambiguation** — model picks the user-implied
  interpretation rather than the most likely one. The
  `disambiguation` field surfaces this; sample borderline cases
  to verify.
- **Self-assessment inflation** — model marks `addresses_instruction:
  high` for everything. Track distribution; if "low" rate is <2%
  on a diverse benchmark, the field is unreliable.

## Tuning Notes

- 模型差异：response generator 通常用比目标 SFT 模型**更强**的模型
  （teacher-student 关系）。如果你的目标 SFT 模型是 7B，generator
  应该是 70B+ 或 frontier 模型。**不要**用同等规模或更弱的模型生成
  自己的 SFT 数据 — 那只会复刻已有模式。
- 温度：`0.3`–`0.7`。完全 0 温会让 N 个 instruction 的 response 风格
  趋同；高于 0.7 会引入 noise。
- 长度控制：通过 style_constraints 显式给 length range（e.g. "2-3
  sentences", "100-200 words"）比让模型自己掌控更稳。
- 与 `sft/self-instruct-from-seed` 的关系：那张卡产 instructions；
  本卡产 responses；两者串联是 self-instruct 训练数据 pipeline 的
  完整形态。
- 与 `sft/instruction-variant-expander` 的关系：variant-expander 假设
  variant 和 seed 共享一个 gold response（如果你只有 instruction），
  本卡可以为每个 variant 单独生成 response（如果你想让 variant 有
  不同 response）。
- 与 `sft/data-quality-filter` 的关系：本卡产出**必须**经过
  data-quality-filter 才能进入训练集。`would_refuse=true` 和
  `self_assessment.factual_risk=high` 的样本应该在 filter 阶段被
  特别审视。
- safety 双层防御：`would_refuse` 是 generator 的 self-flag，是
  first-pass 信号；最终决定 keep/drop 应当由 `eval/safety-output-classifier`
  + 人工 spot-check 共同判断。

## Changelog

- `0.1.0` — Initial card.
