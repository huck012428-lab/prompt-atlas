---
id: agent/plan-and-execute-planner
title: Plan-and-Execute Upfront Planner
version: 0.1.0
status: stable
direction: agent
tags: [planning, decomposition, structured-output]
audience: [prompt-engineer, app-builder, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: user_goal
    description: The user's high-level goal for this agent session.
    required: true
  - name: tool_catalog
    description: JSON list of available tools, each with name, description, parameters schema.
    required: true
---

## Quick Use

**Use when:** Your agent's goal is predictable enough to plan upfront instead of step-by-step (linear dependencies, known sub-problems).
**Fill in:** `{{user_goal}}` = the agent's goal; `{{tool_catalog}}` = JSON list of available tools.
**You'll get:** A 2-7 step linear plan with explicit dependency edges and a final synthesis step. Output is JSON.

## Purpose

Produce a complete multi-step plan upfront, before any tool calls,
given a user goal and a tool catalog. Each step names the tool to call
and the dependency on prior steps' outputs. Used as an alternative to
ReAct-style interleaved reasoning for goals where the structure is
predictable enough to plan first and execute second — typically tasks
with linear dependency chains and well-known sub-problems. Output is
structured so an executor can run the plan deterministically and a
re-planner can edit it in place.

## Prompt

```text
You produce a complete plan to achieve a user goal using the available
tools. Plan FIRST; do not execute. The output is a sequence of steps
the downstream executor will run.

User goal:
{{user_goal}}

Tool catalog:
{{tool_catalog}}

Rules:
1. Use 2-7 steps. Fewer is better when achievable.
2. Each step must call exactly one tool from the catalog OR be a
   final synthesis step (type=synthesize) that combines prior outputs
   into the final answer.
3. Each step MUST list which prior step outputs it depends on, by
   step id. The first step has no dependencies.
4. Do not invent tools. If the goal cannot be reached with the given
   tools, set "feasible: false" and stop.
5. Do not embed conditional branching ("if X then Y else Z"). If the
   plan needs branching, that is a reflection / re-planning event,
   not a single plan.

Return ONLY this JSON object:
{
  "feasible": true | false,
  "infeasibility_reason": "<if feasible=false: why; else empty string>",
  "steps": [
    {
      "id": "s1",
      "type": "tool_call" | "synthesize",
      "description": "<one sentence: what this step accomplishes>",
      "tool": "<tool name from catalog, or empty if type=synthesize>",
      "arguments_template": { ... }, /* may reference {{s1.output}} for prior step outputs */
      "depends_on": ["s0_or_empty", ...]
    }
    /* ... */
  ],
  "final_step_id": "<id of the step that produces the final answer>",
  "decision_basis": "<one sentence, <=30 words, explaining the plan shape>"
}
```

## Example

**Input:**

```text
user_goal: "Find the population of Reykjavik and compute its share of Iceland's total population."
tool_catalog: [
  {"name": "search", "description": "Web search", "parameters": {"query": "string"}},
  {"name": "calc",   "description": "Arithmetic on a single expression", "parameters": {"expression": "string"}}
]
```

**Expected output:**

```json
{
  "feasible": true,
  "infeasibility_reason": "",
  "steps": [
    {
      "id": "s1",
      "type": "tool_call",
      "description": "Find Reykjavik's current population.",
      "tool": "search",
      "arguments_template": {"query": "Reykjavik population 2024"},
      "depends_on": []
    },
    {
      "id": "s2",
      "type": "tool_call",
      "description": "Find Iceland's total population.",
      "tool": "search",
      "arguments_template": {"query": "Iceland total population 2024"},
      "depends_on": []
    },
    {
      "id": "s3",
      "type": "tool_call",
      "description": "Compute the share as a percentage.",
      "tool": "calc",
      "arguments_template": {"expression": "{{s1.output}} / {{s2.output}} * 100"},
      "depends_on": ["s1", "s2"]
    },
    {
      "id": "s4",
      "type": "synthesize",
      "description": "Compose the final answer using the share value.",
      "tool": "",
      "arguments_template": {},
      "depends_on": ["s1", "s2", "s3"]
    }
  ],
  "final_step_id": "s4",
  "decision_basis": "Two parallel lookups, then a calc step, then a synthesis — linear chain with one fan-in."
}
```

## Failure Modes

- **Over-decomposition** — model produces 8+ steps for a 3-step task,
  bloating execution. Mitigation: the rule "use 2-7 steps, fewer is
  better"; reject plans whose final step is just "format the answer
  nicely" added on top of an already-complete plan.
- **Implicit branching** — model writes a step description like "if
  the previous step returned no results, search more broadly". Plans
  must be linear; branching is a reflection event. Detect by scanning
  step descriptions for "if / when / unless".
- **Missing dependencies** — step uses `{{s1.output}}` but does not
  list `s1` in `depends_on`. The downstream executor needs accurate
  dependencies to schedule and to detect cycles. Validate the
  reference graph before executing.
- **Tool hallucination** — plan calls a tool not in the catalog. The
  rubric forbids this; reject and require re-plan.
- **Premature `feasible: false`** — model gives up when the plan
  would actually work with creative tool composition. Sample false
  outputs and check that the listed tools genuinely cannot reach the
  goal.
- **Stale plan after first failure** — the executor takes step 1, it
  fails, and the rest of the plan is now invalid. Plans need to be
  re-planned, not patched in place; route to
  `agent/self-critique-reflection` on first failure.

## Tuning Notes

- 模型差异：plan quality 对模型推理能力高度敏感；frontier 模型必须的。
  中档模型经常给"linear chain of trivial searches"，缺少 fan-in 和
  synthesis。
- 温度：`0.0`–`0.3`。
- 与 `agent/react-planner-with-tool-schema` 的对比：ReAct 适合不可预测
  的 goal（每一步根据上一步观察决定）；plan-and-execute 适合
  predictable goal（从 user goal 就能猜出大致结构）。Eval-set 类、
  benchmark 类任务通常 plan-and-execute 更高效；探索类、debug 类任务
  通常 ReAct 更合适。
- 与 `agent/self-critique-reflection` 的关系：plan 一旦定下，执行中
  失败应触发 reflection 决定是否 re-plan，而不是在 plan 内部硬编码
  branching 逻辑。
- 与 `agent/tool-call-repair` 的关系：plan 中的 `arguments_template`
  在执行时如果 schema 不通过，先用 tool-call-repair 修一次；连续失败
  再 reflection。
- 上线建议：在执行前用一个 cheap validator 跑一遍 plan（依赖图无环、
  无幻觉工具、final_step_id 存在），失败直接 re-plan，不要让 bad
  plan 进入执行阶段烧 token。

## Changelog

- `0.1.0` — Initial card.
