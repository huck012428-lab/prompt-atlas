---
id: rag/hyde-hypothetical-answer-generator
title: HyDE — Hypothetical Answer Generator for Retrieval
version: 0.1.0
status: experimental
direction: rag
tags: [retrieval, query-rewriting, generation, synthesis]
audience: [prompt-engineer, app-builder, llm-trainer]
models: [generic, frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: text
output_schema: text
license: CC-BY-4.0
variables:
  - name: query
    description: The user's original query for which retrieval is being performed.
    required: true
---

> 🎯 **场景**：HyDE 技术——给 query 生成"假答"用作检索向量，让 embedding 检索的召回更高。生成的假答**不**给用户看，是 retrieval 内部的脚手架。

## Quick Use

**Use when:** You want to generate a hypothetical answer to embed and use as a search vector (HyDE technique).
**Fill in:** `{{query}}` = the user's original query.
**You'll get:** A 2-4 sentence reference-style hypothetical answer. Output is plain text (not JSON), intended to be embedded — not shown to the user.

## Purpose

Generate a short, plausible hypothetical answer to a query. The
hypothetical answer is then embedded and used as the search vector
instead of (or in addition to) the embedded query — the HyDE technique
(Hypothetical Document Embeddings). The intuition: a model-generated
"what an answer would look like" is closer in embedding space to real
answer documents than the query itself, which boosts recall on
embedding-based retrievers. Used at query time, before retrieval.

## Prompt

```text
You generate a hypothetical answer to a user query. The output will be
EMBEDDED and used as a retrieval query, not shown to the user. Goal:
write text that resembles what a real reference document answering this
query would look like, so that its embedding lands near real answer
documents.

Rules:
1. Write 2 to 4 sentences. Avoid bullet lists, headers, or markdown.
2. Use the register of an encyclopedic / reference document, not a
   conversational reply ("The X is..." not "Sure! The X is...").
3. Include plausible specifics (named entities, numbers, dates) where
   they would naturally appear. These do NOT need to be factually
   correct — the output is a search vector, not a final answer.
4. Stay on the topic of the query. Do not branch into adjacent topics.
5. Do NOT preface with disclaimers ("I am not sure but...") or hedges.
   The output is internal infrastructure, not a user-facing answer.

Query:
{{query}}

Hypothetical answer:
```

## Example

**Input:**

```text
query: "What caused the failure of the Mars Climate Orbiter in 1999?"
```

**Expected output:**

```text
The Mars Climate Orbiter, launched by NASA in December 1998, was lost on September 23, 1999 when it entered the Martian atmosphere at an incorrect altitude. The root cause was a unit-mismatch error: navigation software produced by the contractor used pound-seconds for impulse while the spacecraft team's software expected newton-seconds. This discrepancy caused the orbiter to descend too low into the atmosphere, where it was destroyed by atmospheric stress.
```

## Failure Modes

- **Conversational drift** — model produces "Sure! The Mars Climate
  Orbiter..." with chat preamble. The preamble's embedding is
  generic and pulls retrieval toward chat-style documents instead of
  reference docs. Mitigation: rule 2 in the prompt; reject outputs
  starting with "Sure", "Of course", "I think", etc.
- **Hedge bloat** — model adds "I am not sure but" or "according to
  some sources", diluting the embedding. Rule 5 catches this.
- **Topic drift** — model writes adjacent content (history of Mars
  exploration in general) instead of the specific failure cause,
  pulling retrieval off-target. Mitigation: rule 4; consider adding a
  verifier step that checks topical overlap with the query.
- **Length collapse** — model returns one sentence on weaker variants,
  reducing the effective embedding signal. Mitigation: minimum 2
  sentences; if the output is too short, re-prompt with a length floor.
- **Refusal on speculative queries** — model refuses to answer a
  question whose answer is unknown or contested. For HyDE this is
  unhelpful (we want plausible text, not truth). Mitigation: emphasize
  rule 3; if refusals persist, switch to a less aligned base model
  for this specific call.

## Tuning Notes

- 模型差异：相对小的开源模型（7B 级）足以胜任本卡——HyDE 不要求
  factual 正确，要求 register 正确。用 frontier 模型反而可能浪费成本。
- 温度：`0.7`–`0.9`。多样性帮助召回长尾文档。
- 长度：2–4 句最佳；过长会把 embedding 拉向通用聚类，过短信号不够。
- 与 `rag/query-rewriting-decomposition` 的关系：互补——decomposition
  把 query 拆成多个，HyDE 把 query 改写成更接近文档的形式。两者可以
  组合（先 decompose，再对每个 sub-query 跑 HyDE），但额外 latency 不一定
  值得，先 A/B 看效果。
- 风险：当 retrieved corpus 包含错误信息时，HyDE 可能放大 confirmation
  bias（hypothetical answer 中的错误事实会和 corpus 中的错误事实对齐）。
  用 grounding-checker 兜底。
- 不要把本卡的输出展示给用户——它是 internal retrieval scaffolding，
  不是 final answer。

## Changelog

- `0.1.0` — Initial card.
