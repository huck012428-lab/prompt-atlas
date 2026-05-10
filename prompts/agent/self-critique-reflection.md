---
id: agent/self-critique-reflection
title: Self-Critique Reflection Step for Agents
version: 0.1.0
status: stable
direction: agent
tags: [reflection, self-check, planning, structured-output]
audience: [prompt-engineer, app-builder, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: original_goal
    description: The user's original goal for this agent session.
    required: true
  - name: recent_actions
    description: Recent actions the agent has taken (tool calls, decisions), as a JSON array.
    required: true
  - name: recent_observations
    description: Observations / tool results received in response to the recent actions.
    required: true
---

## Purpose

Insert a structured reflection step into an agent loop after every N
actions or after a tool failure. The agent steps back, evaluates whether
recent actions are moving toward the goal, names what is and isn't
working, and decides one of: continue current strategy, switch strategy,
or escalate (ask the user / give up). Used to break out of stuck loops,
catch silent drift from the original goal, and produce auditable
decision points in long-running trajectories.

## Prompt

```text
You are reflecting on an agent's recent progress toward a user goal.
Step back from the immediate next action and evaluate the trajectory.

Original goal:
{{original_goal}}

Recent actions:
{{recent_actions}}

Recent observations:
{{recent_observations}}

Produce a structured reflection. For each section, be concrete — name
specific actions and observations, do not write generic platitudes.

Return ONLY this JSON object:
{
  "progress_assessment": {
    "on_track": true | false,
    "evidence": "<one specific action or observation that supports the assessment, <=30 words>"
  },
  "what_worked": "<concrete: which action(s) produced useful information, or empty string if none>",
  "what_failed": "<concrete: which action(s) wasted budget or produced no signal, or empty string if none>",
  "drift_check": {
    "drifted": true | false,
    "drift_description": "<if drifted: how the recent actions diverged from the original goal, <=40 words; else empty>"
  },
  "next_strategy": "continue" | "switch_strategy" | "escalate",
  "strategy_reason": "<one sentence, <=30 words, justifying next_strategy; not internal CoT>",
  "switch_proposal": "<if next_strategy=switch_strategy: a one-sentence description of the new approach; else empty string>"
}

Rules:
- "continue"        — current strategy is working; the next action of
                      the same kind is the right move.
- "switch_strategy" — current strategy is not working; describe a
                      DIFFERENT approach in `switch_proposal`. Do not
                      switch on the basis of a single failed call —
                      that is a tool-call repair issue, not a strategy
                      issue.
- "escalate"        — neither continuing nor switching is likely to
                      succeed (the goal needs information you cannot
                      obtain, or the user must clarify ambiguity).
```

## Example

**Input:**

```text
original_goal: "Find the population of Reykjavik and compute its share of Iceland's population."
recent_actions: [
  {"step": 1, "tool": "search", "args": {"query": "Reykjavik history"}},
  {"step": 2, "tool": "search", "args": {"query": "famous landmarks in Reykjavik"}},
  {"step": 3, "tool": "search", "args": {"query": "Reykjavik nightlife guide"}}
]
recent_observations: [
  {"step": 1, "result": "Reykjavik was founded in 874 CE..."},
  {"step": 2, "result": "Hallgrimskirkja is a notable landmark..."},
  {"step": 3, "result": "Top bars in Reykjavik include..."}
]
```

**Expected output:**

```json
{
  "progress_assessment": {
    "on_track": false,
    "evidence": "Three searches done; none returned population numbers for Reykjavik or Iceland."
  },
  "what_worked": "",
  "what_failed": "All three searches were thematic queries that retrieved tourism content instead of demographic data.",
  "drift_check": {
    "drifted": true,
    "drift_description": "The agent moved into Reykjavik tourism topics instead of pursuing the population numbers needed for the share computation."
  },
  "next_strategy": "switch_strategy",
  "strategy_reason": "Need to query specifically for population statistics rather than general topics about the city.",
  "switch_proposal": "Issue targeted queries like 'Reykjavik population 2024' and 'Iceland total population 2024', then compute the share."
}
```

## Failure Modes

- **Vacuous reflection** — model writes "the agent should consider its
  approach" with no specific reference to actions or observations.
  Mitigation: the prompt's "name specific actions" rule; reject
  reflections with empty or generic `evidence` fields.
- **Confirmation bias toward `continue`** — model defaults to "continue"
  even when the trajectory is clearly stuck, because admitting failure
  feels like criticism. Mitigation: track the rate of `switch_strategy`
  decisions; if <10% across stuck-trajectory test cases, the prompt
  is too forgiving — sharpen the failure framing.
- **Premature `switch_strategy`** — model switches strategy after a
  single failed call. The rubric explicitly says don't; if violations
  persist, add a few-shot showing one tool failure → `continue`.
- **`escalate` over-trigger** — model escalates whenever a query is
  complex. Mitigation: reserve `escalate` for cases where neither
  continuation nor switching can succeed (information not obtainable,
  ambiguity in user goal). Track escalation rate; high rates mean
  the prompt is too eager to give up.
- **Context loss** — long `recent_actions` and `recent_observations`
  drown the goal. Mitigation: cap each to last N items; restate
  `original_goal` at the top of the prompt (already done).

## Tuning Notes

- 调用频率：每 N 步插入一次（典型 N=3–5），或在 tool 失败时立刻触发。
  每步都做反思会把 latency 翻倍且贡献边际信号。
- 模型差异：reflection 对 judgment quality 极敏感；frontier 模型显著
  优于中档模型。如果只能用中档模型，把决策从 3 档（continue / switch /
  escalate）降为 2 档（continue / replan）以提升一致性。
- 温度：`0.0`–`0.3`。
- 与 `agent/react-planner-with-tool-schema` 的关系：react-planner 是
  每步行动；本卡是周期性的元层反思。两者配合：planner 输出
  reasoning_summary（局部），reflection 输出 progress_assessment
  （全局）。
- 与 `agent/tool-call-repair` 的关系：tool-call-repair 处理"调用语法
  错误"层面的失败；本卡处理"策略不对"层面的失败。一次 tool-call 失败
  先用 tool-call-repair；连续失败或 silent 失败用本卡反思。
- 用作训练数据：reflection 输出可以收集为"什么是好的策略反思"的偏好
  数据，反向训练 agent 的 meta-reasoning 能力。

## Changelog

- `0.1.0` — Initial card.
