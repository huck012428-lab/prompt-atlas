---
id: agent/tool-call-repair
title: Tool-Call Repair from Validation Error
version: 0.1.0
status: stable
direction: agent
tags: [tool-use, structured-output, extraction]
audience: [prompt-engineer, app-builder]
models: [generic, frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: tool_schema
    description: JSON schema for the tool's parameters (the contract the call must satisfy).
    required: true
  - name: attempted_call
    description: The malformed tool call the agent emitted (JSON object with name and arguments).
    required: true
  - name: error_message
    description: The validator / runtime error message describing what went wrong.
    required: true
---

## Purpose

Take a malformed tool call (schema validation failure, type mismatch,
missing required field) plus the error message, and emit a corrected
call that satisfies the tool's parameter schema. Used inside agent
loops to recover from a single bad call without escalating to the full
reflection step or restarting the whole trajectory. Output is the
repaired call as structured JSON, ready to re-submit to the tool layer.

## Prompt

```text
You repair a malformed tool call. The call failed validation; produce
a corrected version that satisfies the schema.

Tool schema (JSON Schema for the tool's parameters):
{{tool_schema}}

Attempted call:
{{attempted_call}}

Error message:
{{error_message}}

Rules:
1. Preserve the user-intent of the attempted call. Do NOT change tool
   choice, do NOT invent new arguments unrelated to the original
   intent.
2. Fix only what the error message indicates is wrong, plus any other
   schema violation you can see.
3. If a required field is missing AND its value cannot be inferred
   from the attempted call, set `repairable: false` and explain in
   `escalation_reason` rather than fabricating a value.
4. If the attempted call's tool name is not consistent with the
   schema (wrong tool entirely), set `repairable: false` — that is a
   strategy issue, not a repair issue.

Return ONLY this JSON object:
{
  "repairable": true | false,
  "repaired_call": {
    "name": "<tool name from schema>",
    "arguments": { ... }
  },
  "changes": ["<short description of each fix applied>"],
  "escalation_reason": "<if repairable=false: one-sentence reason; else empty string>"
}

If repairable=false, set "repaired_call" to the attempted_call
unchanged (so the caller has a consistent shape to handle).
```

## Example

**Input:**

```text
tool_schema: {
  "name": "search",
  "parameters": {
    "type": "object",
    "required": ["query", "max_results"],
    "properties": {
      "query": {"type": "string"},
      "max_results": {"type": "integer", "minimum": 1, "maximum": 20}
    }
  }
}
attempted_call: {
  "name": "search",
  "arguments": {"query": "Reykjavik population 2024", "max_results": "ten"}
}
error_message: "validation error at /arguments/max_results: expected integer, got string 'ten'"
```

**Expected output:**

```json
{
  "repairable": true,
  "repaired_call": {
    "name": "search",
    "arguments": {"query": "Reykjavik population 2024", "max_results": 10}
  },
  "changes": ["Converted max_results from string 'ten' to integer 10."],
  "escalation_reason": ""
}
```

## Failure Modes

- **Over-repair / drifting intent** — model also changes the `query`
  string ("Reykjavik population 2024" → "Iceland demographic statistics
  2024") under the guise of "fixing" the call. Detect by comparing
  string fields between attempted and repaired calls; flag any change
  to fields not mentioned in the error message.
- **Fabricating required fields** — when a required field is missing,
  model invents a plausible value instead of escalating. The rubric
  forbids this; verify by spot-checking outputs where `repairable=true`
  and a required field appears in `changes` — its value should be
  derivable from the attempted call's other fields, not arbitrary.
- **Tool swapping** — model "fixes" the call by switching to a
  different tool that would have been more appropriate. The rubric
  forbids this; if it happens, return `repairable: false` so the
  reflection step can decide whether to switch tools.
- **Schema misreading** — model reads the schema's `properties` as
  `required` (or vice versa) and adds fields that should be optional.
  Mitigation: use a strict JSON-schema validator on the repaired
  call before submitting; on validation failure, escalate.
- **Silent format drift** — model returns valid JSON but with extra
  prose around it. Use JSON-mode if available, or a strict parser
  that rejects extras.

## Tuning Notes

- 模型差异：本卡对 schema understanding 比对 reasoning 要求更高；中档
  模型在简单类型修复（string→int）上稳定，在嵌套 schema / 联合类型
  上失败率上升。复杂 schema 建议用 frontier 模型。
- 温度：`0.0`，repair 必须可重现。
- 调用预算：单次 tool call 失败立刻 repair 一次；连续 2 次 repair 失败
  应触发反思（见 `agent/self-critique-reflection`），不要无限循环
  repair。
- 与 `agent/react-planner-with-tool-schema` 的关系：planner 的失败处理
  规则要求"不要立刻重试同样的 call"。本卡产生的 `repaired_call` 不算
  "同样的 call"，可以直接重试。
- 与 `agent/self-critique-reflection` 的关系：本卡处理语法层失败；
  reflection 处理策略层失败。`repairable: false` 是一个明确的"升级到
  reflection"信号。
- 安全考虑：repair 必须保留原 intent；这是为了防止恶意构造的 error
  message 诱导 agent 改写 query 去搜索其他内容。生产中要监控
  intent-drift 率。

## Changelog

- `0.1.0` — Initial card.
