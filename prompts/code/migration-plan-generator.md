---
id: code/migration-plan-generator
title: Code Migration Plan Generator
version: 0.1.0
status: stable
direction: code
tags: [code-review, generation, structured-output, decomposition]
audience: [app-builder, prompt-engineer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: from_version
    description: Current version / spec the codebase uses (e.g. "React 16", "Python 3.7", "OpenAPI 2.0", "Kubernetes 1.21").
    required: true
  - name: to_version
    description: Target version / spec to migrate to (e.g. "React 18", "Python 3.12", "OpenAPI 3.1", "Kubernetes 1.28").
    required: true
  - name: representative_code
    description: A representative slice of the codebase that uses from_version (one or more files / snippets, ~500-2000 lines), so the plan can identify concrete migration points.
    required: true
---

> 🎯 **场景**：跨大版本迁移规划——React 16→18、Python 3.7→3.12、Kubernetes 老版升新版等。基于代码样本识别具体改动点，按 risk + 工作量产出阶段化迁移 plan。比读 changelog 自己列 todo 更系统。

## Quick Use

**Use when:** You're planning a major version migration (framework upgrade, runtime upgrade, API spec migration) and want a phased plan based on your actual code rather than generic upgrade-guide reading.
**Fill in:** `{{from_version}}` = current version; `{{to_version}}` = target; `{{representative_code}}` = a code slice that uses from_version.
**You'll get:** A phased migration plan with breaking-change items, work estimates, risk levels, suggested ordering, and decision points. Output is JSON.

## Purpose

Produce a phased migration plan to move a codebase from one major
version to another. The plan grounds in the user's actual code (not
just the upgrade guide), identifies specific migration points,
estimates work, and orders phases by dependency and risk. Used
before kicking off a multi-week migration to align on scope and
sequencing. Output is structured so the plan can be tracked as
issues / tickets in a project management system.

## Prompt

```text
You produce a phased migration plan from one version to another,
grounded in the user's actual code.

From: {{from_version}}
To:   {{to_version}}

Representative code (uses from_version):
{{representative_code}}

Steps:
1. Identify breaking-change items between from_version and
   to_version. Use your knowledge of the version-specific changelog
   AND the patterns visible in representative_code.

2. For each breaking-change item that is RELEVANT to the visible
   code (skip items that don't apply):
   - Cite an example location in representative_code.
   - Estimate work: "trivial" (mechanical replace), "small"
     (per-call adaption), "medium" (refactor), "large" (architecture
     change).
   - Risk: "low" (purely mechanical), "medium" (subtle semantic
     differences), "high" (deprecated behavior with no clean
     replacement).

3. Group changes into phases. Ordering rule:
   - Phase 1: tooling / build / dependency setup (compiler, lint
     config).
   - Phase 2: trivial mechanical replaces.
   - Phase 3: small per-call adaptations.
   - Phase 4: medium refactors.
   - Phase 5: large changes / architecture shifts.
   Phases run sequentially; later phases depend on earlier.

4. Identify "decision_points" — places where the user must choose
   between options (e.g. "React 18 strict mode: enable now or
   later", "Python 3.12 typing changes: opt in or use shim").

5. Identify "compatibility_gates" — points where the code temporarily
   needs to support BOTH versions (e.g. for canary rollout). Note
   shim libraries / patterns.

Return ONLY this JSON object:
{
  "applicability_assessment": "<one sentence: how much of the upgrade actually applies given visible code>",
  "phases": [
    {
      "phase_number": <1-5>,
      "phase_name": "<short>",
      "items": [
        {
          "change": "<one-line description>",
          "example_location": "<short pointer into representative_code>",
          "work_estimate": "trivial" | "small" | "medium" | "large",
          "risk": "low" | "medium" | "high"
        }
      ]
    }
  ],
  "decision_points": [
    {"decision": "<short>", "options": ["<a>", "<b>"], "recommendation": "<one of the options or 'consult'>"}
  ],
  "compatibility_gates": [
    {"need": "<short>", "approach": "<short>"}
  ],
  "estimated_total_work": "<rough estimate in person-weeks for a senior dev familiar with the codebase>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
from_version: "React 16"
to_version: "React 18"
representative_code: |
  class App extends React.Component {
      componentWillMount() { /* legacy */ }
      render() {
          return ReactDOM.render(<MyComponent />, document.getElementById('root'));
      }
  }
```

