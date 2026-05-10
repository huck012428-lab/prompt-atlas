---
id: eval/reference-based-judge
title: Reference-based Judge (output vs gold)
version: 0.1.0
status: stable
direction: eval
tags: [llm-judge, scoring, factuality, comparative, structured-output]
audience: [eval-team, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The question or task the model was asked.
    required: true
  - name: gold_answer
    description: The reference / gold answer treated as the correct response.
    required: true
  - name: model_output
    description: The model's actual output to be judged against the gold.
    required: true
---

## Quick Use

**Use when:** You're scoring closed-form outputs (short-answer QA, math, structured extraction) against a known gold answer.
**Fill in:** `{{question}}` = the question; `{{gold_answer}}` = the reference correct answer; `{{model_output}}` = the AI's actual output.
**You'll get:** Correctness / completeness / style scores plus a match / partial_match / mismatch verdict and a one-sentence delta. Output is JSON.

## Purpose

Score a model output against a known-correct gold answer on three axes:
substantive correctness, completeness relative to the gold, and stylistic
fidelity (only as far as the user's task implies a style requirement).
Used for offline benchmark evaluation where every example has a ground
truth — short-answer QA, math, structured extraction, closed-form tasks.
Output is structured so per-axis means can be aggregated into a benchmark
score.

## Prompt

```text
You are a reference-based evaluation judge. Compare the model output
to the gold answer for the same question.

Question:
{{question}}

Gold answer:
{{gold_answer}}

Model output:
{{model_output}}

Score on three axes (1 to 5):
- correctness: Does the model output convey the same factual content as
  the gold answer? Penalize wrong facts, missing key facts, or
  contradictions. Do NOT penalize different wording when the meaning
  matches.
- completeness: Does the model output cover all the substantive points
  present in the gold answer? Partial coverage scores below 5.
- style_fidelity: Only judge if the question implies a format / style
  requirement (e.g. "in 2 bullets", "as JSON", "in 50 words"). If the
  question does NOT specify a style, score 5 by default and note in
  `style_relevant: false`.

Return ONLY this JSON object:
{
  "scores": {
    "correctness": 1-5,
    "completeness": 1-5,
    "style_fidelity": 1-5
  },
  "style_relevant": true | false,
  "verdict": "match" | "partial_match" | "mismatch",
  "delta": "<one sentence describing what differs from gold, <=30 words>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Verdict rule:
- "match"         — correctness=5 AND completeness>=4
- "partial_match" — correctness>=3 AND completeness>=3 (but not match)
- "mismatch"     — anything else
```

## Example

**Input:**

```text
question: "What is the capital of Australia?"
gold_answer: "Canberra is the capital of Australia."
model_output: "Sydney is Australia's capital and largest city."
```

**Expected output:**

```json
{
  "scores": {
    "correctness": 1,
    "completeness": 1,
    "style_fidelity": 5
  },
  "style_relevant": false,
  "verdict": "mismatch",
  "delta": "Model says Sydney, gold says Canberra; the answer is factually wrong.",
  "decision_basis": "Output names the wrong city; correctness is the deciding axis."
}
```

## Failure Modes

- **Reference hugging** — judge punishes any output that diverges in
  surface wording even when meaning matches the gold. Mitigation: the
  rubric's "Do NOT penalize different wording" line; spot-check
  partial_match outputs to see if rewording is being penalized.
- **Permissive on meaning shifts** — judge marks "Sydney is the largest
  city" as a match for "Canberra is the capital" because both are
  Australia-related. Detect by sampling and asking "would a human say
  this output answers the question?"
- **Style over-weighting** — when the question hints at format ("answer
  briefly"), judge pushes correctness down because output was wordy.
  Mitigation: keep style_fidelity as a separate axis, not a multiplier;
  the verdict rule depends primarily on correctness and completeness.
- **Gold under-specification** — when the gold answer is itself
  incomplete (missing a valid alternative), the judge will mark a
  correct-but-different output as mismatch. This is a dataset issue,
  not a judge issue; budget for a small human re-audit on mismatches.

## Tuning Notes

- 模型差异：strong judge（GPT-4 / Claude Sonnet+）在 correctness vs
  completeness 区分上稳定；中档模型容易把两者混淆。降级方案：只用
  correctness 一个轴，verdict 只用 match / mismatch 二档。
- 温度：`0.0`，benchmark 评估可重现性优先。
- 与 `eval/llm-judge-rubric-open-ended` 的关系：本卡需要 gold answer，
  适合 closed-form 任务；rubric-open-ended 适合没有标准答案的开放式
  生成（advice、解释、长文）。
- 与 `eval/per-claim-factuality-judge` 的关系：本卡的 correctness 是
  整体级；per-claim-factuality-judge 是逐 claim 级，更细但更贵。短答
  题用本卡，长答题用 per-claim。
- gold quality：本卡的天花板是 gold answer 的质量。如果你发现一致的
  "judge 错判"，先怀疑 gold 不全或不唯一，再怀疑 judge。

## Changelog

- `0.1.0` — Initial card.
