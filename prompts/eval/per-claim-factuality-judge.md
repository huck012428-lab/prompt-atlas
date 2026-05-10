---
id: eval/per-claim-factuality-judge
title: Per-claim Factuality Judge (atomic decomposition)
version: 0.1.0
status: stable
direction: eval
tags: [llm-judge, factuality, scoring, structured-output, extraction]
audience: [eval-team, llm-trainer, ai-pm]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: model_output
    description: The model's output to be fact-checked, claim by claim.
    required: true
  - name: domain_hint
    description: Optional one-line hint about the domain/topic to help the judge calibrate (e.g. "biology, undergraduate level"). Pass empty string if not applicable.
    required: false
---

## Purpose

Decompose a model output into atomic factual claims and label each as
true, false, unverifiable, or non-factual (opinion / interpretation / not
a factual statement). Used for fine-grained factuality benchmarks where
a single output-level "correct / incorrect" label is too coarse — long-
form generation, explanation tasks, multi-claim summaries. Output is
structured so per-output factuality precision (true / labeled-factual)
can be aggregated.

## Prompt

```text
You are a per-claim factuality judge. Decompose the model output into
atomic factual claims, then label each claim.

Model output:
{{model_output}}

Domain hint (optional, may be empty):
{{domain_hint}}

Steps:
1. Split the model output into atomic factual claims. Skip:
   - Opinions / value judgments ("X is the best...")
   - Hedges that do not assert a fact ("It might be that...")
   - Pure framing ("Here is the answer:")
   - Restatements of the question
2. For each claim, label it:
   - "true"          — the claim is factually correct given commonly
                       accepted knowledge in the relevant domain.
   - "false"         — the claim is factually incorrect.
   - "unverifiable"  — the claim is specific and verifiable in
                       principle, but you cannot confidently verify it
                       without external lookup (e.g. specific numbers
                       you do not know, recent events you cannot
                       confirm).
   - "non_factual"   — on second look, this is not actually a factual
                       claim (slipped through step 1). Use sparingly.

Return ONLY this JSON object:
{
  "claims": [
    {"text": "<atomic claim 1>", "label": "true" | "false" | "unverifiable" | "non_factual",
     "decision_basis": "<one short phrase, <=20 words; no internal CoT>"},
    /* ... one entry per claim */
  ],
  "factual_precision": <float 0.0 to 1.0: true / (true + false), or null if denominator is 0>,
  "summary_basis": "<one sentence, <=40 words, summarizing the overall factual quality>"
}

Be strict about "true": prefer "unverifiable" if you do not actually
know the fact. Calibration matters more than coverage.
```

## Example

**Input:**

```text
model_output: "The Great Pyramid of Giza was built around 2560 BCE for Pharaoh Khufu and is the only one of the Seven Wonders of the Ancient World still standing. It is composed entirely of limestone blocks and stands 200 meters tall."
domain_hint: "Egyptology, general knowledge"
```

**Expected output:**

```json
{
  "claims": [
    {"text": "The Great Pyramid of Giza was built around 2560 BCE", "label": "true", "decision_basis": "Standard accepted dating in Egyptology."},
    {"text": "The Great Pyramid was built for Pharaoh Khufu", "label": "true", "decision_basis": "Khufu is the universally cited builder."},
    {"text": "The Great Pyramid is the only one of the Seven Wonders of the Ancient World still standing", "label": "true", "decision_basis": "Standard claim in classical lists."},
    {"text": "The Great Pyramid is composed entirely of limestone blocks", "label": "false", "decision_basis": "It also contains granite, especially in the King's Chamber."},
    {"text": "The Great Pyramid stands 200 meters tall", "label": "false", "decision_basis": "Original height was approximately 146 meters; current is around 139 meters."}
  ],
  "factual_precision": 0.6,
  "summary_basis": "Three out of five atomic claims are correct; two contain hard factual errors about composition and height."
}
```

## Failure Modes

- **Model knowledge limits** — judge marks a claim "true" because it
  matches the judge model's stale or incomplete training data, even when
  the claim is wrong. Mitigation: for high-stakes evals, prefer "judge +
  retrieval" (see `rag/answer-grounding-checker`) over closed-book
  factuality judging. Treat closed-book judgments as signals, not
  ground truth.
- **Over-confident "true"** — judge marks specific numbers / dates as
  true when it is actually guessing. Mitigation: the prompt's "prefer
  unverifiable if you do not actually know" line; spot-check claims
  labeled true that contain specific numbers and re-rate against an
  external source.
- **Atomization failure** — judge produces compound claims joined by
  "and", which then get a single label that masks half-correct
  outputs. Detect by rejecting claims containing top-level conjunctions.
- **Domain miscalibration** — without `domain_hint`, judge applies
  general-knowledge thresholds to specialist content (medicine, law,
  niche history). Mitigation: pass a domain_hint when the output is
  domain-specific; consider a domain-tuned judge model.
- **Opinion creep** — judge treats "X is the most important Y" as a
  factual claim. Use `non_factual` label sparingly to flag these without
  destroying precision metrics.

## Tuning Notes

- 模型差异：必须用 frontier 模型作为 judge。中档模型在"不知道但说知道"
  这一项上失败率明显更高。
- 温度：`0.0`。
- factual_precision 仅以 (true / (true + false)) 计算，主动排除
  unverifiable 和 non_factual——这是有意为之，避免"判官不会就给好分"
  导致的 metric 膨胀。
- 与 `rag/answer-grounding-checker` 的关系：本卡 closed-book，无需
  retrieved context；answer-grounding-checker open-book，需要明确的
  context。前者衡量"模型自己知不知道"，后者衡量"模型答案是否扎根
  在给定 context"，两者评估的是不同维度的 factuality。
- 高敏场景（医疗、法律、金融）：closed-book judge 不够，需要"judge +
  外部知识库"组合。本卡可作为 first-pass，再把可疑 claim 送外部核查。

## Changelog

- `0.1.0` — Initial card.