**Expected output:**

```json
{
  "applicability_assessment": "Visible code uses three React-16 patterns that change in 18: legacy class lifecycle (componentWillMount), ReactDOM.render API, and lacks the new createRoot pattern.",
  "phases": [
    {
      "phase_number": 1,
      "phase_name": "Tooling and dependencies",
      "items": [
        {"change": "Update package.json to React 18; install matching ReactDOM 18", "example_location": "package.json (not shown — implied)", "work_estimate": "trivial", "risk": "low"}
      ]
    },
    {
      "phase_number": 2,
      "phase_name": "Mechanical API replaces",
      "items": [
        {"change": "Replace ReactDOM.render with createRoot().render", "example_location": "App.render() return statement", "work_estimate": "small", "risk": "low"}
      ]
    },
    {
      "phase_number": 3,
      "phase_name": "Lifecycle deprecation",
      "items": [
        {"change": "Replace componentWillMount with componentDidMount or constructor logic", "example_location": "App.componentWillMount", "work_estimate": "small", "risk": "medium"}
      ]
    }
  ],
  "decision_points": [
    {"decision": "Enable React 18 Strict Mode immediately", "options": ["enable now (catches double-rendering issues)", "defer until app stable"], "recommendation": "defer until app stable"}
  ],
  "compatibility_gates": [
    {"need": "Other parts of codebase using ReactDOM.render", "approach": "Migrate all entry points in same PR; createRoot and render coexist but mixing causes hydration warnings."}
  ],
  "estimated_total_work": "1-2 person-weeks for a senior React dev on a small app",
  "decision_basis": "Three concrete migration points visible; ordered by mechanical-first, lifecycle-deprecation second; small total scope."
}
```

## Failure Modes

- **Generic changelog dumping** — model lists every breaking change
  in the version regardless of relevance. Filter against
  representative_code; skip changes that don't apply.
- **Work estimate hallucination** — "trivial" on a large refactor.
  Calibrate by the work definition: trivial = sed replace, small =
  per-call, medium = refactor function, large = restructure
  architecture.
- **Phase miscategorization** — putting a "trivial" item in phase 4.
  Validate ordering rule.
- **Missed compatibility gates** — large migrations always need
  shims; if compatibility_gates is empty for a major version jump,
  the rubric missed something.
- **Knowledge cutoff issues** — for very recent versions, model
  knowledge may be incomplete. Flag if `to_version` released after
  model cutoff; the plan is best-effort.

## Tuning Notes

- 模型差异：frontier 模型必须的。需要同时具备 changelog 知识 + code
  pattern 识别 + work 估计能力。中档模型在 estimate 上经常飘。
- 温度：`0.0`–`0.3`。
- representative_code 选择：选最 representative 的（含主要 pattern
  和最复杂 case）。500-2000 行是甜点；少了 pattern 不全，多了 prompt
  挤占。
- 与 `code/code-summary-for-pr` 的对比：本卡 forward-looking（plan
  what to do），summary-for-pr backward-looking（describe what was
  done）。
- 与 `code/refactor-suggestion` 的关系：refactor 是单文件改进；本卡
  是跨版本系统迁移。前者用于 PR 改进，后者用于 sprint planning。
- estimated_total_work 是 hint：只是基于代码量和复杂度的粗估，**不**
  考虑 testing / review / 部署 / 协调成本。生产规划中加 1.5-2x
  buffer。
- 用作 RFC 起草：本卡产出可作为内部 migration RFC 的 first draft，
  人工再扩充 deployment / rollback / metrics 策略。

## Changelog

- `0.1.0` — Initial card.
