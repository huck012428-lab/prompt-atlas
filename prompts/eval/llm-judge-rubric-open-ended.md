---
id: eval/llm-judge-rubric-open-ended
title: LLM-as-Judge Rubric for Open-Ended Outputs
version: 0.1.0
status: stable
direction: eval
tags: [llm-judge, rubric, holistic, scoring, factuality, coherence]
audience: [eval-team, ai-pm, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: task_description
    description: One paragraph describing what the model was asked to do.
    required: true
  - name: model_output
    description: The model's response to be judged.
    required: true
  - name: reference_answer
    description: A reference / gold answer, if available. Pass empty string if none.
    required: false
---

> 🎯 **场景**：开放式输出（长文 / 解释 / advice）的 LLM-as-judge 打分——固定 4 维度（factuality / instruction-following / coherence / completeness）+ 整体 verdict。无 gold 答案场景的主力打分卡。

## Quick Use

**Use when:** You want a structured quality assessment of a single AI output across factuality / instruction-following / coherence / completeness.
**Fill in:** `{{task_description}}` = what the AI was asked to do; `{{model_output}}` = the AI's response; `{{reference_answer}}` = optional gold reference (pass empty string if none).
**You'll get:** Per-dimension scores 1-5, a holistic verdict, a one-sentence basis, and concrete issues. Output is JSON.

## Purpose

Score a single open-ended model output against a rubric covering factuality,
instruction-following, coherence, and completeness. Used for offline eval
runs where exact-match metrics do not apply (long-form generation, advice,
explanations). Output is a per-criterion score plus a holistic decision so
you can both rank models and inspect specific weak dimensions.

## Prompt

```text
You are an evaluation judge. Score the model output on each rubric dimension
from 1 (poor) to 5 (excellent), then give a holistic verdict.

Rubric:
- factuality: Are factual claims correct? Treat unverifiable opinions
  neutrally; only penalize false claims.
- instruction_following: Did the output do what the task description asked,
  in the requested format and scope?
- coherence: Is the output well-structured, internally consistent, and
  readable?
- completeness: Does the output cover the points needed to fully respond,
  without obvious gaps?

Task description:
{{task_description}}

Model output:
{{model_output}}

Reference answer (may be empty if no reference exists):
{{reference_answer}}

Return ONLY this JSON object:
{
  "scores": {
    "factuality": 1-5,
    "instruction_following": 1-5,
    "coherence": 1-5,
    "completeness": 1-5
  },
  "verdict": "excellent" | "good" | "borderline" | "poor",
  "decision_basis": "<one sentence, <=40 words, no quotes from output>",
  "issues": ["<concrete issue 1>", "<concrete issue 2>"]
}

If reference_answer is empty, judge factuality based on common knowledge and
internal consistency only; do not penalize for not matching a missing reference.
```

## Example

**Input:**

```text
task_description: "Explain why the sky appears blue, in 2-3 sentences accessible to a curious 12-year-old."
model_output: "The sky looks blue because sunlight hits air molecules and scatters. Blue light scatters more than red because it has a shorter wavelength, so we see more blue from every direction in the sky."
reference_answer: ""
```

**Expected output:**

```json
{
  "scores": {
    "factuality": 5,
    "instruction_following": 5,
    "coherence": 5,
    "completeness": 4
  },
  "verdict": "excellent",
  "decision_basis": "Accurate Rayleigh scattering explanation in two sentences at the requested register; could note sunset reddening for completeness.",
  "issues": ["Does not address why sunsets appear red, which would round out the explanation."]
}
```

## Failure Modes

- **Self-preference bias** — when judging output from the same model family,
  score is inflated. Mitigation: cross-judge with a different model family
  on a holdout slice; report the gap.
- **Reference hugging** — when reference_answer is provided, the judge
  punishes any output that diverges in style even if substantively correct.
  Mitigation: explicit instruction in the prompt that style differences are
  not penalized; show this in few-shots if drift persists.
- **Verbosity reward** — long outputs score higher on completeness regardless
  of substance. Mitigation: length-controlled eval slice; if completeness
  correlates >0.7 with length, retrain raters or add a "do not reward
  verbosity" line.
- **Score compression** — judge gives 4 to almost everything. Mitigation:
  inspect distribution; if entropy is low, increase temperature slightly or
  add few-shots with explicit 1, 3, and 5 examples.

## Tuning Notes

- 模型差异：判官模型应当强于（或至少不弱于）被判模型；用 7B 判 70B 通常
  得到压缩分布。常用配置：GPT-4 / Claude Sonnet 作为 judge。
- 温度：`0.0`，结果稳定性优先；如需多次采样取均值，再略提温度（`0.3`）。
- agreement：上线前用 100 个人工 gold 样本算 quadratic-weighted kappa；
  低于 0.5 不建议作为单一指标，可作为多指标之一。
- pair 与 pointwise 的关系：本卡是 pointwise；如需排序模型，pairwise
  （见 `rlhf/pairwise-preference-labeler`）通常一致性更高。

## Changelog

- `0.1.0` — Initial card.
