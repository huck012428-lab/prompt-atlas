---
id: code/dependency-impact-analyzer
title: Dependency Impact Analyzer
version: 0.1.0
status: experimental
direction: code
tags: [extraction, classification, structured-output]
audience: [app-builder, prompt-engineer]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: target_function_signature
    description: The function / API / type whose change you're considering (e.g. "def parse_user(input_str) -> User", "GET /api/users/:id returning User schema").
    required: true
  - name: proposed_change
    description: One paragraph describing what about the function will change (signature, behavior, return type, side effects).
    required: true
  - name: codebase_sample
    description: A representative slice of code that USES the target function (call sites, type usages, etc.) — typically 500-2000 lines covering diverse usage patterns.
    required: true
---

> 🎯 **场景**：评估一个函数 / API 改动会影响什么——找出依赖它的调用点、按"是否需要修"分类、估改动量。before-the-PR 评估，避免动手改了才发现影响 50 处。

## Quick Use

**Use when:** You're planning to change a function signature / API contract / shared type and want to know what breaks before you start.
**Fill in:** `{{target_function_signature}}` = the thing you'd change; `{{proposed_change}}` = what about it changes; `{{codebase_sample}}` = code that uses it.
**You'll get:** A list of impact points with classification (no-change-needed / minor-update / breaking), aggregate work estimate, and migration suggestions. Output is JSON.

## Purpose

Estimate the impact of changing a shared function / API / type
across a codebase BEFORE making the change. Identifies call sites
that will need updates, classifies them by required work, and
suggests batch migration patterns. Used in the planning step of
medium-to-large refactors. Cheaper than "ship and let CI tell you
what broke" for breaking changes.

## Prompt

```text
You analyze the impact of a proposed change to a shared function /
API / type, against a sample of code that uses it.

Target:
{{target_function_signature}}

Proposed change:
{{proposed_change}}

Code sample (uses the target):
{{codebase_sample}}

Steps:
1. Find every call site / usage of the target in codebase_sample.
   Include type-only usages (signatures, generics, casts) where
   relevant.

2. For each call site, classify impact:
   - "no_change_needed"  : The call site continues to work
                            unchanged after the proposed change
                            (e.g. old signature still backward-
                            compatible at this call site).
   - "minor_update"     : Mechanical change — rename, swap arg
                          order, simple wrap (1-3 line changes).
   - "breaking"         : Logic change required — caller's logic
                          must adapt to new behavior or new return
                          shape.
   - "requires_design"  : Caller's contract with downstream depends
                          on the old behavior in non-trivial ways;
                          a redesign discussion is needed.

3. Group impact by file / module to produce per-file work estimates.

4. Suggest a migration pattern when many sites have the same kind
   of change (codemod / sed / find-replace).

5. Identify any "ripple_effects" — places where this change
   cascades into changes in other modules (e.g. type changes
   propagate through generics).

Return ONLY this JSON object:
{
  "call_sites": [
    {
      "location": "<file:line or function name>",
      "current_usage": "<short snippet showing how it's called>",
      "impact": "no_change_needed" | "minor_update" | "breaking" | "requires_design",
      "fix_suggestion": "<short>"
    }
  ],
  "impact_summary": {
    "total_sites": <integer>,
    "no_change_needed": <integer>,
    "minor_update": <integer>,
    "breaking": <integer>,
    "requires_design": <integer>
  },
  "migration_patterns": [
    {"pattern": "<pattern name>", "applicable_count": <integer>, "approach": "<short>"}
  ],
  "ripple_effects": [
    {"area": "<module / abstraction>", "description": "<short>"}
  ],
  "estimated_work": "<rough estimate>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
target_function_signature: "def parse_user(input_str: str) -> User"
proposed_change: "Add a required `tenant_id: str` parameter to support multi-tenancy. Old callers will fail to compile."
codebase_sample: |
  # api/handlers.py
  user = parse_user(request.body)
  
  # tests/test_user.py
  def test_basic():
      user = parse_user("{}")
  
  # workers/sync.py
  for line in feed:
      u = parse_user(line)
      save(u)
```

**Expected output:**

```json
{
  "call_sites": [
    {
      "location": "api/handlers.py",
      "current_usage": "user = parse_user(request.body)",
      "impact": "minor_update",
      "fix_suggestion": "Add tenant_id: parse_user(request.body, tenant_id=request.tenant_id)"
    },
    {
      "location": "tests/test_user.py",
      "current_usage": "user = parse_user('{}')",
      "impact": "minor_update",
      "fix_suggestion": "Add a fixture tenant: parse_user('{}', tenant_id='test_tenant')"
    },
    {
      "location": "workers/sync.py",
      "current_usage": "u = parse_user(line)",
      "impact": "breaking",
      "fix_suggestion": "Worker has no tenant context — needs design: pass tenant_id from feed metadata, OR run worker per-tenant. Cannot mechanically fix."
    }
  ],
  "impact_summary": {
    "total_sites": 3,
    "no_change_needed": 0,
    "minor_update": 2,
    "breaking": 1,
    "requires_design": 0
  },
  "migration_patterns": [
    {"pattern": "API handler with request context", "applicable_count": 1, "approach": "Pass request.tenant_id at call site."},
    {"pattern": "Test fixture", "applicable_count": 1, "approach": "Add tenant_id='test_tenant' to test calls."}
  ],
  "ripple_effects": [
    {"area": "workers/sync.py and any worker code", "description": "Workers don't have request-level tenant context; this signature change forces a tenant-aware worker design."}
  ],
  "estimated_work": "2-4 hours for the 2 minor updates; 1-2 days for the breaking worker case (design + implementation).",
  "decision_basis": "Two minor mechanical updates and one genuine breaking case in workers; the worker case is the bottleneck for the change."
}
```

## Failure Modes

- **Missed call sites** — model overlooks usages, especially in
  test files, generic type contexts, or string-based references
  (e.g. `getattr(module, 'parse_user')`). Pair with a real
  static-analysis tool for high-stakes refactors.
- **Over-classification** — every site marked "breaking". Each
  classification needs evidence; sample minor_update outputs and
  verify they really are mechanical.
- **Hallucinated migration patterns** — invented "pattern" entries.
  Verify each pattern.applicable_count corresponds to actual sites.
- **Ripple-effect blindness** — change affects type signature
  generics that flow through 5 other modules; model only sees
  direct calls. Acknowledge limitation in `decision_basis` when
  scope is uncertain.
- **Estimate hallucination** — work estimate based on call-site
  count alone, missing per-site complexity. Use as hint only.

## Tuning Notes

- 模型差异：必须 frontier 模型。需要同时识别 call sites + 估改动
  + 推断 ripple effects。中档模型在 ripple effects 上几乎总是漏。
- 温度：`0.0`，分析必须可重现。
- codebase_sample 选择：要包含**多样化** call sites（API handler、
  test、worker、CLI 等不同角色），不只是相同模式重复 100 次。
- 与真实静态分析的关系：本卡是 LLM-based 分析，不能替代 LSP /
  jedi / pyright / tsc 等 deterministic 工具。生产用法：用 LSP 找
  全部 call sites（exhaustive） → 用本卡做 impact 分类 + work 估计
  （semantic）。
- 与 `code/migration-plan-generator` 的对比：那张卡是大版本升级
  （框架 / runtime / spec），本卡是单点变更（一个函数 / API）。
- 与 `code/refactor-suggestion` 的关系：refactor 是建议改怎么改；
  本卡是评估改了影响多大。两者可串联：先 impact analyze → 决定要不
  要做 → refactor 卡设计具体改法。

## Changelog

- `0.1.0` — Initial card.
