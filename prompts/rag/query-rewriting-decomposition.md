---
id: rag/query-rewriting-decomposition
title: Query Rewriting and Decomposition for Retrieval
version: 0.1.0
status: stable
direction: rag
tags: [query-rewriting, retrieval, decomposition, structured-output]
audience: [prompt-engineer, app-builder, ai-pm]
models: [generic, frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: text
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: original_query
    description: The user's raw query as typed.
    required: true
  - name: max_subqueries
    description: Cap on how many sub-queries to emit (small integer, typically 3 to 5).
    required: true
---

> 🎯 **场景**：把一个复合 query 拆成 3-5 个 focused 子查询，提升 RAG 检索召回率。在检索之前用，每个子查询独立检索后再融合。

## Quick Use

**Use when:** You want to split a single complex query into focused sub-queries before retrieval.
**Fill in:** `{{original_query}}` = the user's raw query; `{{max_subqueries}}` = a small number, typically 3 to 5.
**You'll get:** A list of self-contained sub-queries each with the facet they target, plus a short reasoning summary. Output is JSON.

## Purpose

Rewrite a single user query into a small set of focused sub-queries that
together are more likely to retrieve all relevant context for the original
ask. Used at query time, before vector / lexical search, to handle
under-specified, multi-aspect, or compound questions. Produces structured
JSON so the downstream retriever can run each sub-query independently and
the orchestrator can fuse results.

## Prompt

```text
You rewrite a user query into a small set of focused sub-queries for
retrieval. Goal: maximize the chance that retrieving each sub-query
independently surfaces all the context needed to answer the original query.

Rules:
1. Emit at most {{max_subqueries}} sub-queries. Use fewer when the query
   is already focused.
2. Each sub-query must be a self-contained search query — no pronouns
   referring to other sub-queries, no "and also" conjunctions hiding
   multiple aspects.
3. Preserve named entities, numbers, and dates verbatim from the original.
4. If the original query is already well-formed and atomic, return it as
   a single sub-query unchanged.
5. Do NOT invent constraints, time ranges, or entities that are not in
   the original query.

Original query:
{{original_query}}

Return ONLY this JSON object:
{
  "subqueries": [
    {"text": "<sub-query 1>", "aspect": "<one short phrase: which facet of the original this targets>"},
    /* ... up to {{max_subqueries}} entries */
  ],
  "reasoning_summary": "<<=30 words explaining how the original was decomposed; user-visible, not internal CoT>"
}
```

## Example

**Input:**

```text
original_query: "How does Voyager 1's interstellar communication compare to the Deep Space Network's coverage of New Horizons after 2020?"
max_subqueries: 4
```

**Expected output:**

```json
{
  "subqueries": [
    {"text": "Voyager 1 interstellar communication system specifications", "aspect": "Voyager 1 comm capabilities"},
    {"text": "Deep Space Network coverage of New Horizons after 2020", "aspect": "DSN coverage of New Horizons"},
    {"text": "Voyager 1 signal strength and data rate from interstellar space", "aspect": "Voyager 1 link quality"},
    {"text": "DSN antenna allocation policies for outer solar system probes", "aspect": "DSN allocation policy"}
  ],
  "reasoning_summary": "Split a comparative question into one sub-query per probe's communication facts plus a policy sub-query that bridges them."
}
```

## Failure Modes

- **Over-decomposition** — model splits an already-atomic query into N
  near-duplicates, hurting retrieval precision and wasting calls. Detect
  by comparing token-level Jaccard between sub-queries; reject batches
  with mean similarity > 0.85.
- **Constraint hallucination** — adds a year, location, or qualifier not
  in the original ("Voyager 1 in 2024..." when the original said no year).
  Detect by checking that all named entities and numbers in sub-queries
  also appear in the original.
- **Lost specificity** — generalizes a precise query into vague aspects
  ("space exploration" instead of "Voyager 1 communication"). Detect by
  measuring whether the original's rare terms survive in at least one
  sub-query.
- **Pronoun leakage** — sub-query 2 says "its signal strength" referring
  back to sub-query 1, breaking independent retrieval. Mitigation: the
  prompt's rule 2 helps; reject any sub-query containing third-person
  pronouns referring to entities not named within it.

## Tuning Notes

- 模型差异：弱模型（7B 级）容易出现 over-decomposition 和约束幻觉；建议
  在弱模型上把 `max_subqueries` 限到 2–3 并增加一个 verifier 步骤过滤。
- 温度：`0.0`–`0.3`。多样性不是这里的目标，稳定的 decomposition 是。
- 与 fusion 的关系：本卡只负责出 sub-queries，结果如何 fuse（RRF /
  weighted / 重排）由检索层决定。如果 downstream 用 RRF，建议 sub-query
  数量 3–5 较合适。
- 与 HyDE 的关系：本卡和 `rag/hyde-hypothetical-answer-generator` 互补
  而非替代——前者把 query 拆细，后者把 query 改写成更接近文档的形式。

## Changelog

- `0.1.0` — Initial card.
