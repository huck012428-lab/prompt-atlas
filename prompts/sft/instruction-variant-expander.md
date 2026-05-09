---
id: sft/instruction-variant-expander
title: Instruction Variant Expander (seed → diverse rewrites)
version: 0.1.0
status: stable
direction: sft
tags: [instruction-tuning, seed-expansion, data-augmentation, generation]
audience: [sft-team, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: seed_instruction
    description: A single seed instruction to expand.
    required: true
  - name: n_variants
    description: How many variants to produce.
    required: true
---

## Purpose

Take one seed instruction from a small high-quality SFT set and produce N
diverse rewrites that preserve task semantics but vary surface form, register,
and elicitation style. Used to multiply hand-curated SFT seeds into a larger
training set without drifting off-task. Output is structured so each variant
can be paired with the original gold answer (if the answer is invariant to
rewrites) or sent to a separate answer-generation pass.

## Prompt

```text
You expand a single seed instruction into {{n_variants}} diverse rewrites.

Constraints:
- Each variant MUST preserve the same underlying task and produce the same
  correct answer as the seed (no scope drift, no added or removed fields).
- Variants should differ on at least two of: surface phrasing, register
  (formal/casual/terse), context (with/without backstory), output format hint,
  language complexity.
- Do NOT introduce new entities, numbers, constraints, or topics not present
  in the seed.

Seed instruction:
{{seed_instruction}}

Return ONLY this JSON object:
{
  "variants": [
    {"text": "<variant 1>", "delta": "<one short phrase: what changed vs seed>"},
    {"text": "<variant 2>", "delta": "<...>"}
    /* ... up to {{n_variants}} entries */
  ]
}
```

## Example

**Input:**

```text
seed_instruction: "Summarize the following article in 3 bullet points."
n_variants: 3
```

**Expected output:**

```json
{
  "variants": [
    {"text": "Give me 3 bullets that capture the key points of this article.", "delta": "casual register"},
    {"text": "Please produce a three-bullet summary of the article below, preserving the original ordering of major points.", "delta": "formal + ordering hint"},
    {"text": "TL;DR in 3 bullets:", "delta": "terse style with format cue"}
  ]
}
```

## Failure Modes

- **Scope drift** — variant changes the task ("Summarize in 3 bullets" →
  "Translate the article"). Mitigation: post-filter by re-asking a verifier
  model "is variant X the same task as seed Y?" and dropping disagreements.
- **Cosmetic-only diversity** — all variants are the same sentence with
  punctuation tweaks. Detect with cheap surface metrics (Jaccard on tokens);
  reject batches with mean similarity > 0.85.
- **New constraint injection** — variant adds "in less than 50 words" or
  "in JSON" when seed had no such constraint. The `delta` field exposes this
  for review.
- **Answer divergence** — when paired with the seed's gold answer, the variant
  actually produces a different correct answer. Mitigation: re-run the gold
  answer generator on each variant and compare.

## Tuning Notes

- 模型差异：frontier 模型多样性显著高于开源中等模型；如果用 7B 模型生成会
  得到大量"换标点"伪多样性，建议用 GPT-4/Claude Sonnet 类模型生成 seed→variant
  扩展。
- 温度：`0.8`–`1.0`，多样性优先；之后用低温 verifier 过滤。
- N 选择：每个 seed 扩 5–10 个，过滤后保留率约 40–70%，得到 2–7 个有效 variant。
- 与人工的关系：此卡是规模化工具，不替代人工审核。建议保留 5–10% 样本送人工
  采样审核。

## Changelog

- `0.1.0` — Initial card.
