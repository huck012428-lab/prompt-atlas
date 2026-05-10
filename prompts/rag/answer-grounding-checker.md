---
id: rag/answer-grounding-checker
title: Answer Grounding Checker (hallucination detector)
version: 0.1.0
status: stable
direction: rag
tags: [grounding, factuality, scoring, structured-output, eval-set]
audience: [eval-team, llm-trainer, ai-pm, app-builder]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The original question the answer was generated to address.
    required: true
  - name: retrieved_context
    description: The full retrieved context (concatenated passages) the model had access to.
    required: true
  - name: answer
    description: The model's final answer to be checked for grounding.
    required: true
---

## Purpose

Decompose a RAG answer into atomic claims and label each one as supported,
unsupported (i.e. hallucinated), or contradicted relative to the retrieved
context. Used as the primary hallucination detector for RAG systems where
no per-claim citation is available — answer-level grounding rather than
citation-level. Output is structured so a hallucination rate can be
computed and individual unsupported claims can be surfaced for review.

## Prompt

```text
You audit a RAG answer for grounding. Decompose the answer into atomic
claims, then label each claim against the retrieved context.

Question:
{{question}}

Retrieved context:
{{retrieved_context}}

Answer to audit:
{{answer}}

Steps:
1. Extract atomic factual claims from the answer (one fact per claim).
   Skip claims that are pure restatements of the question, generic
   framing ("Here is the answer"), or instructions to the user.
2. For each claim, label it relative to the retrieved context:
   - "supported"     — context directly entails the claim.
   - "unsupported"   — context does not contain enough information to
                       verify the claim (the claim may be true in the
                       world, but it is not grounded in this context).
   - "contradicted"  — context contains information that contradicts
                       the claim.
3. Compute hallucination_rate = (unsupported + contradicted) / total.

Return ONLY this JSON object:
{
  "claims": [
    {"text": "<atomic claim 1>", "label": "supported" | "unsupported" | "contradicted",
     "evidence_phrase": "<verbatim sub-string of retrieved_context, or empty if label != supported>"},
    /* ... one entry per atomic claim */
  ],
  "hallucination_rate": <float 0.0 to 1.0>,
  "decision_basis": "<one sentence, <=40 words, no internal CoT>"
}

Be strict: a claim is supported ONLY if a verbatim or trivially
paraphrased phrase in the context entails it. Common-knowledge true
claims that are NOT in the context are "unsupported", not "supported".
```

## Example

**Input:**

```text
question: "When did the Hubble Space Telescope launch and what mission deployed it?"
retrieved_context: "The Hubble Space Telescope was deployed from Space Shuttle Discovery on April 25, 1990, during STS-31. It has since been serviced five times."
answer: "Hubble launched on April 24, 1990 from Space Shuttle Atlantis as part of mission STS-31, and is the largest space telescope ever built."
```

**Expected output:**

```json
{
  "claims": [
    {"text": "Hubble launched on April 24, 1990", "label": "contradicted", "evidence_phrase": ""},
    {"text": "Hubble launched from Space Shuttle Atlantis", "label": "contradicted", "evidence_phrase": ""},
    {"text": "Hubble was deployed as part of mission STS-31", "label": "supported", "evidence_phrase": "during STS-31"},
    {"text": "Hubble is the largest space telescope ever built", "label": "unsupported", "evidence_phrase": ""}
  ],
  "hallucination_rate": 0.75,
  "decision_basis": "Date and shuttle are contradicted by the context, the largest-telescope claim is not in the context, and only the mission ID is supported."
}
```

## Failure Modes

- **Common-knowledge leakage** — judge marks a claim "supported" because
  the judge itself knows the fact, even when the context is silent.
  Mitigation: the rubric explicitly says "common-knowledge true claims
  not in the context are unsupported"; verify by checking
  `evidence_phrase` is non-empty for every "supported" label.
- **Paraphrase blindness** — judge marks a claim "unsupported" when the
  context entails it via a clear paraphrase. Mitigation: at temperature
  0 the model tends to be too literal; sample multiple judgments and
  take majority vote on disputed claims.
- **Claim atomization failure** — model produces compound claims ("X
  and Y on date Z"), making per-claim labels unscorable. Detect by
  checking that no claim contains conjunctions; reject and re-prompt
  with a sharper atomicity instruction.
- **Skipping framing claims is asymmetric** — sometimes the model
  treats hedges like "according to the source" as a claim, sometimes
  not. This is acceptable noise as long as the hallucination_rate
  trend is consistent across runs.

## Tuning Notes

- 模型差异：judge 应该是 frontier 模型。中档模型在 unsupported vs
  contradicted 的区分上不稳定，可降级为二档（grounded / not_grounded）
  以提升一致性。
- 温度：`0.0`，必要时跑 3 次取多数票。
- 与 `rag/citation-faithfulness-scorer` 的关系：当系统输出带 explicit
  citations 时优先用 citation-faithfulness-scorer（更精细）；当系统输出
  是裸答案时用本卡。两者可以叠加：先用 citation-faithfulness 审 cited
  spans，再用本卡审整体 grounding。
- 用作训练信号：`hallucination_rate` 是 RAG eval 的关键指标；建议同时
  跟踪三个分量比例（supported / unsupported / contradicted），单看
  hallucination_rate 会掩盖"不答"和"答错"的本质差异。
- context 长度：retrieved_context 过长（>10k tokens）会让 judge 变懒；
  必要时先做 context 截断或 per-passage 切分跑多次。

## Changelog

- `0.1.0` — Initial card.
