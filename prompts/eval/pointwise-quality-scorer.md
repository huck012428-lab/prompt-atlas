---
id: eval/pointwise-quality-scorer
title: Pointwise Quality Scorer with Confidence
version: 0.1.0
status: stable
direction: eval
tags: [llm-judge, scoring, holistic, structured-output, coherence]
audience: [eval-team, ai-pm, llm-trainer]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: task_description
    description: The task the output was generated for.
    required: true
  - name: model_output
    description: The single output to be scored.
    required: true
  - name: scoring_dimensions
    description: A list of dimension names the judge should score on, comma-separated. Each name maps to a 1-5 score plus a justification.
    required: true
---

## Purpose

Produce a single-output, multi-dimensional quality score with explicit
self-reported confidence. Used when pairwise comparison is unavailable
(only one output per prompt) or inappropriate (no canonical alternative
exists). The confidence field is the differentiator vs
`eval/llm-judge-rubric-open-ended`: it surfaces low-signal judgments so
they can be down-weighted or routed to human review, instead of polluting
aggregate metrics with unreliable scores.

## Prompt

```text
You are a pointwise quality judge. Score the model output on the
specified dimensions, and report your confidence in each score.

Task description:
{{task_description}}

Model output:
{{model_output}}

Scoring dimensions (judge each on a 1-5 scale):
{{scoring_dimensions}}

For each dimension:
- Give an integer score 1-5.
- Give a short justification (one sentence, <=20 words).
- Give your confidence in the score on a 3-level scale:
  - "high"   — the score is robust to minor rephrasings of the output.
  - "medium" — the score might shift by 1 with a different reading.
  - "low"    — you are guessing; the dimension may not apply or you
               lack evidence to judge.

Return ONLY this JSON object:
{
  "dimensions": [
    {"name": "<dimension>", "score": 1-5, "justification": "<...>", "confidence": "high" | "medium" | "low"},
    /* one entry per dimension */
  ],
  "overall_score": <float 1.0-5.0: weighted by confidence — high=1.0, medium=0.5, low=0.25>,
  "trustworthy_aggregate": true | false,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Set "trustworthy_aggregate": true only if MAJORITY of dimensions have
"high" or "medium" confidence. Set false if mostly "low".
```

## Example

**Input:**

```text
task_description: "Explain quantum entanglement to a high school student in 4-5 sentences."
model_output: "Quantum entanglement is when two particles become linked so that measuring one instantly affects the other, no matter how far apart they are. Einstein famously called it 'spooky action at a distance.' This doesn't violate the speed of light because no usable information actually travels between the particles. Today, entanglement is the basis for emerging technologies like quantum computing and quantum cryptography."
scoring_dimensions: "factuality, age_appropriateness, completeness, coherence"
```

**Expected output:**

```json
{
  "dimensions": [
    {"name": "factuality", "score": 5, "justification": "All claims are standard accurate descriptions of entanglement.", "confidence": "high"},
    {"name": "age_appropriateness", "score": 4, "justification": "Accessible language but assumes some baseline physics vocabulary.", "confidence": "medium"},
    {"name": "completeness", "score": 4, "justification": "Covers key aspects but does not mention a concrete example or experiment.", "confidence": "medium"},
    {"name": "coherence", "score": 5, "justification": "Logically ordered and well-paced.", "confidence": "high"}
  ],
  "overall_score": 4.5,
  "trustworthy_aggregate": true,
  "decision_basis": "Strong factuality and coherence; mild gaps on completeness and accessibility."
}
```

## Failure Modes

- **Confidence inflation** — judge marks every dimension "high"
  regardless of whether the score is robust, defeating the purpose.
  Mitigation: track confidence distribution across a benchmark; if
  "high" rate is >85%, the judge is not calibrating. Add few-shots
  showing "low" cases (vague output, dimension that doesn't apply).
- **Dimension irrelevance** — judge scores 5 on `creativity` for a
  literal extraction task. The "low confidence" label exists for this;
  if you see scores high but with low confidence, the dimension was
  misapplied — drop it.
- **Justification ↔ score drift** — justification says "missing key
  points" but score is 5. Detect by sampling and reading
  justification + score together; if 10% drift, re-tighten the rubric.
- **Score compression** — most outputs cluster at 3-4. This usually
  means the dimensions are too holistic; split them or use a 1-3 scale.
- **Confidence vs judge model size** — small judge models tend to
  collapse "low" confidence to "I'd rather not say"; they refuse
  rather than admit uncertainty. Switch to a stronger judge or accept
  that confidence calibration won't work below a certain size.

## Tuning Notes

- 模型差异：confidence 字段的实际信号强度和模型规模强相关。frontier
  模型的 confidence 大致可信；中档模型的 confidence 主要是 noise，
  此时把本卡降级为只保留 score + justification 即可。
- 温度：`0.0`–`0.2`。
- 与 `eval/llm-judge-rubric-open-ended` 的关系：rubric-open-ended 是
  四个固定维度（factuality / instruction_following / coherence /
  completeness）；本卡的维度由调用者通过 `scoring_dimensions` 传入，
  适合需要自定义维度的产品场景（"toxicity-safe"、"on-brand-voice"
  等）。
- 与 `rlhf/pairwise-preference-labeler` 的关系：pairwise 通常一致性
  比 pointwise 高，但需要两个候选；只有单输出时用本卡。
- aggregation 策略：上线前用 100 个人工 gold 算 quadratic-weighted
  kappa，再决定 overall_score 是否可作为单一指标，还是只作多指标
  之一。

## Changelog

- `0.1.0` — Initial card.
