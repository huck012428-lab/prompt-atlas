---
id: eval/judge-bias-probe
title: LLM Judge Bias Probe (length / position / format / verbosity)
version: 0.1.0
status: experimental
direction: eval
tags: [llm-judge, scoring, classification, structured-output]
audience: [eval-team, llm-trainer, ai-pm]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: judge_outputs
    description: A JSON array of judgment records — each record contains the prompt, the response, the judge's verdict / score, and optional metadata (length, position, format-class). Typical batch 50-500 records.
    required: true
---

> 🎯 **场景**：诊断 LLM judge 自身有没有偏见——长 vs 短、A 位置 vs B 位置、bullet vs prose、verbose vs terse 等。给一批 judge 输出，本卡返回每种偏见的检测结果 + 严重度。LLM-as-judge pipeline 上线前必备 sanity check。

## Quick Use

**Use when:** You're using an LLM as a judge in production and want to verify it doesn't have systemic bias on length / position / format dimensions before trusting its scores.
**Fill in:** `{{judge_outputs}}` = JSON array of judgment records (prompt, response, verdict, metadata fields).
**You'll get:** Per-bias detection results (which biases detected, evidence, severity) and an overall trust signal. Output is JSON.

## Purpose

Probe an LLM-as-judge for systematic biases that would invalidate
its scores. Common biases tested: (1) **length bias** — does the
judge prefer longer responses regardless of substance? (2) **position
bias** — in pairwise judging, does the first-shown response win
disproportionately? (3) **format bias** — does the judge prefer
bullets / specific Markdown? (4) **verbosity bias** — does the judge
reward "showing your work" over concise correctness? (5) **self-
preference** — when judging outputs from the same model family.

Used as pre-launch sanity check on any LLM-as-judge pipeline. Output
is structured so individual biases can be tracked over time and
mitigation strategies (length normalization, position randomization)
can be tied to specific biases detected.

## Prompt

```text
You diagnose biases in an LLM judge by analyzing a batch of its
judgment records. The data is already collected; you analyze it for
systematic patterns.

Judge outputs (batch of records, each with prompt / response /
verdict / metadata):
{{judge_outputs}}

Bias categories to check:
1. "length_bias"     : Does the judge favor longer responses?
                       Compare verdict distribution across response
                       length quartiles.
2. "position_bias"   : For pairwise records, does the judge prefer
                       the first-shown option disproportionately?
                       Need metadata.position field.
3. "format_bias"     : Does the judge prefer bulleted / formatted
                       responses over equivalent prose? Need
                       metadata.format_class field.
4. "verbosity_bias"  : Does the judge prefer "show your reasoning"
                       responses over concise correct ones? Look at
                       responses with reasoning_visible vs not.
5. "self_preference" : Does the judge prefer outputs from a specific
                       model family disproportionately? Need
                       metadata.model_family field.

For each bias category, classify detection:
- "not_detected"  : Distribution looks balanced, or insufficient
                    metadata to test.
- "weak"          : Slight skew (e.g. 5-10% above neutral baseline).
- "moderate"      : Clear skew (10-25% above baseline).
- "strong"        : Severe skew (>25% above baseline) — judge
                    scores are unreliable on this axis.

Provide concrete evidence: cite specific count comparisons or rate
gaps from the data.

Return ONLY this JSON object:
{
  "bias_results": [
    {
      "category": "<one of the 5>",
      "detection": "not_detected" | "weak" | "moderate" | "strong",
      "evidence": "<concrete count / rate observation from the data, e.g. 'top length quartile won 73% of pairwise vs bottom quartile 27%'>",
      "metadata_required": "<which metadata field needed; if missing in data, say 'metadata field X not present in inputs'>",
      "mitigation": "<for weak+ detections: short suggested mitigation>"
    }
  ],
  "overall_judge_trustworthy": true | false,
  "trustworthy_reason": "<one sentence>",
  "n_records_analyzed": <integer>,
  "decision_basis": "<one sentence, <=40 words, no internal CoT>"
}

Trust rule:
- overall_judge_trustworthy: false if any "strong" detected, OR
  two+ "moderate" detected.
- overall_judge_trustworthy: true otherwise.
```

## Example

**Input:**

```text
judge_outputs: [
  /* 50 pairwise records with metadata: position (a or b), response_a_length, response_b_length, judge picked: a or b */
  {"id": 1, "judge_picked": "a", "metadata": {"position_a_length": 320, "position_b_length": 180}},
  {"id": 2, "judge_picked": "a", "metadata": {"position_a_length": 50, "position_b_length": 480}},
  /* ... 48 more records ... */
]
```

**Expected output:**

