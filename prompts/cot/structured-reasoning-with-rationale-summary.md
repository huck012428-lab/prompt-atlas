---
id: cot/structured-reasoning-with-rationale-summary
title: Structured Reasoning with Rationale Summary
version: 0.1.0
status: stable
direction: cot
tags: [structured-reasoning, rationale-summary, decomposition-cot, structured-output]
audience: [prompt-engineer, llm-trainer, app-builder]
models: [generic, frontier-closed, mid-tier-closed, open-source-large, reasoning-model]
language: en
input_schema: text
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The question or task that requires reasoning.
    required: true
---

## Quick Use

**Use when:** You want the model to decompose its reasoning into named sub-steps and emit a summary rationale (not hidden chain-of-thought).
**Fill in:** `{{question}}` = the question or task that needs reasoning.
**You'll get:** Sub-steps each with a concrete result, a final answer, a short rationale_summary for the user, and a confidence level. Output is JSON.

## Purpose

Force a model to decompose a problem into named sub-steps, produce a final
answer, and emit a *summary* rationale (not a hidden chain-of-thought trace)
explaining the decision. Designed for production use where you need
auditability without leaking proprietary internal reasoning. Output is JSON
so each sub-step is individually inspectable and the rationale is bounded.

## Prompt

```text
Solve the following problem with structured reasoning. Decompose your work
into named sub-steps in the order you actually performed them, then produce
the final answer and a brief rationale.

Question:
{{question}}

Return ONLY this JSON object:
{
  "sub_steps": [
    {"name": "<short label>", "result": "<concrete output of this step>"},
    /* one entry per sub-step, 2 to 6 entries total */
  ],
  "final_answer": "<the answer>",
  "rationale_summary": "<<=40 words explaining how the sub-steps lead to the answer. NOT a verbatim trace of internal thoughts; a user-facing justification.>",
  "confidence": "low" | "medium" | "high"
}

Rules:
- Each sub-step must produce a concrete artifact (number, expression, claim).
  Do not write "I will think about X" — write what you found.
- The rationale_summary is for the end user. Do not include private chain-of-thought.
- Confidence reflects how robust the answer is to plausible variations in the input.
```

## Example

**Input:**

```text
question: "A train leaves at 9:00am traveling 80 km/h. Another leaves the same station at 10:30am traveling 100 km/h on the same track. When does the second train catch up?"
```

**Expected output:**

```json
{
  "sub_steps": [
    {"name": "head start", "result": "First train has 1.5h head start = 120 km lead at 10:30am"},
    {"name": "closing speed", "result": "Second train closes at 100 - 80 = 20 km/h"},
    {"name": "catch-up time", "result": "120 km / 20 km/h = 6 hours after 10:30am"},
    {"name": "clock time", "result": "10:30am + 6h = 4:30pm"}
  ],
  "final_answer": "4:30pm",
  "rationale_summary": "Computed the lead distance at the second train's departure, divided by the closing speed, and added to its start time.",
  "confidence": "high"
}
```

## Failure Modes

- **Sub-steps as filler** — model writes vague labels like "think about
  problem" with no concrete artifact. Mitigation: enforce that `result` must
  contain at least one number / equation / named entity at parse time.
- **Rationale becomes a CoT dump** — `rationale_summary` balloons to 200+
  words restating the sub-steps. Truncate at parse time; the 40-word cap is
  intentional.
- **Confidence calibration drift** — model says "high" on everything.
  Mitigation: hold out a calibration set; if "high" precision is not >=85%,
  add a few-shot showing a "medium" case.
- **Order misrepresentation** — model lists sub-steps in textbook order, not
  the order it actually used. Hard to detect; accept that the artifact is an
  exposed-order narrative, not a literal trace.

## Tuning Notes

- 模型差异：reasoning-model（如 o-系列、Claude extended-thinking）原生支持
  内部思维隐藏，只输出 summary，配合本卡效果最好。普通模型上 sub_steps 偶尔
  会重复或漏掉，可通过 `2 to 6 entries` 上下界约束缓解。
- 温度：`0.0`–`0.3`。
- 设计哲学：本卡明确避免 `chain_of_thought` / `internal_thoughts` 字段名，
  使用 `sub_steps` + `rationale_summary`——这同时是审计友好和符合多家闭源
  模型政策的设计。
- 不要用本卡尝试套出闭源模型的内部 reasoning trace；那既违反 docs/SAFETY.md
  也会触发模型方的反规避。

## Changelog

- `0.1.0` — Initial card.
