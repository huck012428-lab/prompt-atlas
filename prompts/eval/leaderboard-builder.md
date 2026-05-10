---
id: eval/leaderboard-builder
title: Multi-Benchmark Leaderboard Builder
version: 0.1.0
status: stable
direction: eval
tags: [comparative, scoring, structured-output]
audience: [eval-team, ai-pm, llm-trainer]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: model_results
    description: A JSON array of objects, each with `model_name` and `benchmarks` (object mapping benchmark_name → score in [0, 1] or 0-100).
    required: true
  - name: weights
    description: Optional JSON object mapping benchmark_name → weight. Weights need not sum to 1; will be normalized. Pass empty object for equal weights.
    required: false
---

> 🎯 **场景**：给一组模型在多个 benchmark 上的分数，做出**带 caveats 的 leaderboard**——加权排序、分项 ranking、识别"哪个 benchmark 是 differentiator"、每条 entry 标 strength / weakness。比简单平均靠谱。

## Quick Use

**Use when:** You have model results across multiple benchmarks and want a leaderboard with weighted overall ranking, per-benchmark rankings, and analysis of where models are strong / weak.
**Fill in:** `{{model_results}}` = JSON array of {model_name, benchmarks: {name: score}}; `{{weights}}` = optional benchmark weights.
**You'll get:** Overall ranking with weighted scores, per-benchmark ranking, model strength/weakness profile, and notes on differentiators. Output is JSON.

## Purpose

Aggregate model scores across multiple benchmarks into a usable
leaderboard. Beyond simple averaging: weighted aggregation, per-
benchmark sub-rankings, identification of differentiators (which
benchmark separates good from bad models), and per-model
strength/weakness profile. Used to summarize internal eval runs
or to prepare external benchmark comparisons honestly.

## Prompt

```text
You build a leaderboard from multi-benchmark model results.

Model results:
{{model_results}}

Weights (may be empty for equal weights):
{{weights}}

Steps:
1. Normalize all scores to [0, 1] (if some are 0-100 and others
   0-1, pick the canonical scale and convert).

2. Apply weights — normalize weights to sum to 1. Compute
   weighted_score per model = sum(score_b × normalized_weight_b)
   for each benchmark b.

3. Rank models by weighted_score for the headline ranking. Compute
   per-benchmark sub-rankings.

4. For each model, identify "strengths" (benchmarks where it
   ranks in top 1-2) and "weaknesses" (benchmarks where it ranks
   in bottom 1-2). If only 2 models, skip this.

5. Identify "differentiator_benchmarks" — benchmarks where the
   score range across models is widest. These are the ones that
   actually distinguish; benchmarks where everyone scores ~similar
   carry less ranking signal.

6. Note any caveats — score ranges that are very narrow (saturated
   benchmark), missing scores, etc.

Return ONLY this JSON object:
{
  "leaderboard": [
    {
      "rank": <integer>,
      "model_name": "<name>",
      "weighted_score": <float>,
      "per_benchmark_rank": {"<benchmark>": <integer>},
      "strengths": ["<benchmark name>"],
      "weaknesses": ["<benchmark name>"]
    }
  ],
  "differentiator_benchmarks": [
    {"benchmark": "<name>", "score_range": <float>, "explanation": "<short>"}
  ],
  "saturated_benchmarks": ["<benchmarks where scores cluster too tightly to rank>"],
  "caveats": ["<short>"],
  "summary": "<one or two sentences on the headline finding>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
model_results: [
  {"model_name": "ModelA", "benchmarks": {"factuality": 0.85, "reasoning": 0.72, "code": 0.90}},
  {"model_name": "ModelB", "benchmarks": {"factuality": 0.83, "reasoning": 0.85, "code": 0.65}},
  {"model_name": "ModelC", "benchmarks": {"factuality": 0.84, "reasoning": 0.70, "code": 0.55}}
]
weights: {"factuality": 1.0, "reasoning": 1.5, "code": 1.0}
```

**Expected output:**

```json
{
  "leaderboard": [
    {"rank": 1, "model_name": "ModelB", "weighted_score": 0.797, "per_benchmark_rank": {"factuality": 3, "reasoning": 1, "code": 2}, "strengths": ["reasoning"], "weaknesses": ["code"]},
    {"rank": 2, "model_name": "ModelA", "weighted_score": 0.785, "per_benchmark_rank": {"factuality": 1, "reasoning": 2, "code": 1}, "strengths": ["factuality", "code"], "weaknesses": []},
    {"rank": 3, "model_name": "ModelC", "weighted_score": 0.731, "per_benchmark_rank": {"factuality": 2, "reasoning": 3, "code": 3}, "strengths": [], "weaknesses": ["code", "reasoning"]}
  ],
  "differentiator_benchmarks": [
    {"benchmark": "code", "score_range": 0.35, "explanation": "Code scores span 0.55-0.90 — biggest discriminator across models."},
    {"benchmark": "reasoning", "score_range": 0.15, "explanation": "Moderate spread on reasoning."}
  ],
  "saturated_benchmarks": ["factuality"],
  "caveats": ["Factuality scores all cluster 0.83-0.85 (range 0.02) — close to saturation, may not distinguish models meaningfully.", "ModelA leads in 2 of 3 benchmarks but ranks #2 due to higher weight on reasoning."],
  "summary": "ModelB takes #1 due to reasoning weight despite ModelA leading more benchmarks; code is the main differentiator across the trio.",
  "decision_basis": "Weighted aggregation favors reasoning; rank order reflects weight × score; factuality saturated and provides little signal."
}
```

## Failure Modes

- **Saturation blindness** — all models cluster on benchmark X but
  ranking pretends X distinguishes them. The saturated_benchmarks
  field is the safety net.
- **Weight misnormalization** — weights summed wrong, weighted
  scores invalid. Validate at parse time.
- **Strength/weakness inflation** — every model gets 5 strengths.
  Cap to top 1-2; not every dimension is a strength.
- **Missing-score handling** — some models lack scores for some
  benchmarks. Should appear in caveats; verify.
- **Differentiator misranking** — narrow-range benchmark labeled as
  differentiator. Verify score_range matches the actual range.

## Tuning Notes

- 模型差异：本卡是数学聚合 + 文字总结；中档模型够用。
- 温度：`0.0`，统计聚合必须可重现。
- 数据规模：3-20 模型 × 3-15 benchmarks 是甜点。超过这个规模建议
  分维度做多个 leaderboard。
- 与 `eval/regression-detector` 的关系：那张卡是双版本对比；本卡是
  N 模型对比。前者纵向（同一模型不同版本），后者横向。
- 与 `eval/calibration-checker` 的关系：那张卡审 confidence；本卡聚合
  accuracy. 互补 — 一个模型可能 leaderboard 排第一但 calibration 差.
- weights 选择: 默认 equal 是 honest baseline. 加 weights 应当有
  business 理由（"我们更关心 reasoning 因为产品场景需要"）, 不是
  挑选有利权重让某模型赢.
- saturated_benchmarks 处理: 报告时应当声明哪些 benchmark 已经
  saturated, 不然 leaderboard 会 misleading（看似分数有差实际是噪声）.

## Changelog

- `0.1.0` — Initial card.
