---
id: rag/query-fusion
title: Query Fusion (combine sub-query results into ranked set)
version: 0.1.0
status: stable
direction: rag
tags: [retrieval, synthesis, structured-output, ranking]
audience: [app-builder, prompt-engineer, llm-trainer]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: original_query
    description: The original user query (before decomposition).
    required: true
  - name: subquery_results
    description: A JSON array of objects, each containing `subquery_text`, `passages` (array of passage objects with id + text + retrieval_score). Typically 3-5 sub-queries each with 5-10 passages.
    required: true
---

> 🎯 **场景**：把 `rag/query-rewriting-decomposition` 拆出的多个子查询的检索结果**融合**成一个排序集——按对原 query 的整体覆盖排序，去重 near-duplicate，标记每条来自哪个 sub-query。是 query-decomposition 的 "fan-in" 步骤。

## Quick Use

**Use when:** You decomposed a query into sub-queries, retrieved separately, and now need to fuse the per-sub-query result sets into one deduplicated, ranked set.
**Fill in:** `{{original_query}}` = original user query; `{{subquery_results}}` = JSON array of (subquery, passages) pairs.
**You'll get:** A unified ranked passage list with deduplication, source-subquery attribution, and per-passage reasoning. Output is JSON.

## Purpose

Fuse retrieval results from multiple sub-queries into a single
ranked, deduplicated set, ranked by relevance to the ORIGINAL query
(not to each sub-query). Used as the fan-in step after
`rag/query-rewriting-decomposition`. Distinct from
`rag/multi-source-aggregator`: that card synthesizes an answer; this
card produces the fused passage set used as input to answering.

## Prompt

```text
You fuse retrieval results from multiple sub-queries into one ranked
passage set, ranked by relevance to the ORIGINAL query.

Original query:
{{original_query}}

Sub-query results (each sub-query has its own passages):
{{subquery_results}}

Steps:
1. Walk through all passages across all sub-queries.
2. Identify near-duplicates (same chunk surfaced via different
   sub-queries; same fact stated in different passages). Group
   them; pick the most informative representative.
3. Rank the deduplicated set by relevance to the ORIGINAL query
   (not to any single sub-query). A passage that addresses two
   different sub-queries should rank higher than one that addresses
   only one.
4. For each kept passage, note which sub-queries surfaced it.
5. Drop passages that don't bear on the original query at all
   (sub-query may have over-decomposed).

Return ONLY this JSON object:
{
  "fused_passages": [
    {
      "passage_id": "<original id>",
      "rank": <integer>,
      "from_subqueries": ["<subquery text>", "..."],
      "relevance_to_original": "high" | "medium" | "low",
      "rationale": "<one short phrase: how this contributes to original_query>"
    }
  ],
  "duplicates_merged": <integer count>,
  "passages_dropped": <integer count>,
  "coverage_check": {
    "subqueries_with_no_kept_passages": ["<subquery text>"],
    "missing_aspects_of_original": ["<aspect of original_query not covered by any kept passage>"]
  },
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

Two sub-queries about Reykjavik (population, weather), each retrieved
3 passages, some passages overlap.

**Expected output (abridged):**

```json
{
  "fused_passages": [
    {"passage_id": "p1", "rank": 1, "from_subqueries": ["Reykjavik population 2024", "Reykjavik facts"], "relevance_to_original": "high", "rationale": "Covers two sub-queries — population number and general overview."},
    {"passage_id": "p3", "rank": 2, "from_subqueries": ["Reykjavik population 2024"], "relevance_to_original": "high", "rationale": "Population statistics with citation."}
  ],
  "duplicates_merged": 1,
  "passages_dropped": 1,
  "coverage_check": {
    "subqueries_with_no_kept_passages": [],
    "missing_aspects_of_original": []
  },
  "decision_basis": "Two distinct passages kept; one near-duplicate merged into rank-1; one off-topic passage dropped."
}
```

## Failure Modes

- **Reciprocal-rank-fusion blindness** — model uses each sub-query's
  retrieval_score directly, ignoring that scores aren't
  comparable across sub-queries. Mitigation: rule "rank by
  relevance to ORIGINAL query"; verify rationale references the
  original query.
- **Duplicate keeping** — same chunk appears at rank 1 and rank 5;
  model didn't detect duplication. Audit by checking passage_id
  uniqueness in fused_passages.
- **Coverage blindness** — model drops passages from a sub-query
  entirely, missing an aspect of the original. The coverage_check
  field surfaces this; verify subqueries_with_no_kept_passages is
  empty unless the sub-query was off-topic.
- **Hallucinated rationale** — rationale describes content not in
  the passage. Sample and check.

## Tuning Notes

- 模型差异：frontier 模型在 cross-subquery deduplication 上更稳；
  中档模型容易把"提到同一实体"误判为 near-duplicate。
- 温度：`0.0`–`0.2`。
- 与 `rag/query-rewriting-decomposition` 的关系：那张卡是 fan-out
  （一个 query 拆成 N 个 sub-query）；本卡是 fan-in（N 个 sub-query
  的结果合一）。组合是 multi-query RAG 的标准模式。
- 与 reciprocal rank fusion (RRF) 算法的关系：传统 RRF 是基于
  retrieval_score 的数学融合；本卡是基于语义理解的融合。前者更便宜
  快，后者更准。生产中可以叠加：先 RRF 粗排到 top-20，再用本卡精
  fuse 到 top-10。
- 与 `rag/multi-source-aggregator` 的关系：本卡产 fused passage 集
  （检索阶段产物）；那张卡产合成 answer（生成阶段产物）。pipeline:
  decompose → retrieve per-sub → fuse (本卡) → aggregate answer。
- coverage_check 的下游：missing_aspects_of_original 非空时触发追
  加 retrieval（用未覆盖的 aspect 作新 query）。

## Changelog

- `0.1.0` — Initial card.
