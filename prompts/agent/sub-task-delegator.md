---
id: agent/sub-task-delegator
title: Sub-Task Delegator (multi-agent prep)
version: 0.1.0
status: experimental
direction: agent
tags: [planning, decomposition, structured-output]
audience: [prompt-engineer, app-builder, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: complex_task
    description: A complex user task that benefits from being split across multiple specialized agents or workers.
    required: true
  - name: available_workers
    description: A JSON array describing available agents / workers, each with name, capabilities (one-line description), and any constraints.
    required: true
---

> 🎯 **场景**：多 agent 派发的 supervisor——把复杂任务拆给一组特定能力的 worker（researcher / writer / fact-checker 等），含输入输出契约 + 依赖图。多 agent 系统的前置编排。

## Quick Use

**Use when:** A user task is too complex for one agent and you want to split it across specialized workers / agents (multi-agent foundation).
**Fill in:** `{{complex_task}}` = the user's full task; `{{available_workers}}` = JSON array of workers each with name + capability description.
**You'll get:** A list of sub-tasks each delegated to a specific worker, with explicit dependencies, hand-off contracts, and a final integration step. Output is JSON.

## Purpose

Take a complex user task plus a roster of available agents / workers,
and produce a structured delegation plan that names which sub-task
goes to which worker, what each worker needs as input, and how the
results are integrated. Used as the **front-end** of a multi-agent
system — the supervisor / orchestrator step before any worker is
invoked. Distinct from `agent/plan-and-execute-planner`, which assigns
each step to a tool; here each sub-task is assigned to a peer agent
with broader capabilities. Output is structured so the orchestration
layer can dispatch sub-tasks in parallel where dependencies allow.

## Prompt

```text
You are decomposing a complex task and delegating sub-tasks to a roster
of specialized workers / agents. Goal: produce a delegation plan that
the orchestrator can dispatch.

Complex task:
{{complex_task}}

Available workers:
{{available_workers}}

Rules:
1. Use 2-6 sub-tasks. Fewer when achievable. Decomposing a one-sub-task
   plan is unnecessary overhead.
2. Each sub-task must be assigned to a worker present in the roster.
   Do NOT invent workers or duplicate worker assignments unless the
   workers can run in parallel and produce non-overlapping outputs.
3. Each sub-task must have a self-contained `input_contract` — what
   the worker needs to do its job, expressed as fields a downstream
   orchestrator can populate from prior sub-task outputs.
4. Each sub-task must have an `output_contract` — what the worker is
   expected to return, in a form that downstream sub-tasks (or the
   final integration step) can consume.
5. Mark dependencies explicitly: which sub-tasks must complete before
   this one starts. Dependency-free sub-tasks can be dispatched in
   parallel.
6. Always end with an `integration` sub-task that combines worker
   outputs into the final answer. The integrator can be a worker
   from the roster OR a synthesis prompt run by the orchestrator
   itself (set worker: "orchestrator" in that case).
7. If the task cannot be served by the available workers, set
   `feasible: false` and identify the missing capability.

Return ONLY this JSON object:
{
  "feasible": true | false,
  "missing_capability": "<if feasible=false: what capability is missing; else empty>",
  "sub_tasks": [
    {
      "id": "st1",
      "description": "<one-sentence description of what this sub-task does>",
      "assigned_worker": "<worker name from roster, or 'orchestrator' for the integrator>",
      "input_contract": {
        "<field name>": "<what this field provides; reference {{stN.output.field}} for upstream outputs>"
      },
      "output_contract": {
        "<field name>": "<what this field will contain when the worker completes>"
      },
      "depends_on": ["<id of upstream sub-task>"]
    }
    /* ... */
  ],
  "final_sub_task_id": "<id of the integration sub-task>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
complex_task: "Research the top 3 cloud providers' GPU pricing for H100 instances in November 2024 and produce a comparison table with notes on availability."
available_workers: [
  {"name": "researcher", "capabilities": "Web search, summarize findings, follow citations", "constraints": "No real-time pricing API access"},
  {"name": "writer", "capabilities": "Compose tables, summaries, structured documents from inputs", "constraints": ""},
  {"name": "fact_checker", "capabilities": "Verify factual claims against sources, flag stale or unverifiable claims", "constraints": ""}
]
```

**Expected output:**

```json
{
  "feasible": true,
  "missing_capability": "",
  "sub_tasks": [
    {
      "id": "st1",
      "description": "Research H100 instance pricing for AWS, Azure, and GCP as of November 2024.",
      "assigned_worker": "researcher",
      "input_contract": {
        "topic": "H100 GPU instance pricing on AWS, Azure, GCP in November 2024 with availability notes"
      },
      "output_contract": {
        "findings": "Per-provider pricing claims with citation URLs and any availability caveats"
      },
      "depends_on": []
    },
    {
      "id": "st2",
      "description": "Verify the pricing claims and citations from the research findings; flag stale or unverifiable.",
      "assigned_worker": "fact_checker",
      "input_contract": {
        "findings_to_verify": "{{st1.output.findings}}"
      },
      "output_contract": {
        "verified_findings": "Findings with each claim labeled verified/stale/unverifiable plus the citation source"
      },
      "depends_on": ["st1"]
    },
    {
      "id": "st3",
      "description": "Compose a comparison table with availability notes from the verified findings.",
      "assigned_worker": "writer",
      "input_contract": {
        "verified_data": "{{st2.output.verified_findings}}"
      },
      "output_contract": {
        "comparison_table_markdown": "Markdown table of provider × instance pricing with a notes column"
      },
      "depends_on": ["st2"]
    },
    {
      "id": "st4",
      "description": "Combine the comparison table and any unverified-claim flags into the final answer for the user.",
      "assigned_worker": "orchestrator",
      "input_contract": {
        "table": "{{st3.output.comparison_table_markdown}}",
        "verification_flags": "{{st2.output.verified_findings}}"
      },
      "output_contract": {
        "final_answer": "Markdown table with verification footnotes for stale or unverifiable rows"
      },
      "depends_on": ["st3", "st2"]
    }
  ],
  "final_sub_task_id": "st4",
  "decision_basis": "Linear chain — research, verify, write, integrate — using each worker for its specialized capability."
}
```

## Failure Modes

- **Worker hallucination** — plan assigns sub-tasks to workers not in
  the roster ("data_analyst" when only researcher/writer/fact_checker
  exist). The rubric forbids this; reject at parse time.
- **Capability mismatch** — sub-task assigned to wrong worker (e.g.
  asking the writer to do web search when the researcher has that
  capability). Mitigation: validate `assigned_worker` against the
  roster's capability descriptions; flag mismatches for re-plan.
- **Over-decomposition** — model produces 8 sub-tasks where 3 would
  suffice, multiplying coordination cost. Mitigation: rule "use 2-6
  sub-tasks, fewer when achievable"; reject plans exceeding 6.
- **Implicit dependencies** — sub-task references `{{st1.output.X}}`
  but doesn't list `st1` in `depends_on`. Validate the dependency
  graph from the input/output contract references.
- **Circular dependencies** — st1 depends on st2 and vice versa.
  Validate as DAG before dispatch; force re-plan on cycles.
- **`feasible: false` under-trigger** — model fakes feasibility when
  the roster genuinely lacks a needed capability (e.g. user asked
  for image analysis but no vision worker exists). Spot-check
  feasible plans against capability list; if a sub-task can't
  actually be done by its assigned worker, the plan was bad.
- **Missing integration step** — plan has no orchestrator integration
  sub-task; outputs are left scattered. Rule 6 enforces this; reject
  plans missing the final integration.

## Tuning Notes

- 模型差异：本卡对模型的"任务理解 + 资源分配"判断同时要求高，
  frontier 模型显著优于中档。中档模型常出现 capability mismatch
  （把研究任务派给 writer）。
- 温度：`0.0`–`0.3`。delegation 一致性优先。
- 与 `agent/plan-and-execute-planner` 的对比：plan-and-execute 把
  goal 拆成 tool call 序列（每步是 LLM + 一个 tool）；本卡把 goal
  拆成 worker 序列（每步是另一个 agent）。前者细粒度，后者粗粒度。
  前者在 tool ecosystem 上跑；后者在 agent ecosystem 上跑。
- 与 `cot/least-to-most-decomposition` 的对比：least-to-most 是纯
  推理拆解（不分配资源）；本卡是带资源分配的拆解。当 sub-tasks 都能
  由一个推理 LLM 完成时用 least-to-most；当 sub-tasks 真的需要不同
  agent / 不同模型 / 不同上下文时用本卡。
- worker roster 设计：roster 中每个 worker 的 capability 描述要
  具体到 verb 和 domain（"verify factual claims against sources"
  好于 "do verification"）。模糊描述会导致 capability mismatch。
- 单 prompt vs multi-call：本卡产出的是 plan，不是执行。Plan 由
  orchestrator 解析后并行/串行 dispatch 给 workers。每个 worker
  又可以再用本卡（recursive delegation），但要小心爆炸。
- 用作 multi-agent 训练数据：本卡产出的 (complex_task, plan) 对
  可以作为 supervisor agent 的 SFT 数据；plan 中的 input/output
  contracts 可以作为协议规范的训练信号。

## Changelog

- `0.1.0` — Initial card.
