---
id: rag/context-compression
title: Retrieved Context Compression
version: 0.1.0
status: stable
direction: rag
tags: [retrieval, generation, synthesis, structured-output]
audience: [app-builder, llm-trainer, ai-pm]
models: [generic, frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The user's question that the retrieved context is supposed to help answer.
    required: true
  - name: retrieved_passages
    description: A JSON array of retrieved passage objects, each with `id` and `text` fields. Typical sizes 5-20 passages.
    required: true
  - name: token_budget
    description: Approximate target token budget for the compressed context (an integer hint, e.g. 800).
    required: true
---

> 🎯 **场景**：检索后压缩——把多个 retrieved passage 压成针对问题的小上下文（保留 verbatim spans + citation），省 token 同时让模型注意力更聚焦，避免"lost in the middle"。

## Quick Use

**Use when:** Your retriever returns more text than fits comfortably in the LLM's context window, or you want to focus the model's attention on the spans actually relevant to the question.
**Fill in:** `{{question}}` = the user's question; `{{retrieved_passages}}` = JSON array of retrieved passages each with id + text; `{{token_budget}}` = target compressed size, e.g. 800.
**You'll get:** A compressed context built from question-relevant span excerpts (citing original passage IDs), a list of dropped passage IDs, and a sufficiency check. Output is JSON.

## Purpose

Compress a list of retrieved passages into a smaller context tailored
to a specific question — keeping the spans that actually bear on the
question and dropping the surrounding text that doesn't. Used between
retrieval and generation in a RAG pipeline to: (1) fit more breadth
into a constrained context window, (2) reduce per-query token cost,
and (3) focus the generator's attention on relevant content (LLMs
have well-documented "lost in the middle" failure modes when fed
long uniformly-relevant context). Output is structured so each
extracted span is traceable to a source passage ID and the
sufficiency_check flag tells downstream whether the compressed
context can actually answer the question.

## Prompt

```text
You compress retrieved passages into a smaller context tailored to a
specific question. The compressed context will be passed to another
LLM that will use it to answer the question — your job is to keep
exactly the spans that bear on the question, with citations.

Question:
{{question}}

Retrieved passages (each with id and text):
{{retrieved_passages}}

Approximate token budget for the compressed context:
{{token_budget}}

Rules:
1. Extract verbatim or near-verbatim spans from the passages — do NOT
   paraphrase, summarize, or interpret. Preserve facts as written.
2. For each kept span, attach the source passage `id` so downstream
   citation tracking works.
3. Drop passages entirely if they don't bear on the question; do not
   include filler like section headers, navigation, or unrelated
   context just because they were retrieved.
4. Aim for the token budget. Going slightly over to preserve a
   critical fact is fine; going far over defeats the purpose.
5. If the retrieved passages collectively do NOT contain enough
   information to answer the question, set
   "sufficiency_check.sufficient": false and explain what's missing.

Return ONLY this JSON object:
{
  "compressed_context": "<the compressed context text, with passage IDs inline like [p3] before each span>",
  "kept_spans": [
    {"source_id": "<passage id>", "span": "<verbatim span kept>", "why": "<one short phrase: how this bears on the question>"}
    /* one entry per kept span */
  ],
  "dropped_passage_ids": ["<id of a passage with nothing relevant>"],
  "sufficiency_check": {
    "sufficient": true | false,
    "missing_info": "<if not sufficient: what fact / aspect is missing; else empty>"
  },
  "compression_ratio": <float: kept_spans total length / retrieved_passages total length>,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
question: "What's the rate limit for the Stripe API and what happens when I exceed it?"
retrieved_passages: [
  {"id": "p1", "text": "## Authentication\n\nThe Stripe API uses API keys for authentication. Each API key is associated with an account..."},
  {"id": "p2", "text": "## Rate Limiting\n\nThe Stripe API enforces rate limits on a per-account basis. The default limit is 100 read requests per second and 100 write requests per second. Test mode has a higher limit of 25 per second of each operation type. When exceeded, the API responds with HTTP 429 and a retry-after header indicating the number of seconds to wait."},
  {"id": "p3", "text": "## Webhooks\n\nWebhooks let you receive real-time notifications when events happen in your account. You can configure up to 16 webhook endpoints..."},
  {"id": "p4", "text": "## Error Handling\n\nFor 5xx errors, retry with exponential backoff. For 4xx errors, do not retry — inspect the error code. Specific 429 responses include a retry-after header that should be honored."}
]
token_budget: 200
```

**Expected output:**