```json
{
  "bias_results": [
    {
      "category": "length_bias",
      "detection": "moderate",
      "evidence": "Across 50 pairwise records, the longer response won 32 / 50 (64%); for an unbiased judge expected ~25 / 50 (50%). Skew is 14 percentage points above neutral.",
      "metadata_required": "response_a_length and response_b_length present.",
      "mitigation": "Add 'do not reward verbosity' instruction; consider length-normalizing the prompt or pairing length-matched candidates."
    },
    {
      "category": "position_bias",
      "detection": "weak",
      "evidence": "First-position (A) won 28 / 50 (56%); marginal skew above 50% baseline.",
      "metadata_required": "position metadata present (always 'a' first).",
      "mitigation": "Run with positions swapped on a sample to confirm; if confirmed, randomize position at calling time."
    },
    {
      "category": "format_bias",
      "detection": "not_detected",
      "evidence": "metadata field 'format_class' not present in inputs; cannot test.",
      "metadata_required": "metadata.format_class (e.g. 'bulleted' / 'prose')",
      "mitigation": ""
    },
    {
      "category": "verbosity_bias",
      "detection": "not_detected",
      "evidence": "metadata field 'reasoning_visible' not present in inputs; cannot test directly. Length bias above suggests this may also be at play.",
      "metadata_required": "metadata.reasoning_visible (true/false)",
      "mitigation": ""
    },
    {
      "category": "self_preference",
      "detection": "not_detected",
      "evidence": "metadata field 'model_family' not present in inputs; cannot test.",
      "metadata_required": "metadata.model_family (e.g. 'gpt' / 'claude' / 'gemini')",
      "mitigation": ""
    }
  ],
  "overall_judge_trustworthy": false,
  "trustworthy_reason": "One moderate (length) and one weak (position) bias detected; combined effect makes pairwise scores unreliable until length is controlled.",
  "n_records_analyzed": 50,
  "decision_basis": "Length bias 64% (vs 50% neutral) is moderate; position bias 56% is weak; together unreliable for ranking decisions."
}
```

## Failure Modes

- **Insufficient data inferred as no bias** — model says
  "not_detected" on small samples (<30) when bias might exist.
  Mitigation: track n_records_analyzed; on small samples,
  "not_detected" should be paired with a note about statistical power.
- **Spurious detection on random noise** — small sample with
  random outcome flagged as bias. Real bias detection needs
  ~100+ records for confidence; flag detections on small samples
  as preliminary.
- **Metadata missing not flagged** — model invents bias detection
  for categories where data lacks the required metadata.
  `metadata_required` field exists for honesty about this.
- **Mitigation hand-waving** — "improve the prompt" as mitigation.
  Reject vague mitigations; each should be a concrete action
  (length normalization, position randomization, prompt change).
- **Aggregation method opaqueness** — `evidence` says "the judge
  is biased" without citing concrete counts. Reject any evidence
  not containing numbers from the data.
- **Trust signal flipping** — overall_judge_trustworthy: true while
  multiple moderates detected. Verify rule logic at parse time.

## Tuning Notes

- 模型差异：分析需要的统计推理能力中等；本卡更挑战的是"诚实地说出
  data 中真实呈现的 pattern"。frontier 模型必须的，否则容易给出
  好看但不准确的诊断。
- 温度：`0.0`，分析必须可重现。
- batch 规模建议：≥100 records per bias category for confidence。
  <50 视为先导观察，需要再跑一批。
- metadata field 规划：上线前 instrument judge pipeline，捕获
  position / response length / model_family / format_class / 
  reasoning_visible 等字段。否则本卡能查的偏见有限。
- 与 `eval/pairwise-judge-with-position-bias-probe` 的关系：那张卡
  在**单次**比较时主动控制 position bias（双向调用）；本卡在**事后**
  分析一批 judgment 检测哪些偏见已经发生。前者预防，后者诊断。
- 与 `eval/safety-output-classifier` 的关系：safety 分类是输出层
  评估；本卡是 judge 层评估。LLM-as-judge pipeline 一层比一层 meta，
  审 judge 是质量控制的高阶环节。
- mitigation 落地：每种 bias 都有标准 mitigation。length-bias 用
  length-normalization (length-controlled subset 重新跑判);
  position-bias 用 random shuffle 输入；format-bias 用 normalized
  format prompt。
- 上线前 baseline：保留一组人工 gold 标注的样本作 calibration
  reference。本卡跑判结果时连同 ground-truth 一起跑，看 judge 是否
  与人类一致——单纯有 bias 不一定坏，关键看是否影响最终 metric。

## Changelog

- `0.1.0` — Initial card.
