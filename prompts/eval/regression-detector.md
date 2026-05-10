---
id: eval/regression-detector
title: Output-Level Regression Detector
version: 0.1.0
status: stable
direction: eval
tags: [llm-judge, scoring, comparative, structured-output]
audience: [eval-team, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: prompt
    description: The input prompt that was given to both versions.
    required: true
  - name: baseline_output
    description: The output from the baseline (current production / last good) version.
    required: true
  - name: candidate_output
    description: The output from the candidate (new / proposed) version.
    required: true
  - name: regression_dimensions
    description: Comma-separated dimensions to check for regression (e.g. "factuality, completeness, format_adherence, safety"). If empty, defaults to factuality + completeness + format_adherence.
    required: false
---

> 🎯 **场景**：上线前回归测试——同一 prompt 喂 baseline 和 candidate 两版模型，本卡判候选是否在指定维度上**变差**。维度级精细判断（factuality 维持但 completeness 下降也算 regression），避免"整体差不多"掩盖局部退步。

## Quick Use

**Use when:** You're testing a candidate model / prompt change against a baseline and need to detect quality regressions on specific dimensions, not just an overall vibe check.
**Fill in:** `{{prompt}}` = the input; `{{baseline_output}}` = current/last-good output; `{{candidate_output}}` = new output; `{{regression_dimensions}}` = comma-separated dimensions or empty.
**You'll get:** Per-dimension regression verdict (better / same / worse) with evidence, an overall regression flag, and severity. Output is JSON.

## Purpose

Detect whether a candidate output regresses against a baseline on
specific quality dimensions. Used for pre-launch model regression
testing, A/B prompt change evaluation, and continuous quality
monitoring on production traffic. Distinct from
`eval/pairwise-judge-with-position-bias-probe`: that card measures
preference; this card detects regression specifically (when the
prompt change should be neutral or positive). Output is structured
so per-dimension regression rates can be aggregated across a benchmark.

## Prompt

```text
You compare a candidate output against a baseline and detect any
regression on specific quality dimensions.

Prompt:
{{prompt}}

Baseline output:
{{baseline_output}}

Candidate output:
{{candidate_output}}

Regression dimensions to check (may be empty; if empty use
factuality + completeness + format_adherence):
{{regression_dimensions}}

For each dimension, decide:
- "candidate_better": Candidate is meaningfully better than baseline on this dimension.
- "same"            : No meaningful difference on this dimension.
- "candidate_worse" : Candidate is meaningfully worse — REGRESSION.

"Meaningfully better/worse" means a human evaluator would
consistently agree, not just stylistic preference.

For each candidate_worse, provide:
- evidence_baseline : What the baseline did right (verbatim or close
                       paraphrase from baseline).
- evidence_candidate: What the candidate did wrong (verbatim or close
                       paraphrase from candidate).
- impact            : "low" (cosmetic), "medium" (annoying but
                       acceptable), "high" (blocks the candidate
                       from shipping).

Return ONLY this JSON object:
{
  "per_dimension": [
    {
      "dimension": "<name>",
      "verdict": "candidate_better" | "same" | "candidate_worse",
      "evidence_baseline": "<for verdict != 'same'; else empty>",
      "evidence_candidate": "<for verdict != 'same'; else empty>",
      "impact": "low" | "medium" | "high (only for candidate_worse)"
    }
  ],
  "regression_detected": true | false,
  "regression_severity": "none" | "low" | "medium" | "high",
  "ship_decision": "ship" | "review_required" | "block",
  "ship_reason": "<one sentence>",
  "decision_basis": "<one sentence, <=40 words, no internal CoT>"
}

Ship decision rule:
- "block"           — any high-impact regression OR factuality
                      regression at any impact.
- "review_required" — any medium-impact regression OR multiple low-
                      impact regressions.
- "ship"            — no regressions OR only candidate-better /
                      same.
```

## Example

**Input:**

```text
prompt: "Summarize the following article in 3 bullet points: [article about Voyager 1]"
baseline_output: "- Voyager 1 entered interstellar space on August 25, 2012.\n- It continues to send data despite being 24+ billion km from Earth.\n- Its instruments are nearing end of operational life."
candidate_output: "Voyager 1 is a fascinating spacecraft. It launched in 1977. It has provided humanity with so much knowledge about the outer solar system."
regression_dimensions: "factuality, format_adherence, completeness"
```

**Expected output:**

```json
{
  "per_dimension": [
    {
      "dimension": "factuality",
      "verdict": "same",
      "evidence_baseline": "",
      "evidence_candidate": "",
      "impact": "low"
    },
    {
      "dimension": "format_adherence",
      "verdict": "candidate_worse",
      "evidence_baseline": "Three bullet points as requested.",
      "evidence_candidate": "Free-form prose, three sentences but not bullets; ignored '3 bullet points' format requirement.",
      "impact": "high"
    },
    {
      "dimension": "completeness",
      "verdict": "candidate_worse",
      "evidence_baseline": "Covers heliopause crossing, current data status, and instrument lifespan — three substantive points.",
      "evidence_candidate": "Covers launch year and a vague 'fascinating' observation; misses the article's substantive points.",
      "impact": "high"
    }
  ],
  "regression_detected": true,
  "regression_severity": "high",
  "ship_decision": "block",
  "ship_reason": "High-impact format and completeness regressions; candidate ignored the bullet format and lost the substantive content.",
  "decision_basis": "Two high-impact regressions: format requirement violated and substantive points lost from baseline."
}
```

## Failure Modes

- **Stylistic preference as regression** — model marks "candidate_worse"
  on dimensions where it's just a different style, not a regression.
  Verify by checking that "evidence_candidate" describes a real
  defect, not just "feels less polished".
- **Missing high-impact regressions** — model marks "same" when the
  candidate clearly broke something. Sample outputs flagged "ship"
  and verify on a known-broken benchmark; if any broken candidates
  pass, the bar is too lenient.
- **Severity inflation** — every regression is "high". Track
  distribution against ground-truth severity ratings.
- **Ship-decision bypass** — model issues "ship" verdict despite
  factuality regression (which the rule says should block). Always
  verify rule logic at parse time.
- **Dimension drift** — model evaluates dimensions not in
  regression_dimensions. Audit per_dimension list against the input
  filter.
- **Cosmetic-style penalty** — penalizing the candidate for using
  different but equally-correct wording. The bar should be
  "meaningfully different to a human", not "any difference".

## Tuning Notes

- 模型差异：必须 frontier 模型作为 judge——detection 需要细致判断。
  中档 judge 常出现 stylistic-as-regression 误判。
- 温度：`0.0`，regression detection 必须可重现。
- regression_dimensions 选择：和你的产品 SLA 对齐。聊天产品 typically
  factuality + completeness + tone；代码生成 correctness + format +
  efficiency；checklist 类 completeness + format。
- 与 `eval/pairwise-judge-with-position-bias-probe` 的关系：那张卡
  无方向性偏好（A 还是 B 好）；本卡有明确方向性（candidate 是否退步
  于 baseline）。前者用于 RLHF data；后者用于 ship decision。
- 与 `eval/multi-turn-dialogue-judge` 的关系：那张卡评对话内部一致性；
  本卡评模型版本之间一致性。两者解决相邻但不同问题。
- benchmark 设计：维护一组（prompt, baseline_output）固定 pair，
  每次 candidate 跑同一组并用本卡比较。结果汇总成 regression rate
  per dimension，可以接告警。
- ship decision 是建议，不是裁决：高敏产品（医疗 / 金融 / 安全）应当
  不靠 LLM judge 单独决定 ship；本卡的 ship_decision 是 first signal，
  人工 review 是必要 second gate。
- 跨多个 prompt 的统计：单 prompt 上的 regression detection 噪声大；
  生产监控建议 100+ prompt batch 跑一遍，看 regression rate 是否
  显著上升（统计显著性，比如 chi-square test）。

## Changelog

- `0.1.0` — Initial card.
