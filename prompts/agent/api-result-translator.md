---
id: agent/api-result-translator
title: API Result to User-Readable Translator
version: 0.1.0
status: stable
direction: agent
tags: [generation, structured-output, tool-use]
audience: [app-builder, prompt-engineer, ai-pm]
models: [generic, frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: user_question
    description: The user's original question that prompted the API call.
    required: true
  - name: api_response
    description: The raw API response (JSON, XML, or stringified data).
    required: true
  - name: response_style
    description: One of "concise" (1-3 sentences), "detailed" (4-8 sentences), "table" (formatted as markdown table when data is tabular).
    required: true
---

> 🎯 **场景**：agent 调 API 拿到的原始 JSON / XML 怎么变成给用户看的话——按 user 问题挑相关字段、隐藏 implementation noise、按 style 选格式（简洁 / 详细 / 表格）。是 agent loop 的 "API → user" 翻译层。

## Quick Use

**Use when:** Your agent called an API and got back structured data; you need to translate it into a user-readable answer that addresses the original question.
**Fill in:** `{{user_question}}` = original question; `{{api_response}}` = raw API output; `{{response_style}}` = `concise` / `detailed` / `table`.
**You'll get:** A user-readable answer, what fields were used, what was hidden, and a flag if the API response didn't actually answer the question. Output is JSON.

## Purpose

Translate a raw API response into a user-readable answer to the
original question. Different from generic API explanation: this card
is question-driven (uses only fields relevant to user_question) and
style-aware (matches output to response_style). Used in agent loops
between tool execution and user-facing output.

## Prompt

```text
You translate a raw API response into a user-readable answer to a
specific question.

User question:
{{user_question}}

API response (raw):
{{api_response}}

Response style: {{response_style}}

Style meanings:
- "concise" : 1-3 sentences answering the question directly. No
              implementation detail.
- "detailed": 4-8 sentences with relevant context. Still hides
              boilerplate.
- "table"   : Markdown table when the data is tabular OR
              structured comparison.

Rules:
1. Use only fields from api_response that bear on user_question.
   Hide pagination metadata, internal IDs, timestamps unless
   relevant.
2. If api_response doesn't actually answer the question, set
   "answers_question": false and explain.
3. Numbers / dates / specific values are preserved verbatim from
   api_response. Don't round / approximate / reformat unless the
   user_question implies it.
4. For table style, pick columns that match the user's implicit
   comparison axes.

Return ONLY this JSON object:
{
  "user_facing_answer": "<the answer in the requested style>",
  "fields_used": ["<api_response field path>"],
  "fields_hidden": ["<api_response field path that wasn't shown>"],
  "answers_question": true | false,
  "unanswered_aspect": "<if answers_question=false: what part of the question API didn't address; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
user_question: "What's the current price of Apple stock?"
api_response: |
  {
    "symbol": "AAPL",
    "price": 178.42,
    "currency": "USD",
    "timestamp": "2024-11-15T16:00:00Z",
    "exchange": "NASDAQ",
    "request_id": "abc-123",
    "rate_limit_remaining": 999
  }
response_style: "concise"
```

**Expected output:**

```json
{
  "user_facing_answer": "Apple (AAPL) is currently trading at $178.42 USD on NASDAQ.",
  "fields_used": ["symbol", "price", "currency", "exchange"],
  "fields_hidden": ["timestamp", "request_id", "rate_limit_remaining"],
  "answers_question": true,
  "unanswered_aspect": "",
  "decision_basis": "Price + currency + exchange directly answer the question; metadata fields hidden."
}
```

## Failure Modes

- **Implementation leak** — answer mentions request_id / pagination
  / API status. Audit fields_used and fields_hidden.
- **Number rounding** — model rounds 178.42 → "around 180" without
  basis. Preserve verbatim unless asked.
- **Style mismatch** — table style returns prose. Validate output
  format matches response_style.
- **Answer-question false positive** — model claims answers_question
  even though API returned an error. Sample API responses with
  status=error and verify.
- **Field hallucination** — answer references field values not in
  api_response. Cross-check.

## Tuning Notes

- 模型差异：相对简单任务，中档模型够用。frontier 模型在复杂 nested
  JSON 上更稳。
- 温度：`0.0`–`0.2`。
- 与 `agent/tool-output-summarizer` 的关系：那张卡是给**agent**继续
  推理用的压缩；本卡是给**用户**看的翻译。前者技术性，后者面向最
  终输出。
- 与 `agent/react-planner-with-tool-schema` 的关系：planner 决定调
  API；本卡处理 API 返回。完整 agent loop 一环。
- response_style 选择：UI 类型决定 — chat UI 用 concise；docs UI 用
  detailed；表格 UI / 报表用 table。
- 错误处理：API error response 应当有特殊处理（answers_question=false
  + 友好的 error 描述）。生产中建议在调用本卡前先检查 status code，
  error case 用专门 prompt 处理。
- 不要把 sensitive data 透传：api_response 含 PII 时应当先脱敏再喂
  本卡，避免 PII 出现在用户看到的 answer 里。

## Changelog

- `0.1.0` — Initial card.
