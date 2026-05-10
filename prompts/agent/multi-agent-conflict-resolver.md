---
id: agent/multi-agent-conflict-resolver
title: Multi-Agent Conflict Resolver
version: 0.1.0
status: experimental
direction: agent
tags: [planning, classification, structured-output, decomposition]
audience: [prompt-engineer, app-builder, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: original_task
    description: The original task being worked on by multiple agents.
    required: true
  - name: agent_outputs
    description: A JSON array of agent outputs, each with `agent_name`, `output`, and optional `reasoning_summary`. Two or more agents must have produced conflicting outputs.
    required: true
---

> 🎯 **场景**：多 agent 系统中，子 agent 给出冲突结论时怎么办——是 vote？trust 最强的 agent？escalate？本卡按冲突类型（factual / value-based / methodological）选不同处理，输出 reconciled 结论 + 处置理由。

## Quick Use

**Use when:** You're orchestrating multiple agents (sub-task delegation, parallel reasoning) and they produced conflicting outputs that need reconciliation before continuing.
**Fill in:** `{{original_task}}` = the task; `{{agent_outputs}}` = JSON array of (agent_name, output, reasoning_summary) records.
**You'll get:** Conflict classification, reconciled output, decision rationale, and (if needed) escalation flag. Output is JSON.

## Purpose

Reconcile conflicting outputs from multiple agents working on the
same task. Different conflict types call for different resolution
strategies: factual conflicts can be resolved by checking which
agent has authoritative source; value-based conflicts may need to
preserve disagreement; methodological conflicts may indicate one
agent used wrong approach. Used in multi-agent orchestration as
the merge step.

## Prompt

```text
You reconcile conflicting outputs from multiple agents.

Original task:
{{original_task}}

Agent outputs:
{{agent_outputs}}

Steps:
1. Classify the conflict:
   - "factual"        : Agents disagree on a fact (e.g. one says
                         population is 140K, another 180K).
   - "value_based"    : Agents disagree on a judgment / trade-off
                         where multiple positions are defensible.
   - "methodological" : Agents used different methods / frames; the
                         right answer depends on which method is
                         appropriate.
   - "scope"          : Agents addressed different parts of the
                         task (not really conflict, just complementary).

2. Pick reconciliation strategy:
   - For "factual": prefer the agent with stronger source / more
     specific claim; if neither has strong source, mark uncertain
     and recommend further research.
   - For "value_based": don't pick a winner — preserve the
     disagreement and present trade-offs. Escalate if a decision
     is required.
   - For "methodological": pick the appropriate method for the
     task; explain why.
   - For "scope": merge complementary outputs into a unified
     result.

3. Produce the reconciled output. Note which inputs were merged /
   selected / dropped.

Return ONLY this JSON object:
{
  "conflict_type": "factual" | "value_based" | "methodological" | "scope",
  "conflict_description": "<one sentence>",
  "reconciliation_strategy": "<which strategy applied>",
  "reconciled_output": "<the merged result, OR explicit disagreement preservation>",
  "agent_decisions": [
    {"agent_name": "<name>", "decision": "kept" | "selected" | "dropped" | "merged", "reason": "<short>"}
  ],
  "escalate_to_human": true | false,
  "escalation_reason": "<if escalate=true: why; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
original_task: "Recommend a programming language for a data-engineering team's new project."
agent_outputs: [
  {"agent_name": "performance_specialist", "output": "Use Rust — best runtime performance.", "reasoning_summary": "Performance benchmarks favor Rust by 2-5x."},
  {"agent_name": "ecosystem_specialist", "output": "Use Python — best ecosystem for data work.", "reasoning_summary": "Pandas, PyArrow, dbt, Airflow all native to Python."}
]
```

**Expected output:**

```json
{
  "conflict_type": "value_based",
  "conflict_description": "Performance specialist optimizes for runtime speed; ecosystem specialist optimizes for library / tooling availability — both defensible priorities.",
  "reconciliation_strategy": "Preserve disagreement and present trade-off; defer final choice to a stakeholder who knows team's priorities.",
  "reconciled_output": "Two recommendations with explicit trade-offs: (1) Rust if runtime performance is the binding constraint and team is willing to build wrappers around data-engineering tools; (2) Python if leveraging existing data-engineering ecosystem (pandas, Airflow, dbt) is more important than 2-5x speed. Likely answer for typical data-engineering teams: Python; for high-throughput streaming: Rust.",
  "agent_decisions": [
    {"agent_name": "performance_specialist", "decision": "kept", "reason": "Performance argument is valid; preserved as one option."},
    {"agent_name": "ecosystem_specialist", "decision": "kept", "reason": "Ecosystem argument is valid; preserved as the other option."}
  ],
  "escalate_to_human": true,
  "escalation_reason": "Decision depends on team priorities (runtime performance vs ecosystem leverage) which are outside the agents' info.",
  "decision_basis": "Value-based conflict; both recommendations defensible; escalating for human priority decision."
}
```

## Failure Modes

- **Forced winner on value-based conflicts** — model picks one agent
  even when both are defensible. Track conflict_type distribution;
  if "value_based" rate is much lower than "factual", model is
  collapsing them.
- **Hidden agent dropping** — model silently ignores one agent's
  output. The agent_decisions field is the safety net; verify
  every input agent has an entry.
- **Escalation under-trigger** — model commits to an answer when
  human input is genuinely needed. Sample committed decisions and
  check whether the trade-off actually depends on info the agents
  don't have.
- **Generic merge for scope conflicts** — model just concatenates
  outputs instead of meaningfully merging. Audit reconciled_output
  on scope-type conflicts.
- **Methodological without explanation** — picks a method as
  "appropriate" without saying why. Reject methodological outputs
  with empty reason fields.

## Tuning Notes

- 模型差异：本卡需要稳定的 conflict-type 分类 + 适当 reconciliation
  策略选择。frontier 模型必须的；中档模型容易把所有冲突当 factual
  处理。
- 温度：`0.0`–`0.2`。
- 与 `agent/sub-task-delegator` 的关系：那张卡 fan-out 派任务；本卡
  fan-in 合并冲突。完整 multi-agent 编排的两端。
- 与 `agent/self-critique-reflection` 的关系：reflection 是单 agent
  对自己 trajectory 反思；本卡是跨 agent 间的协调。两者都是 agent
  loop 中的 "meta" 层。
- escalate_to_human 的下游：触发人工 review queue；典型 SLA 几小时。
  生产中应当有"escalate 后默认走 X 兜底逻辑"以避免 hang。
- value_based 冲突在 LLM 应用中常见——preserving disagreement 比
  forcing winner 通常更有用，让用户自己判断。

## Changelog

- `0.1.0` — Initial card.
