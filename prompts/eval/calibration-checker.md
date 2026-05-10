---
id: eval/calibration-checker
title: Calibration Checker (predicted confidence vs actual accuracy)
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
  - name: predictions
    description: A JSON array of records, each with `predicted_confidence` (high / medium / low or numeric 0-1), `actual_correctness` (true / false), and optional `category` for stratification.
    required: true
---

> 🎯 **场景**：检查模型的 confidence 是不是说真话——high-confidence 答案的实际正确率应当接近 1.0。本卡按 confidence bucket 算正确率，画 calibration curve（文字版），找出 over-confident 和 under-confident 区域。

## Quick Use

**Use when:** You have a batch of model outputs with both predicted confidence AND actual correctness labels, and you want to check whether the confidence is calibrated (high-confidence outputs should be more accurate than low-confidence ones).
**Fill in:** `{{predictions}}` = JSON array of {predicted_confidence, actual_correctness, optional category} records. Typical 50-1000 records.
**You'll get:** Per-confidence-bucket accuracy, calibration error, and identification of over-confident / under-confident regions. Output is JSON.

## Purpose

Diagnose whether a model's self-reported confidence is calibrated to
its actual accuracy. If the model says "high confidence" 80% of the
time but is only correct 60% of the time on those, it's
over-confident — a serious problem because downstream decisions
trust those labels. Used after running any pipeline that produces
(prediction, confidence, ground_truth) tuples — RAG quality
evals, classification benchmarks, judge calibration tests.

## Prompt

```text
You analyze a batch of predictions to check whether the predicted
confidence is calibrated to actual correctness.

Predictions:
{{predictions}}

Steps:
1. Bucket records by predicted_confidence:
   - If confidence is "high" / "medium" / "low" labels, use those.
   - If numeric (0-1), bucket into 5 ranges: [0-0.2), [0.2-0.4),
     [0.4-0.6), [0.6-0.8), [0.8-1.0].

2. For each bucket compute:
   - count: number of records
   - actual_accuracy: fraction with actual_correctness=true
   - expected_accuracy: midpoint of confidence range (e.g. high =
     0.85 if not specified, medium = 0.6, low = 0.3) OR provided
     numeric bucket midpoint

3. Compute calibration_error per bucket = |actual - expected|.

4. Identify regions:
   - "over_confident" : actual_accuracy < expected_accuracy by ≥ 0.1
                        (model says high but is often wrong)
   - "under_confident": actual_accuracy > expected_accuracy by ≥ 0.1
                        (model is more accurate than it claims)
   - "calibrated"     : within 0.1 of expected

5. Compute aggregate Expected Calibration Error (ECE) = weighted
   average of |actual - expected| across buckets, weighted by
   bucket count.

6. If `category` field is present in some records, also report
   per-category calibration to surface which task types are
   miscalibrated.

Return ONLY this JSON object:
{
  "buckets": [
    {
      "confidence": "<label or range>",
      "count": <integer>,
      "actual_accuracy": <float 0-1>,
      "expected_accuracy": <float 0-1>,
      "calibration_error": <float>,
      "verdict": "over_confident" | "under_confident" | "calibrated"
    }
  ],
  "expected_calibration_error": <float 0-1>,
  "calibration_overall": "well_calibrated" | "slightly_miscalibrated" | "poorly_miscalibrated",
  "primary_issue": "over_confidence" | "under_confidence" | "noise" | "none",
  "per_category": [
    {"category": "<name>", "ece": <float>, "primary_issue": "<short>"}
  ],
  "n_records_analyzed": <integer>,
  "recommendation": "<one sentence>",
  "decision_basis": "<one sentence, <=40 words, no internal CoT>"
}

Calibration overall:
- "well_calibrated"        : ECE < 0.05
- "slightly_miscalibrated" : 0.05 ≤ ECE < 0.15
- "poorly_miscalibrated"   : ECE ≥ 0.15
```

## Example

**Input:**

```text
predictions: <50 records of judge confidence + actual ground-truth correctness>
```

**Expected output:**

```json
{
  "buckets": [
    {"confidence": "high", "count": 32, "actual_accuracy": 0.69, "expected_accuracy": 0.85, "calibration_error": 0.16, "verdict": "over_confident"},
    {"confidence": "medium", "count": 13, "actual_accuracy": 0.62, "expected_accuracy": 0.60, "calibration_error": 0.02, "verdict": "calibrated"},
    {"confidence": "low", "count": 5, "actual_accuracy": 0.40, "expected_accuracy": 0.30, "calibration_error": 0.10, "verdict": "under_confident"}
  ],
  "expected_calibration_error": 0.13,
  "calibration_overall": "slightly_miscalibrated",
  "primary_issue": "over_confidence",
  "per_category": [],
  "n_records_analyzed": 50,
  "recommendation": "The judge is significantly over-confident on its 'high' bucket — high-labeled outputs are correct only ~70% of the time, not ~85%. Either tighten the bar for 'high' in the judge prompt OR apply temperature scaling to the high bucket downstream.",
  "decision_basis": "ECE 0.13 driven by over-confidence on the 32-record 'high' bucket; medium and low are reasonably calibrated."
}
```

## Failure Modes

- **Small bucket noise** — bucket with <10 records produces unstable
  accuracy estimate. Track count per bucket; flag as preliminary
  if any bucket count <10.
- **Confidence label mapping wrong** — "high" mapped to 0.7 expected
  vs 0.85 expected gives different verdicts. The default mapping
  is conservative (0.85/0.6/0.3); document if you change it.
- **Per-category ignored** — model returns empty per_category when
  data has category field. Sample records: if `category` field
  exists in inputs but per_category is empty, the rubric was lazy.
- **Recommendation hand-waving** — "improve calibration" is not
  actionable. Each recommendation should name a specific direction
  (tighten judge, apply temp scaling, retrain, increase sample
  size).
- **Over-confidence as accuracy issue** — confusing "model is wrong"
  with "model is over-confident". The rubric is about whether
  confidence MATCHES accuracy, not whether accuracy is high.

## Tuning Notes

- 模型差异：本卡任务相对简单（分桶 + 算 accuracy），中档模型够用。
  frontier 模型在 recommendation 写作上更具体。
- 温度：`0.0`，统计分析必须可重现。
- 数据规模：<30 records 视为先导观察，统计意义弱。生产 calibration
  check 建议 ≥200 records，per-category 时 per-category ≥50。
- 与 `eval/judge-bias-probe` 的关系：bias-probe 检测 systematic biases
  (length, position, format)；本卡检测 calibration（confidence 准
  不准）。互补：一个 judge 可能 calibrated 但有 bias，或反过来。
- 与 `eval/pointwise-quality-scorer` 的 confidence 字段的关系：那张
  卡产 confidence 标签；本卡评估那些 confidence 是否真的准。形成
  自评 → calibration check 闭环。
- 应用场景：
  - 部署前：跑 calibration check 决定是否信任 confidence labels 自动化
  - 训练后：calibration error 是 model quality 的重要补充指标
  - A/B：两个版本 calibration ECE 对比，哪个更"诚实"
- 后处理：检测出 miscalibration 后，常用 fix 是 temperature scaling
  / Platt scaling — 都是后训练 calibration 技术。本卡不实施修复，
  只诊断。

## Changelog

- `0.1.0` — Initial card.
