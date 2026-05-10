---
id: rag/chunk-summarizer-for-retrieval
title: Chunk Summarizer for Retrieval
version: 0.1.0
status: stable
direction: rag
tags: [retrieval, generation, structured-output, synthesis]
audience: [app-builder, llm-trainer, ai-pm]
models: [generic, frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: chunk
    description: A single document chunk (paragraph, section, or extracted slice) to summarize.
    required: true
  - name: source_hint
    description: Optional one-line hint about the source (e.g. "API reference", "legal contract", "research paper introduction"). Pass empty string if unknown.
    required: false
---

## Quick Use

**Use when:** You're building a RAG index and want to store a search-friendly summary alongside (or instead of) the raw chunk text.
**Fill in:** `{{chunk}}` = the document chunk to summarize; `{{source_hint}}` = optional one-line hint about the source.
**You'll get:** A short retrieval-optimized summary, salient keywords, and the chunk's likely-question form. Output is JSON.

## Purpose

Produce a compact summary of a long document chunk, optimized for the
retrieval step rather than for human reading. The summary keeps the
named entities, numbers, and concrete relationships that distinguish
this chunk from siblings, while dropping boilerplate, headers, and
filler. Used as the indexed text in a hybrid retrieval system, or as
the "snippet" returned to the model alongside the raw chunk. Output is
structured so a salient-keyword list and a hypothesized-question form
can both be embedded as separate retrieval channels.

## Prompt

```text
You are summarizing a document chunk for retrieval indexing. Goal: keep
the parts that uniquely identify this chunk; drop the parts that are
generic boilerplate.

Chunk:
{{chunk}}

Source hint (may be empty):
{{source_hint}}

Rules:
1. The summary will be EMBEDDED for retrieval, not shown to a human.
   Optimize for distinguishing this chunk from other chunks of similar
   content, not for narrative flow.
2. Preserve named entities, numbers, dates, and concrete relationships
   verbatim. These are usually the retrieval signal.
3. Drop section headers, navigation cues ("see also", "next chapter"),
   and pure filler ("In this section we will discuss...").
4. Length: 1-3 sentences. Going longer dilutes the embedding.
5. Also produce a list of 3-7 salient keywords (compact retrieval
   signal) and one hypothesized question this chunk would answer
   (useful as an additional retrieval channel).
6. If the chunk is mostly boilerplate or table-of-contents content
   with no information density, set "indexable: false".

Return ONLY this JSON object:
{
  "summary": "<1-3 sentence retrieval-optimized summary>",
  "salient_keywords": ["<keyword 1>", "<keyword 2>", "..."],
  "hypothesized_question": "<one question this chunk plausibly answers>",
  "indexable": true | false,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
chunk: "## 3.2 Rate Limiting\n\nThe Stripe API enforces rate limits on a per-account basis. The default limit is 100 read requests per second and 100 write requests per second. Test mode has a higher limit (25 per second of each operation type). When exceeded, the API responds with HTTP 429 and a retry-after header indicating the number of seconds to wait. Production accounts can request a rate increase by contacting support."
source_hint: "Stripe API reference"
```

**Expected output:**

```json
{
  "summary": "Stripe API rate limits are 100 read and 100 write requests per second per account, with HTTP 429 returned when exceeded; test mode is capped at 25 per second per operation type.",
  "salient_keywords": ["Stripe API rate limit", "100 requests per second", "HTTP 429", "retry-after header", "test mode 25 per second"],
  "hypothesized_question": "What is the default rate limit for the Stripe API and what happens if I exceed it?",
  "indexable": true,
  "decision_basis": "Concrete numbers, named entity (Stripe), and a clear question form make this an information-dense indexable chunk."
}
```

## Failure Modes

- **Generic-summary collapse** — model produces a vague paraphrase
  ("This section discusses rate limiting") that loses the actual
  numbers. Detect by sampling outputs whose `salient_keywords` are
  all noun phrases without numeric values when the chunk had numbers.
  Mitigation: rule 2 explicit; if persistent, add a few-shot showing
  number preservation.
- **Header / nav bleed** — summary copies "Section 3.2" as a salient
  keyword. The retrieval system rarely benefits from section
  numbers; reject as noise. Mitigation: rule 3.
- **Hallucinated keywords** — keywords appear that are NOT in the
  chunk text. Detect by checking each keyword against the chunk via
  substring or fuzzy match; reject extras.
- **`indexable: false` over-trigger** — model marks anything short
  as un-indexable. Track the rate against a benchmark of known-
  indexable chunks; if >5% false negatives, the bar is too high.
- **Hypothesized question drift** — question is more general than
  the chunk supports ("How does the Stripe API work?" instead of
  the specific rate limits question). Mitigation: emphasize
  "plausibly answers" — the question should be specifically
  answerable by THIS chunk.
- **Length inflation** — summaries creep to 4-6 sentences as the
  model tries to be thorough. Cap at parse time; reject overlong
  outputs.

## Tuning Notes

- 模型差异：本卡对模型规模要求不高——结构化总结是大多数中档模型的
  强项。frontier 模型在 hypothesized_question 的准确度上略高。
- 温度：`0.0`–`0.3`。retrieval index 必须可重现。
- 与 raw chunk 的关系：典型用法是**双通道索引**：原 chunk 嵌入一份、
  本卡产出 summary 嵌入一份，retrieval 时融合两者得分。summary 通常
  在 BM25 / 关键词检索上得分更高，原 chunk 在长尾语义上得分更高。
- 与 `rag/hyde-hypothetical-answer-generator` 的关系：HyDE 是 query
  端改写（用户 query → 假答用于检索）；本卡是 corpus 端预处理（文档
  chunk → 索引友好摘要）。两者正交可叠加。
- chunk 大小敏感性：本卡假设 chunk 已经被合理切分（200-1000 tokens
  之间）。过短（<50 tokens）会导致 indexable: false 频繁触发；过长
  （>2000 tokens）会导致 summary 丢细节。
- `salient_keywords` 数量：3-7 是经验最优。少于 3 不够区分；多于 7
  在 BM25 上反而引入噪声。
- 用作训练数据：本卡产出可以作为"检索友好 summary"任务的 SFT 监督
  信号；建议搭配 `eval/per-claim-factuality-judge` 做事实性核查后再
  入训练集。

## Changelog

- `0.1.0` — Initial card.
