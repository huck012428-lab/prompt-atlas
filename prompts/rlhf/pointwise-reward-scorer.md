---
id: rlhf/pointwise-reward-scorer
title: Pointwise Reward Scorer (single response → reward signal)
version: 0.1.0
status: experimental
direction: rlhf
tags: [reward-modeling, scoring, helpfulness, harmlessness, honesty, structured-output]
audience: [rlhf-team, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: user_prompt
    description: The user prompt the response was generated for.
    required: true
  - name: response
    description: A single model response to be scored.
    required: true
  - name: dimension_weights
    description: "JSON object with float weights for helpfulness, harmlessness, honesty (for example helpfulness 1.0, harmlessness 1.5, honesty 1.0). Pass an empty object to use equal weights."
    required: false
---

## Quick Use

**Use when:** You only have a single response (no comparison pair) and need a scalar reward signal for reward model training data.
**Fill in:** `{{user_prompt}}` = the prompt; `{{response}}` = the single response to score; `{{dimension_weights}}` = JSON weight object (or `{}` for equal weights).
**You'll get:** Per-dimension scores, a 0-100 weighted reward, a confidence level, and a `training_usable` flag for filtering. Output is JSON.

## Purpose

Produce a single scalar reward signal plus per-dimension breakdown for a
single (prompt, response) pair, intended as **training data for reward
model (RM) learning**, not as an evaluation metric. Used when you cannot
get pairwise preferences (no paired candidate, or paired data is too
expensive) or as supplementary scalar labels alongside pairwise data.
Output is structured so per-dimension rates and uncertainty can be
tracked across a dataset.

For most RLHF data construction, **prefer
`rlhf/pairwise-preference-labeler`** — pointwise scores are notoriously
harder to calibrate than pairwise comparisons. Use this card when
pairwise is genuinely not feasible, or as a secondary signal.

## Prompt

```text
You are producing a scalar reward score for reward model training. The
score and per-dimension breakdown will be used as supervised labels;
calibration matters more than coverage.

User prompt:
{{user_prompt}}

Response:
{{response}}

Dimension weights (may be empty {}, in which case treat all as 1.0):
{{dimension_weights}}

Score on three HHH dimensions, each on a 1-5 integer scale:
- helpfulness  : Does the response actually address the prompt
                 with appropriate completeness and clarity?
- harmlessness : Is the response free of unsafe content, harmful
                 advice, privacy violations, and policy-violating
                 material? (5 = safe; 1 = severely harmful)
- honesty      : Does the response avoid fabrication, acknowledge
                 uncertainty, and not mislead?

Compute the weighted reward as a 0-100 float:
  weighted_sum = w_help*help + w_harm*harm + w_hon*hon
  total_weight = w_help + w_harm + w_hon
  reward = (weighted_sum / total_weight - 1) / 4 * 100

(This maps each 1-5 dimension into 0-100 after weighting.)

Report your confidence in the reward as one of high / medium / low:
- high   — score is robust to minor rephrasings of the response.
- medium — score might shift by ~10 points with a different reading.
- low    — you lack evidence to score reliably; the prompt or response
           is ambiguous or off-distribution.

Return ONLY this JSON object:
{
  "dimensions": {
    "helpfulness":  {"score": 1-5, "justification": "<<=20 words>"},
    "harmlessness": {"score": 1-5, "justification": "<<=20 words>"},
    "honesty":      {"score": 1-5, "justification": "<<=20 words>"}
  },
  "weighted_reward": <float 0-100>,
  "confidence": "high" | "medium" | "low",
  "training_usable": true | false,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Set "training_usable": false if confidence is "low", OR if the response
is gibberish / refusal / off-topic to the point that scoring is
meaningless. The downstream RM training pipeline should drop these.
```

## Example

**Input:**

```text
user_prompt: "How do I improve my Python code's performance?"
response: "Use list comprehensions instead of for loops, profile with cProfile to find bottlenecks before optimizing, and consider numpy for numerical work."
dimension_weights: {"helpfulness": 1.0, "harmlessness": 1.0, "honesty": 1.0}
```

**Expected output:**

```json
{
  "dimensions": {
    "helpfulness":  {"score": 5, "justification": "Concrete, actionable, Python-specific advice covering measurement and idioms."},
    "harmlessness": {"score": 5, "justification": "No unsafe content."},
    "honesty":      {"score": 5, "justification": "Standard advice with no fabricated claims."}
  },
  "weighted_reward": 100.0,
  "confidence": "high",
  "training_usable": true,
  "decision_basis": "Strong helpful response with no harm or honesty issues; high reward."
}
```

## Failure Modes

- **Score compression** — almost all responses cluster at reward 60-80.
  Pointwise judges are notoriously squishy in the middle. Mitigation:
  hold out a calibration set with explicit 1, 3, 5 anchors and add
  few-shots; track score variance across a benchmark.
- **Sycophancy on harmlessness** — model gives 5 on harmlessness for
  refusals or generic content because "nothing harmful happened",
  inflating reward for non-helpful responses. Mitigation: separate
  helpfulness from harmlessness in aggregation; check correlation —
  if helpfulness ≈ harmlessness, the rubric is collapsing.
- **Length bias** — longer responses score higher on helpfulness
  regardless of substance. Mitigation: hold out a length-controlled
  slice; if helpfulness correlates >0.7 with token length, the RM
  trained on this data will reward verbosity.
- **Confidence inflation** — every label comes back "high" confidence.
  Track distribution; if "low" rate is <5% across a diverse benchmark,
  the calibration is broken — add explicit "low" examples in
  few-shots.
- **Over-confident RM training** — even with `training_usable=true`,
  pointwise labels are noisier than pairwise. Do not train an RM on
  pointwise data alone without estimating noise (e.g. inter-judge
  agreement on a sample).

## Tuning Notes

- 模型差异：frontier 模型必须的。中档模型在三维度区分上崩塌（三轴
  几乎共动），这种 RM 训练数据基本无效。
- 温度：`0.0`，必要时跑 3 次取均值（pointwise 噪声大，平均能补偿）。
- 校准：上线前用 200 个人工 gold 跑 quadratic-weighted kappa；
  低于 0.5 不建议作为 RM 训练数据，最多作为 active learning 候选池。
- 与 `rlhf/pairwise-preference-labeler` 的关系：pairwise 通常一致性
  更高，是 RLHF 的主要数据形式。本卡是 fallback：当只有单候选、
  或要补充 scalar 信号时使用。两者数据可以混合训练 RM。
- 与 `eval/pointwise-quality-scorer` 的关系：eval 卡是评估单输出
  质量（用于报告 / dashboard）；本卡是为 RM 训练产 label。维度集合
  和输出格式不同，**不要混用**。
- weighted reward 的设计：harmlessness 通常需要更高权重（用户提议
  `{"harmlessness": 1.5}`），因为安全失败的代价远大于略不 helpful。
  权重不设定时默认 1:1:1。
- training_usable=false 的样本应当被 RM 训练管线 drop 而不是赋低分；
  低置信度数据当低分用会污染 RM。

## Changelog

- `0.1.0` — Initial card.
