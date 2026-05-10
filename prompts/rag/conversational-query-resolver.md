---
id: rag/conversational-query-resolver
title: Conversational Query Resolver (rewrite follow-ups as standalone)
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
  - name: conversation_history
    description: Prior conversation turns as a JSON array, each with role (user|assistant) and text fields. Most recent turns last.
    required: true
  - name: latest_user_turn
    description: The most recent user message that may contain references to earlier context ("what about that one?", "show me more").
    required: true
---

> 🎯 **场景**：多轮 RAG 的"代词消解器"——把"再多说点"、"那个怎么样"这类含上文指代的 follow-up 改写成自包含的独立查询，喂给检索器。RAG-as-chat 必备组件。

## Quick Use

**Use when:** You're running RAG in a multi-turn conversation and the latest user turn references earlier context (pronouns, "that one", "what about...") — direct retrieval would fail.
**Fill in:** `{{conversation_history}}` = JSON array of prior turns; `{{latest_user_turn}}` = the most recent user message.
**You'll get:** A standalone rewritten query, a list of resolved references, and a flag if the turn was actually independent (no rewrite needed). Output is JSON.

## Purpose

Turn a context-dependent follow-up question into a self-contained
query that a retriever can use without seeing the conversation.
"What about Tesla?" becomes "What is Tesla's revenue in 2024?" if
the prior turn was about company revenues. Used as the first step
of multi-turn RAG, before the retrieval call. Distinct from
`rag/query-rewriting-decomposition`, which decomposes a single complex
query into sub-queries; this card resolves cross-turn references in
chat.

## Prompt

```text
You rewrite a conversational follow-up into a standalone retrieval
query. The retriever has no access to conversation history; the
rewritten query must contain enough context to retrieve correctly
on its own.

Conversation history (oldest first, JSON array):
{{conversation_history}}

Latest user turn:
{{latest_user_turn}}

Rules:
1. If the latest turn is already self-contained (no pronouns or
   referring phrases tied to earlier context), set
   "rewrite_needed": false and return the latest turn as-is.
2. If rewriting: resolve every pronoun and referring phrase ("it",
   "that one", "the company we discussed") to the specific entity.
3. Preserve the original ASK. Do NOT change "tell me more" into
   "tell me everything"; preserve the intent grain.
4. Do NOT inject information not in the conversation. If a reference
   is ambiguous (multiple candidates in history), set
   "ambiguous": true and pick the most recent matching candidate.
5. Keep the rewrite concise — same kind of phrasing the user would
   write if they had to phrase it standalone.

Return ONLY this JSON object:
{
  "rewrite_needed": true | false,
  "standalone_query": "<the rewritten query, OR identical to latest_user_turn if no rewrite needed>",
  "references_resolved": [
    {"original_phrase": "<phrase from latest turn>", "resolved_to": "<concrete entity>"}
  ],
  "ambiguous": true | false,
  "ambiguity_note": "<if ambiguous: which alternatives existed and why you chose this one; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
conversation_history: [
  {"role": "user", "text": "What were Apple's iPhone revenue numbers for Q1 2024?"},
  {"role": "assistant", "text": "Apple reported $69.7B in iPhone revenue for Q1 2024..."},
  {"role": "user", "text": "What about Samsung in the same quarter?"}
]
latest_user_turn: "And how does that compare to their previous year?"
```

**Expected output:**

```json
{
  "rewrite_needed": true,
  "standalone_query": "How did Samsung's smartphone revenue in Q1 2024 compare to Q1 2023?",
  "references_resolved": [
    {"original_phrase": "that", "resolved_to": "Samsung's Q1 2024 smartphone revenue"},
    {"original_phrase": "their", "resolved_to": "Samsung's"},
    {"original_phrase": "previous year", "resolved_to": "Q1 2023"}
  ],
  "ambiguous": false,
  "ambiguity_note": "",
  "decision_basis": "Last context-relevant turn was about Samsung's Q1 2024; 'that' and 'their' resolve to Samsung's revenue."
}
```

## Failure Modes

- **Over-resolution** — model rewrites a self-contained turn anyway,
  injecting unnecessary context that narrows retrieval. Detect by
  sampling outputs where `rewrite_needed: true` and the query is
  significantly longer than the original; verify the rewrite is
  necessary.
- **Wrong reference target** — when multiple candidates exist,
  picks the wrong one (e.g. resolves "it" to a tool mentioned 5
  turns ago instead of the company in the prior turn). The
  `ambiguous` field exists to surface this; track ambiguous=true
  rate and audit.
- **Intent shift** — "tell me more" becomes "tell me everything
  about X". Preserve grain — match the original ask scope.
- **Hallucinated context** — model adds details not present in
  conversation ("their 2023 revenue of $200B" when no number was
  discussed). Verify all entities in standalone_query trace to
  conversation_history.
- **Missed self-contained turn** — model rewrites a turn that's
  actually independent (changing topic). If user says "Now, tell me
  about climate change," that's a topic switch, not a follow-up;
  rewrite_needed should be false.

## Tuning Notes

- 模型差异：本卡对 conversation 理解 + 实体追踪要求高；frontier 模型
  在 ambiguous reference 处理上明显更稳。中档模型常出现 over-resolution。
- 温度：`0.0`–`0.2`。retrieval query 必须可重现。
- 历史长度：建议传最近 5-10 turns。超过 15 轮的对话先用
  `agent/long-context-memory-summarizer` 压缩成 memory，再喂本卡。
- 与 `rag/query-rewriting-decomposition` 的关系：那张卡处理"复杂单次
  query"，本卡处理"chat 中的 follow-up"。两者可串联：先本卡解 chat
  上下文 → 再用那张卡分解。
- 与 `rag/multihop-eval-synthesizer` 的关系：那张是 eval-set 构建（生成
  问题），本卡是 inference 时（解析 query）。完全不同阶段。
- ambiguous=true 的处理：production 中可以选择"reject 让用户澄清"或
  "选最近候选 + 在响应里告诉用户'我假设你说的是 X'"。ambiguity 不是
  bug，是信号。

## Changelog

- `0.1.0` — Initial card.
