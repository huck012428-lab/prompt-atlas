---
id: rag/retrieval-relevance-evaluator
title: Retrieval Relevance Evaluator
version: 0.1.0
status: stable
direction: rag
tags: [retrieval, scoring, eval-set, grounding]
audience: [llm-trainer, eval-team, ai-pm]
models: [generic, frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: query
    description: The user query that drove retrieval.
    required: true
  - name: passage
    description: A single retrieved passage to score.
    required: true
---

> 🎯 **场景**：评估检索到的 passage 与 query 的相关性，0/1/2 三档打分 + 理由 + 支撑短语。RAG eval-set 构建和 retriever 质量评估的标配。

## Quick Use

**Use when:** You want to score whether a retrieved passage is relevant to a search query.
**Fill in:** `{{query}}` = the search query; `{{passage}}` = the retrieved text to score.
**You'll get:** A 0/1/2 relevance score, a one-sentence reason, and the supporting phrase from the passage. Output is JSON.

## Purpose

Score whether a single retrieved passage is relevant to a query, with a short
rationale. Used during RAG eval-set construction and offline retriever quality
analysis. Produces a structured JSON record per (query, passage) pair so that
many records can be aggregated into precision@k / recall@k metrics or fed into
a learned reranker as labels.

## Prompt

```text
You are a retrieval relevance evaluator. Decide whether the passage contains
information that helps answer the query.

Query:
{{query}}

Passage:
{{passage}}

Scoring rubric:
- 2 = passage directly answers the query or contains the key fact needed.
- 1 = passage is on-topic and useful context but does not directly answer.
- 0 = passage is off-topic, contradictory, or contains no useful information.

Return ONLY a JSON object with this exact shape:
{
  "score": <0 | 1 | 2>,
  "rationale_summary": "<one sentence, <=30 words, no internal CoT, no quotes from passage>",
  "supporting_span": "<short verbatim span from passage that justifies the score, or empty string if score=0>"
}
```

## Example

**Input:**

```text
query: "What year did Voyager 1 cross the heliopause?"
passage: "Voyager 1 entered interstellar space on August 25, 2012, when it crossed the heliopause."
```

**Expected output:**

```json
{
  "score": 2,
  "rationale_summary": "Passage states the heliopause crossing date directly.",
  "supporting_span": "Voyager 1 entered interstellar space on August 25, 2012"
}
```

## Failure Modes

- **Score inflation on topical-but-unhelpful passages** — model gives 2 when
  the passage is on-topic but does not contain the answer. Detect by sampling
  score=2 records and checking whether `supporting_span` actually answers the
  query. Mitigation: tighten the rubric wording; add 1–2 negative few-shots.
- **Long rationales / hidden reasoning leakage** — model writes paragraph-long
  rationales. The 30-word cap and the `rationale_summary` field name (not
  `chain_of_thought`) help; reject overlong rationales at parse time.
- **JSON drift** — extra prose around the JSON object on weaker models.
  Wrap with a strict JSON-only re-prompt or use a JSON-mode call.

## Tuning Notes

- 模型差异：frontier 模型在 0/1/2 三档上区分度好；7B 级开源模型容易把 1 和 2
  混淆，建议改成两档（相关 / 不相关）或加 3–5 个 few-shot。
- 温度：建议 `0.0`，分数稳定性优先。
- 评估集：跑此卡前先用 20–50 个人工标注样本估计模型与人工的 Cohen's kappa；
  低于 0.6 不建议用作硬标签，可降级为软监督信号。
- `supporting_span` 用于事后审核——它让低分样本和高分样本都能被快速复核，
  比单纯保存分数有用得多。

## Changelog

- `0.1.0` — Initial card.
