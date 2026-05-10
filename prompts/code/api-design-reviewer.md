---
id: code/api-design-reviewer
title: API Design Reviewer (REST / GraphQL / gRPC)
version: 0.1.0
status: stable
direction: code
tags: [code-review, scoring, structured-output]
audience: [app-builder, prompt-engineer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: api_spec_or_examples
    description: API design as specification (OpenAPI / GraphQL SDL / .proto) OR a representative set of example endpoints / queries / RPCs with descriptions.
    required: true
  - name: api_style
    description: One of "rest", "graphql", "grpc", "rpc_other".
    required: true
  - name: review_focus
    description: Optional comma-separated list of focus areas chosen from "consistency", "ergonomics", "evolvability", "security", "performance". Pass empty string for all five.
    required: false
---

> 🎯 **场景**：审 API 设计而非实现代码——命名一致性 / 资源建模 / 错误约定 / 版本化策略 / 安全 / 易用性。REST / GraphQL / gRPC 各自的最佳实践不同。设计阶段评审 / 公开 API 上线前必走。

## Quick Use

**Use when:** You're reviewing an API design (not implementation) and want structured findings on consistency, ergonomics, evolvability, security, and performance — calibrated to the API style.
**Fill in:** `{{api_spec_or_examples}}` = the design (spec or representative examples); `{{api_style}}` = `rest` / `graphql` / `grpc` / `rpc_other`; `{{review_focus}}` = optional focus areas.
**You'll get:** Per-area findings with severity, suggestions, and an overall design verdict. Output is JSON.

## Purpose

Review the design (not implementation) of an API on multiple
dimensions: consistency (naming, error shape, pagination),
ergonomics (does the common case feel natural), evolvability (can
this be versioned without breaking), security (auth model,
rate-limit, secrets), and performance (N+1, batch endpoints,
caching). Different API styles have different best practices — the
card adapts. Used pre-launch on internal or public APIs, in design
RFCs, and as a prompt for API design discussion.

## Prompt

```text
You review an API design.

API spec or examples:
{{api_spec_or_examples}}

API style: {{api_style}}

Review focus (may be empty for all):
{{review_focus}}

Style-specific best practices to check:
- "rest"   : Resource-oriented URLs, HTTP verbs match action,
              consistent pagination, proper status codes,
              hypermedia where appropriate.
- "graphql": Schema design (avoid n+1 patterns in resolvers),
              fragment-friendly types, error handling via union
              types or extensions, deprecation discipline.
- "grpc"   : Proto design (versioned package, no semantic-meaning
              field renames), rpc method naming, streaming where
              appropriate, error code discipline.
- "rpc_other" : General rpc principles — operation naming,
                argument shape, error model.

For each area in review_focus (or all 5 if empty):
- Identify findings.
- Severity: "low" (nit), "medium" (will hurt over time), "high"
  (will hurt at v1 launch).

Be specific: cite an endpoint / query / rpc by name.

Return ONLY this JSON object:
{
  "findings_by_area": {
    "consistency": [{"finding": "<short>", "location": "<short>", "severity": "low|medium|high", "suggestion": "<short>"}],
    "ergonomics": [...],
    "evolvability": [...],
    "security": [...],
    "performance": [...]
  },
  "design_strengths": ["<short>"],
  "overall_verdict": "ship" | "iterate" | "redesign",
  "verdict_reason": "<one sentence>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Verdict rule:
- "redesign"  : 2+ "high" findings or fundamental style mismatch.
- "iterate"   : 1 "high" or several "medium".
- "ship"      : Only "low" findings or none.
```

## Example

**Input:**

```text
api_style: "rest"
api_spec_or_examples: <endpoints: GET /users, POST /createUser, GET /users/get/:id, DELETE /removeUser/:id>
```

**Expected output (abridged):**

```json
{
  "findings_by_area": {
    "consistency": [
      {"finding": "Mixing resource-style (/users, /users/:id) and verb-style (/createUser, /removeUser) URLs.", "location": "POST /createUser, DELETE /removeUser/:id", "severity": "high", "suggestion": "Use POST /users and DELETE /users/:id; verbs belong in HTTP methods, not URLs."},
      {"finding": "/users/get/:id has redundant 'get' segment.", "location": "GET /users/get/:id", "severity": "medium", "suggestion": "Use GET /users/:id."}
    ],
    "ergonomics": [],
    "evolvability": [],
    "security": [{"finding": "No visible auth model.", "location": "all endpoints", "severity": "high", "suggestion": "Document auth scheme (bearer token / oauth / etc.) in spec."}],
    "performance": []
  },
  "design_strengths": ["Resource collection at /users follows convention"],
  "overall_verdict": "redesign",
  "verdict_reason": "Two high-severity issues (verb-style URLs, missing auth) require coordinated redesign before shipping.",
  "decision_basis": "Inconsistent URL style + no auth = needs redesign before any client integrates."
}
```

## Failure Modes

- **Style mismatch** — applying REST principles to a GraphQL spec.
  Always anchor to api_style; check first that the principles
  applied match the style.
- **Generic findings** — "API could be more consistent". Reject
  findings shorter than ~10 words or without specific location.
- **Severity inflation** — every finding is "high".
- **Missing security** — model glosses over auth. Audit security
  area always being non-empty unless the spec explicitly addresses
  auth.
- **Strengths inflation** — listing every endpoint as a strength.
  Cap at 3 distinct strengths; only call out genuinely good design.

## Tuning Notes

- 模型差异：frontier 模型必须的——需要稳定的 style-specific best
  practices 知识. 中档模型常 mix-and-match REST/GraphQL practices.
- 温度：`0.0`–`0.2`.
- 与 `code/code-review-checklist` 的关系：那张卡审实现代码；本卡审
  API 设计. 形态不同, 焦点不同.
- 与 `code/security-review` 的关系：那张卡审实现的安全 issues; 本卡
  审设计的安全 model (是否有 auth, 是否有 rate limit, 等). 互补.
- 输入选择: spec 优于 examples; openapi.yaml > 几个 endpoint 例子.
  例子模式适合早期设计 brainstorm.
- 高 leverage 用法: design RFC 阶段过本卡, 修正 → 实现 → ship. 比
  shipped 后发现需要 v2 便宜 100x.
- 不要 overrule the team: 本卡是 critique tool, 最终设计决策是
  team 的. 有些"违反 best practice"是经过权衡的产品决策.

## Changelog

- `0.1.0` — Initial card.