```json
{
  "compressed_context": "[p2] The Stripe API enforces rate limits on a per-account basis. The default limit is 100 read requests per second and 100 write requests per second. When exceeded, the API responds with HTTP 429 and a retry-after header indicating the number of seconds to wait. [p4] Specific 429 responses include a retry-after header that should be honored.",
  "kept_spans": [
    {"source_id": "p2", "span": "The Stripe API enforces rate limits on a per-account basis. The default limit is 100 read requests per second and 100 write requests per second.", "why": "Direct rate limit number for default account."},
    {"source_id": "p2", "span": "When exceeded, the API responds with HTTP 429 and a retry-after header indicating the number of seconds to wait.", "why": "Direct answer to 'what happens when exceeded'."},
    {"source_id": "p4", "span": "Specific 429 responses include a retry-after header that should be honored.", "why": "Reinforces the retry-after handling."}
  ],
  "dropped_passage_ids": ["p1", "p3"],
  "sufficiency_check": {
    "sufficient": true,
    "missing_info": ""
  },
  "compression_ratio": 0.32,
  "decision_basis": "Two passages directly relevant; kept rate-limit numbers and 429 behavior, dropped auth and webhooks."
}
```

## Failure Modes

- **Paraphrasing creep** — model rewrites spans instead of extracting
  verbatim, drifting the meaning. Detect by sampling and checking
  whether each `span` appears (or near-appears with only whitespace
  differences) in the original passage. Mitigation: rule 1 explicit;
  use exact / fuzzy matching on `kept_spans` against
  `retrieved_passages` and reject low-match outputs.
- **Citation drift** — span is correctly extracted but source_id
  points to wrong passage. Validate by string-matching each `span`
  back to its claimed source passage; reject mismatches.
- **Over-compression** — model drops passages that are actually
  relevant because they're written awkwardly. Detect by sampling
  outputs where `sufficient: true` but downstream answer-quality
  drops; if persistent, the compressor is too aggressive.
- **Under-compression** — model keeps long spans that contain only a
  small relevant fragment surrounded by filler, blowing the token
  budget. Mitigation: rule 4 + cap on individual span length at
  parse time.
- **Sufficiency over-confidence** — model marks `sufficient: true`
  when the compressed context only partially answers. Mitigation:
  chain with `rag/answer-grounding-checker` after generation — if
  hallucination_rate is high on outputs from this card's compressed
  context, the sufficiency calibration is off.
- **Question keyword overfit** — model only keeps spans that contain
  the question's literal words, missing relevant content phrased
  differently. Frontier models handle this well; mid-tier models
  often fail and require explicit "look for related concepts, not
  just word matches" framing.
- **Cross-passage merging** — model merges spans from two passages
  into one citation, losing traceability. Each kept span must have
  exactly one source_id; reject merges at parse time.

## Tuning Notes

- 模型差异：本卡对模型的"语义相关性判断"高度依赖；frontier 模型显
  著优于中档。但成本上 compressor 通常用比 generator 弱一档的模型
  也行（compressor 是加速器，generator 是主力）。
- 温度：`0.0`–`0.2`，extraction 必须可重现。
- token_budget 选择：典型 600-1500 tokens。budget 太小会强制 drop
  必要内容；太大没有压缩收益。从 retrieved 总长的 25-40% 起步。
- 与 `rag/retrieval-relevance-evaluator` 的关系：那张卡是
  per-passage 二/三档相关性打分（用于 retrieval 质量评测和数据集
  构建）；本卡是 query-conditioned 的 span-level 提取（用于运行时
  context 准备）。前者粗粒度评估，后者细粒度生成。
- 与 `rag/chunk-summarizer-for-retrieval` 的关系：那张卡是
  index-time 预处理（chunk → indexable summary）；本卡是 query-time
  后处理（retrieved passages → compressed context）。一个发生在
  索引建设期，一个发生在每次查询。两者正交可叠加。
- 与 `rag/answer-grounding-checker` 的关系：本卡产 compressed
  context → generator 出答案 → answer-grounding-checker 用本卡的
  compressed context 作为 retrieved_context 来检查 grounding。
  完整 RAG pipeline 的中段。
- 引用 ID 的形式：`[p3]` 是常见约定；如果你的 generator 期望另一种
  形式（比如 `<doc id="3">`），调整 prompt 中的指令并确保
  generator 端能解析。
- 不要把 compressed_context 作为唯一的下游输入——同时 keep 原始
  passage IDs，让 generator 在边缘 case 时可以请求"原文回查"。
- 用作训练数据：(question, retrieved_passages, compressed_context)
  triples 可以作为压缩任务的 SFT 监督信号；建议先用人工抽检 100
  例做 calibration set。

## Changelog

- `0.1.0` — Initial card.
