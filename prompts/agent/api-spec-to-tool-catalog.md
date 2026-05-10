---
id: agent/api-spec-to-tool-catalog
title: API Spec to Tool Catalog Converter
version: 0.1.0
status: stable
direction: agent
tags: [tool-use, extraction, generation, structured-output]
audience: [prompt-engineer, app-builder, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: api_spec
    description: The API specification — OpenAPI / JSON Schema / Swagger YAML or JSON. Pass as a string.
    required: true
  - name: filter_hint
    description: Optional one-line filter to scope which endpoints to include (e.g. "only read-only GET endpoints", "billing-related only", "v2 endpoints"). Pass empty string to include all.
    required: false
---

> 🎯 **场景**：把 OpenAPI / Swagger / JSON Schema 自动转成 agent 用的 tool catalog 格式（每个 endpoint 一个 tool，含 name / description / parameters schema）。装 agent 不再手写一份 tool 列表，直接读 API spec 即可。

## Quick Use

**Use when:** You have an OpenAPI / Swagger / JSON Schema spec and want a tool catalog ready to paste into an agent loop, without hand-writing each tool.
**Fill in:** `{{api_spec}}` = the spec text; `{{filter_hint}}` = optional scoping filter.
**You'll get:** A JSON tool_catalog where each tool has name, description, and parameters schema. Output is JSON, ready to feed into agent/react-planner-with-tool-schema.

## Purpose

Convert an API specification (OpenAPI 3.x, Swagger, JSON Schema) into
a tool catalog the agent loop can use. Each API endpoint becomes one
tool with normalized name, human-readable description (synthesized
from path + summary + parameters), and a JSON Schema for parameters.
Used to bootstrap agent integrations without hand-authoring the
catalog. Output is structured to plug directly into
`agent/react-planner-with-tool-schema` or `agent/plan-and-execute-planner`.

## Prompt

```text
You convert an API specification into a tool catalog for an agent
loop. Each endpoint becomes one tool entry.

API spec:
{{api_spec}}

Filter hint (may be empty):
{{filter_hint}}

Rules:
1. For each endpoint NOT excluded by the filter:
   - Tool name: derive from the operationId if present, otherwise
     from method + path. Use snake_case. Examples:
     "GET /users/{id}" → "get_user_by_id"
     "POST /orders" → "create_order"
     "DELETE /tasks/{taskId}" → "delete_task_by_task_id"
   - Description: synthesize from the spec's summary, description,
     and parameters. 1-2 sentences in plain English explaining what
     the tool does and when an agent would call it.
   - Parameters: combine path parameters, query parameters, and
     request body schema into one JSON Schema object describing all
     inputs the tool accepts.
   - Returns: brief description of what the tool returns (success
     case only).
   - Side effects: "none" if GET/HEAD/OPTIONS, otherwise describe
     what state changes (e.g. "creates a new order record").
2. Filter rules:
   - If filter_hint says "read-only", include only GET / HEAD /
     OPTIONS.
   - If filter_hint mentions specific tags or paths, include only
     those.
3. If the spec is malformed or empty, set "valid_spec": false.

Return ONLY this JSON object:
{
  "valid_spec": true | false,
  "validation_error": "<if valid_spec=false: short reason; else empty>",
  "tool_catalog": [
    {
      "name": "<snake_case>",
      "description": "<1-2 sentences plain English>",
      "method": "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD" | "OPTIONS",
      "path": "<original endpoint path>",
      "parameters": { /* JSON Schema combining path + query + body */ },
      "returns": "<short description>",
      "side_effects": "<none, OR description of state change>"
    }
  ],
  "excluded_count": <integer: how many endpoints were excluded by filter>,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
api_spec: |
  openapi: 3.0.0
  paths:
    /users/{id}:
      get:
        operationId: getUser
        summary: Get user by ID
        parameters:
          - name: id
            in: path
            required: true
            schema: {type: string}
        responses: {'200': {description: "User found"}}
    /users:
      post:
        operationId: createUser
        summary: Create new user
        requestBody:
          content:
            application/json:
              schema:
                type: object
                required: [name, email]
                properties:
                  name: {type: string}
                  email: {type: string}
filter_hint: ""
```

**Expected output:**

```json
{
  "valid_spec": true,
  "validation_error": "",
  "tool_catalog": [
    {
      "name": "get_user",
      "description": "Get a user by their ID. Use this when the agent has a user ID and needs to look up details about that user.",
      "method": "GET",
      "path": "/users/{id}",
      "parameters": {
        "type": "object",
        "required": ["id"],
        "properties": {
          "id": {"type": "string", "description": "User ID (path parameter)"}
        }
      },
      "returns": "User object with details for the given ID.",
      "side_effects": "none"
    },
    {
      "name": "create_user",
      "description": "Create a new user with the given name and email. Use this when the agent needs to register or onboard a new user.",
      "method": "POST",
      "path": "/users",
      "parameters": {
        "type": "object",
        "required": ["name", "email"],
        "properties": {
          "name": {"type": "string"},
          "email": {"type": "string"}
        }
      },
      "returns": "Newly-created user object with assigned ID.",
      "side_effects": "Creates a new user record in the system."
    }
  ],
  "excluded_count": 0,
  "decision_basis": "Two endpoints, both included; names derived from operationIds; parameters combined from path + body."
}
```

## Failure Modes

- **Description hallucination** — model invents what the endpoint
  does when the spec lacks summary/description. Detect by checking
  whether the description references concepts not in the spec.
  Mitigation: prefer literal restatement over creative interpretation
  when source is sparse.
- **Parameter schema loss** — model strips constraints (min/max,
  enum, format) when combining schemas. Validate combined schema
  against original parts.
- **Naming collision** — two endpoints map to the same tool name
  (e.g. GET /users and GET /users/{id} both become get_users).
  Mitigation: include disambiguation (get_user_by_id vs list_users)
  when paths differ on parameter presence.
- **Side-effect under-flagging** — POST/PUT marked side_effects
  "none". The mapping is mechanical (non-GET → has side effects);
  enforce.
- **Filter over-application** — filter_hint "read-only" excludes a
  HEAD endpoint that actually has side effects (rare but possible).
  Track filter_hint vs included methods.
- **Spec format detection** — model assumes OpenAPI when input is
  raw JSON Schema or vice versa. Sample inputs of each kind and
  check classification.

## Tuning Notes

- 模型差异：本卡对 OpenAPI 结构理解和 JSON Schema 生成能力同时要求
  高。frontier 模型对完整 spec 处理稳定；中档模型在嵌套
  schemas、$ref、allOf/oneOf/anyOf 上失败率高。
- 温度：`0.0`–`0.2`，结构性转换必须可重现。
- spec 大小：建议 <50KB 单次。大型 spec 应该按 tag 切分多次调用。
- 与 `agent/react-planner-with-tool-schema` 的关系：本卡产出的
  tool_catalog 字段直接喂给那张卡对应的 tool_catalog 输入变量。
  完整 agent 启动 pipeline。
- 与 `agent/plan-and-execute-planner` 的关系：本卡 + plan-and-execute
  组成"读 API spec → 直接产 plan"的简短链路。适合"看一遍文档就能
  解决的"任务。
- 与 `agent/tool-call-repair` 的关系：本卡产 catalog，repair 卡修
  agent 调用时的参数错误。生产中两者协同：catalog 给的是 schema 期望，
  repair 给的是失败时的恢复。
- 高敏 API（含 DELETE / 财务 / 安全相关）：建议本卡产出后人工 review
  description 段是否准确传达了"这会做什么"——agent 看到 description
  就会调用，描述错误会导致误调用。
- 实际工程建议：本卡输出做一次 schema validation（如 ajv）后再用，
  防止幻觉构造无效 JSON Schema。

## Changelog

- `0.1.0` — Initial card.
