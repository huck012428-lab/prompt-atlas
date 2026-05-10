---
id: rag/time-aware-retrieval-rewriter
title: Time-Aware Retrieval Query Rewriter
version: 0.1.0
status: stable
direction: rag
tags: [query-rewriting, retrieval, structured-output, generation]
audience: [app-builder, prompt-engineer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: user_query
    description: The user's query, possibly containing time-relative phrases.
    required: true
  - name: current_date
    description: The current date in YYYY-MM-DD format (so the model can resolve relative time phrases like "last week", "this year").
    required: true
---

> 🎯 **场景**：处理时间敏感 query 的检索改写——"上个月""最新""今年的 Q3"等相对时间词转成具体时间范围；明确"是要时点数据还是时段数据"；标记需要按时间过滤的字段。让 retrieval / vector store 能正确处理 freshness。

## Quick Use

**Use when:** Your RAG handles queries with time-relative phrases ("latest", "last quarter", "this year") and you need to resolve them into concrete time bounds before retrieval.
**Fill in:** `{{user_query}}` = the user query; `{{current_date}}` = today's date in YYYY-MM-DD.
**You'll get:** A rewritten query with explicit time bounds, time-filter metadata for the retriever, and a flag for time-sensitivity. Output is JSON.

## Purpose

Resolve time-relative phrases in queries into concrete time bounds
the retriever can use as filters. Handles three classes:
(1) explicit dates ("in 2023"), (2) relative phrases ("last month",
"recent"), (3) implicit recency expectations ("the new iPhone" —
no explicit time but freshness matters). Used as a query-time
preprocessing step in RAG pipelines that index time-varying content.

## Prompt

```text
You resolve time-relative phrases in a user query into concrete time
bounds the retriever can use.

User query:
{{user_query}}

Current date: {{current_date}}

Steps:
1. Decide if the query is time-sensitive:
   - "explicit"  : Contains specific dates / years / quarters.
   - "relative"  : Contains words like "latest", "recent", "last
                    month", "this year", "yesterday".
   - "implicit"  : No time language but freshness matters (current
                    events, prices, version-specific tech).
   - "atemporal" : Time doesn't matter (definitions, historical facts).

2. For sensitive queries, resolve to concrete bounds:
   - "last month" relative to {{current_date}} → ISO date range.
   - "this year" → from Jan 1 of current year to current_date.
   - "recent" → past 30 days as default; longer for slow-changing
     domains.
   - "latest" → strict descending sort, no specific bound.

3. Produce a rewritten query that includes the resolved time
   in plain text, AND structured time_filter metadata for the
   retriever.

Return ONLY this JSON object:
{
  "time_sensitivity": "explicit" | "relative" | "implicit" | "atemporal",
  "rewritten_query": "<query with time bounds spelled out>",
  "time_filter": {
    "from": "<YYYY-MM-DD or empty>",
    "to": "<YYYY-MM-DD or empty>",
    "sort_by_recency": true | false,
    "freshness_window_days": <integer or null>
  },
  "ambiguity_note": "<if time language was ambiguous, describe; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
user_query: "What were the latest iPhone reviews from last month?"
current_date: "2024-11-15"
```

**Expected output:**

```json
{
  "time_sensitivity": "relative",
  "rewritten_query": "iPhone reviews published between 2024-10-15 and 2024-11-15 (the previous month relative to today, 2024-11-15).",
  "time_filter": {
    "from": "2024-10-15",
    "to": "2024-11-15",
    "sort_by_recency": true,
    "freshness_window_days": 31
  },
  "ambiguity_note": "Used 'last month' as a rolling 30-day window from today rather than the calendar month October 2024; the user could plausibly have meant either.",
  "decision_basis": "Resolved 'last month' to past-30-days from current_date; sort by recency since 'latest' was also requested."
}
```

## Failure Modes

- **Wrong relative resolution** — "last week" interpreted as last
  calendar week vs past 7 days. Both are valid; the
  `ambiguity_note` should surface which was picked.
- **Atemporal query treated as time-sensitive** — "What is RAG?"
  given a time filter. Verify time_sensitivity classification on
  benchmarks.
- **Implicit-freshness blindness** — query like "iPhone 15 specs"
  marked atemporal because no time word; but iPhone 15 specs
  changed several times after launch. Audit
  technology / market queries specifically.
- **Future date hallucination** — model uses current_date that's
  inconsistent with what was passed. Validate that time_filter
  values relate to the input current_date.
- **Sort-by-recency over-trigger** — model sets sort_by_recency=true
  on queries that just want diverse coverage (research summaries),
  ranking by date and missing depth.

## Tuning Notes

- 模型差异：本卡需要日期算术 + 语境理解。中档模型在日期算术上偶尔
  错（"3 weeks ago" = 21 天 vs 3 个 calendar week 都可能）。
  frontier 模型更稳。
- 温度：`0.0`，时间解析必须可重现。
- current_date 来源：从 system / pipeline 取，不要让模型自己猜（避免
  cutoff drift）。
- 与 `rag/query-rewriting-decomposition` 的关系：可以串联——先 time-
  aware 处理时间，再 decomposition 拆 sub-query。也可以并联（一个
  query 既需时间又需多 sub）。
- 与 retriever 的接口：time_filter 字段格式应当和你的 retriever
  metadata schema 匹配（如 Pinecone / Weaviate 等）。如果 schema
  不同，加一个轻量映射层。
- freshness_window_days 默认 30 天是 generic；不同领域应当有 domain-
  specific defaults（新闻 7 天，技术文档 90 天，法律条文 1825 天）。
- 不要把 atemporal 查询硬塞 freshness filter——会把高质量但旧的
  passages 排掉。

## Changelog

- `0.1.0` — Initial card.
