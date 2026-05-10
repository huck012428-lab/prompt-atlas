---
id: eval/human-eval-bootstrap
title: Human Eval Study Bootstrap
version: 0.1.0
status: experimental
direction: eval
tags: [llm-judge, rubric, structured-output]
audience: [eval-team, ai-pm, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: task_description
    description: One paragraph describing the task being evaluated.
    required: true
  - name: sample_size
    description: Target number of human-rated samples (typically 30-300).
    required: true
  - name: budget_constraints
    description: Optional one-line budget hint (e.g. "cheap labelers, max 5 min per sample"). Pass empty string for default rigor.
    required: false
---

> 🎯 **场景**：从 task 描述快速搭一个人工评测研究——出 rubric、annotator 培训说明、calibration 样本数、analysis plan。比"找 5 个人来打分"靠谱得多。LLM-as-judge 正式上线前先做小规模 human eval 是质量保障的金标准。

## Quick Use

**Use when:** You're standing up a human eval study for a task and want a structured study design (rubric, annotator instructions, sample size guidance, analysis plan) instead of figuring it out ad-hoc.
**Fill in:** `{{task_description}}` = the task; `{{sample_size}}` = target sample count; `{{budget_constraints}}` = optional budget hint.
**You'll get:** A complete study design with rubric, annotator instructions, calibration plan, and analysis recommendations. Output is JSON.

## Purpose

Bootstrap a small human evaluation study from a task description.
Produces the artifacts you actually need (rubric, annotator
instructions, calibration sample plan, analysis plan) so a human
eval can be set up in hours rather than weeks. Used before scaling
LLM-as-judge to production, as a reality check on whether the
LLM judge agrees with humans, and as a post-launch quality
benchmark.

## Prompt

```text
You design a small human evaluation study from a task description.

Task description:
{{task_description}}

Target sample size: {{sample_size}}

Budget constraints (may be empty):
{{budget_constraints}}

Steps:
1. Define what's being evaluated (the unit of analysis: per-output,
   per-pair, per-conversation).

2. Design the rubric:
   - 3-5 dimensions appropriate to the task.
   - Each dimension: 1-5 scale OR binary (depending on task).
   - Each dimension: 1-2 sentence operational definition + 1
     positive example + 1 negative example.

3. Annotator instructions:
   - Background needed (or "no background needed").
   - Time per sample estimate.
   - Common mistakes to avoid (e.g. don't reward verbosity,
     don't penalize style differences from your own preference).

4. Calibration plan:
   - 5-10 calibration samples (with author-supplied gold ratings)
     each annotator should label first.
   - Pass criterion: agreement with gold ≥ X% before they label
     the real set.

5. Inter-annotator setup:
   - How many annotators per item (typical 2-3 for medium-stakes,
     3-5 for high-stakes).
   - Resolution rule for disagreements (majority / median / third
     annotator).

6. Analysis plan:
   - Headline metric (e.g. mean rating per dimension, fleiss kappa
     for agreement).
   - Reporting format (CI, per-stratum break, etc.).
   - Threshold for declaring "model passes" / "needs work".

Return ONLY this JSON object:
{
  "unit_of_analysis": "<short>",
  "rubric": [
    {
      "dimension": "<name>",
      "scale": "1-5" | "binary" | "<other>",
      "definition": "<1-2 sentences>",
      "positive_example": "<short>",
      "negative_example": "<short>"
    }
  ],
  "annotator_instructions": {
    "background_required": "<short or 'no specific background'>",
    "time_per_sample_minutes": <integer>,
    "common_mistakes_to_avoid": ["<short>"]
  },
  "calibration_plan": {
    "n_calibration_samples": <integer>,
    "pass_criterion": "<short>"
  },
  "annotator_setup": {
    "annotators_per_item": <integer>,
    "resolution_rule": "<short>"
  },
  "analysis_plan": {
    "headline_metric": "<short>",
    "agreement_metric": "<short>",
    "model_pass_threshold": "<short>"
  },
  "estimated_total_cost_indicator": "<rough; under specified budget if any>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
task_description: "Customer support agent responses to refund requests."
sample_size: 100
budget_constraints: "Trained labelers OK, max 3 min per sample"
```

**Expected output (abridged):**

```json
{
  "unit_of_analysis": "per-response (one customer message → one agent response)",
  "rubric": [
    {"dimension": "issue_addressed", "scale": "1-5", "definition": "Does the response address the actual issue raised?", "positive_example": "Customer asks for refund timing → response gives 3-5 business day estimate", "negative_example": "Customer asks for refund → response promises a callback"},
    {"dimension": "tone_appropriate", "scale": "1-5", "definition": "Tone is empathetic but not over-apologetic", "positive_example": "...", "negative_example": "..."},
    {"dimension": "actionable", "scale": "binary", "definition": "Does customer have a concrete next step?", "positive_example": "...", "negative_example": "..."}
  ],
  "annotator_instructions": {
    "background_required": "Familiarity with customer-support norms; no specific industry expertise.",
    "time_per_sample_minutes": 3,
    "common_mistakes_to_avoid": ["Don't reward verbose / over-apologetic replies — concise replies on-issue should score 5.", "Don't penalize style differences from your own writing — focus on substance."]
  },
  "calibration_plan": {"n_calibration_samples": 8, "pass_criterion": "Agreement with author gold ≥ 75% before labeling real set."},
  "annotator_setup": {"annotators_per_item": 2, "resolution_rule": "Disagreements >1 point on a dimension routed to a third annotator; final = median."},
  "analysis_plan": {
    "headline_metric": "Mean per-dimension score, broken by refund-reason stratum.",
    "agreement_metric": "Cohen's kappa between primary 2 annotators per dimension.",
    "model_pass_threshold": "All dimensions mean ≥ 4.0; kappa ≥ 0.6 (substantial agreement)."
  },
  "estimated_total_cost_indicator": "~10 hours total annotator time (100 samples × 2 annotators × 3 min)",
  "decision_basis": "Standard CS-response eval with on-issue / tone / actionable axes; 2 annotators with kappa monitoring."
}
```

## Failure Modes

- **Rubric too generic** — dimensions like "quality" or "good" with
  no operational definition. Audit definition lengths and example
  specificity.
- **Sample size mismatch** — model returns plan that doesn't account
  for the requested sample size's statistical power. Sample size
  affects how many calibration samples are appropriate.
- **Calibration unrealistic** — pass criterion 95% on subjective
  task. Calibrate criterion: 70-80% on subjective, 90%+ on
  objective.
- **Annotators_per_item miscalibrated** — 1 annotator on
  high-stakes / 5 on low-stakes. Match to task criticality.
- **Cost estimate hand-wave** — vague time estimates. Verify by
  multiplying samples × annotators × time.

## Tuning Notes

- 模型差异：frontier 模型在 rubric design 上明显更具体；中档模型
  容易给 generic 维度。
- 温度：`0.0`–`0.3`。
- 与 `eval/rubric-generator` 的关系：那张卡只生 rubric；本卡是完整
  human study 设计含 rubric。本卡更全面，那张卡更聚焦。
- 与 `eval/judge-bias-probe` 的关系：human eval 完成后，可以用
  human gold 对 LLM judge 跑 bias probe — 检测 judge 和 human 在
  哪里分歧最大。
- 上线 LLM-as-judge 前流程：本卡设计 human study → 跑 ~50-200
  human-labeled samples → LLM judge 跑同一组 → 对比 LLM-vs-human
  agreement → 决定 LLM judge 是否可信。本卡是这个流程的入口。
- 不要省略 calibration: 直接发 N annotators 不培训 = noise. 5-10 个
  calibration samples 是最低标准.

## Changelog

- `0.1.0` — Initial card.
