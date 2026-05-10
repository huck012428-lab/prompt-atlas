---
id: agent/tool-output-summarizer
title: Tool Output Summarizer (compress before context)
version: 0.1.0
status: stable
direction: agent
tags: [generation, memory, structured-output]
audience: [prompt-engineer, app-builder]
models: [generic, frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: tool_name
    description: Which tool produced the output (e.g. "search", "fetch_user_orders", "list_files").
    required: true
  - name: tool_call_args
    description: The arguments the tool was called with (JSON object).
    required: true
  - name: raw_tool_output
    description: The raw output from the tool — could be large JSON, large text blob, file listing, etc.
    required: true
  - name: agent_goal
    description: The agent's overall goal — used to decide what's relevant in the tool output.
    required: true
---

> 🎯 **场景**：tool 返回大块输出（搜索结果 / 文件列表 / API 响应），把它压缩成"agent 接下来真的需要"的精简版再加入 context。比把原始输出整段塞进 context 节省 token 且让 agent 注意力聚焦。

## Quick Use

**Use when:** A tool returned verbose output (JSON blob, file listing, search results, long fetch response) and you want to compress it down to what the agent actually needs for the next step.
**Fill in:** `{{tool_name}}` = which tool; `{{tool_call_args}}` = JSON of args; `{{raw_tool_output}}` = the raw output; `{{agent_goal}}` = the agent's overall goal.
**You'll get:** A compressed summary tailored to the agent's goal, key facts extracted, and indicators for what was dropped. Output is JSON.

## Purpose

Compress a tool's verbose output into the agent's working context.
Picks out goal-relevant information and drops scaffolding (HTTP
headers, pagination metadata, repeated keys, irrelevant fields).
Used inside agent loops between tool execution and the next reasoning
step. Output is structured so the compressed summary, key facts, and
"what was dropped" are separately addressable.

## Prompt

```text
You compress a tool's output to feed into an agent's next reasoning
step. Keep what's relevant to the goal; drop what isn't.

Tool name: {{tool_name}}
Tool call args:
{{tool_call_args}}

Agent's overall goal:
{{agent_goal}}

Raw tool output:
{{raw_tool_output}}

Rules:
1. Identify what's relevant to the agent_goal. The agent doesn't
   need everything — just what advances the goal.
2. Drop boilerplate (response headers, pagination metadata, status
   strings, repeated keys, schema annotations) unless the agent
   needs them for the next step.
3. For lists, keep representative items + count; don't dump 50
   rows when 5 is enough.
4. For text content, preserve named entities and numbers verbatim;
   summarize narrative.
5. If the tool failed (error status), capture the error short-form
   and note it.
6. If the tool output is genuinely small and useful as-is, return
   it nearly unchanged.

Return ONLY this JSON object:
{
  "compressed_summary": "<the compressed text the agent will see in context>",
  "key_facts": [
    {"fact": "<short>", "from": "<which part of tool_output>"}
  ],
  "what_was_dropped": ["<short list of categories dropped: e.g. 'pagination metadata', '47 of 50 search results past top 3', 'response headers'>"],
  "tool_failed": true | false,
  "error_summary": "<if tool_failed=true: short error description; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
tool_name: "search"
tool_call_args: {"query": "Reykjavik population 2024"}
raw_tool_output: |
  {"status": "success", "took_ms": 234, "next_token": "abc123", "results": [
    {"title": "Reykjavik - Wikipedia", "url": "...", "snippet": "Reykjavik is the capital of Iceland with a population of approximately 140,000 (2024 estimate, Statistics Iceland)..."},
    {"title": "Iceland tourism guide", "url": "...", "snippet": "Reykjavik, Iceland's largest city, ..."},
    {"title": "Travel Reykjavik 2024", "url": "...", "snippet": "Best places to visit in Reykjavik include..."}
    /* ... 47 more results */
  ]}
agent_goal: "Find the population of Reykjavik and compute its share of Iceland's total population."
```

**Expected output:**

```json
{
  "compressed_summary": "Reykjavik population is approximately 140,000 in 2024 per Wikipedia citing Statistics Iceland. Top result is authoritative; remaining 49 results are tourism guides not relevant to population query.",
  "key_facts": [
    {"fact": "Reykjavik population ≈ 140,000 (2024)", "from": "result 1 (Wikipedia / Statistics Iceland)"}
  ],
  "what_was_dropped": [
    "Status / took_ms / next_token metadata",
    "47 of 50 search results — tourism guides not relevant to population question",
    "URL strings (not needed for next step)"
  ],
  "tool_failed": false,
  "error_summary": "",
  "decision_basis": "Top result has the population number with a citation; remaining results are off-topic; compressed to one fact + provenance."
}
```

## Failure Modes

- **Over-aggressive drop** — compresses away information the agent
  will need next step. If `key_facts` is too thin to advance the
  goal, the summary cut too much.
- **Boilerplate retention** — keeps HTTP headers / pagination metadata
  the agent doesn't need. Audit `compressed_summary` for raw
  structural noise.
- **Hallucinated facts** — key_facts contain values not in
  raw_tool_output. Validate by sampling and string-matching key_facts
  back to raw_tool_output.
- **Tool failure not flagged** — error response treated as success
  data. Check status / error fields explicitly; set tool_failed=true
  if present.
- **Loss of provenance** — compressed summary cites a number without
  saying which result it came from. Each key_fact's `from` field
  exists for this.

## Tuning Notes

- 模型差异：相对简单任务，中档模型也能用。但 long tool output (>10k
  tokens) 时 frontier 模型在"识别哪条结果最权威"上更稳。
- 温度：`0.0`，summary 必须可重现。
- 与 `agent/long-context-memory-summarizer` 的对比：那张卡处理整个
  trajectory 的 memory 压缩；本卡处理**单次 tool 输出**的就地压缩。
  trajectory 跑长了用前者；每次 tool 调用后用后者。
- 与 `rag/context-compression` 的对比：那张卡处理 retrieved passages，
  本卡处理 tool outputs。结构相似但语境不同（前者 RAG，后者 agent）。
- 集成位置：典型 agent loop 中——tool() returns → 本卡 → next reasoning
  step. 加这一层对 token 成本和 attention 都明显有改善。
- 不同 tool 对 summary 偏好不同：search 适合"top 1-3 + count"压缩；
  list_files 适合"按类型聚合 + 关键文件"压缩；fetch_user 适合"keep
  field-by-field"压缩。可以传 tool 特定的 hint 提升精度。

## Changelog

- `0.1.0` — Initial card.
