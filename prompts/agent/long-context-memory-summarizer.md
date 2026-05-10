---
id: agent/long-context-memory-summarizer
title: Long-Context Trajectory Memory Summarizer
version: 0.1.0
status: stable
direction: agent
tags: [memory, generation, structured-output, decomposition]
audience: [prompt-engineer, app-builder, llm-trainer]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: trajectory_so_far
    description: The full trajectory so far — actions, observations, intermediate results — as a JSON array.
    required: true
  - name: current_objective
    description: The agent's current objective (may be the original user goal, or a refined sub-goal).
    required: true
  - name: token_budget_for_summary
    description: Approximate target token budget for the produced summary (an integer hint, e.g. 500).
    required: true
---

## Quick Use

**Use when:** Your agent's trajectory is approaching the context window limit and you need to compress earlier history into a structured memory record.
**Fill in:** `{{trajectory_so_far}}` = JSON array of all actions and observations; `{{current_objective}}` = the current goal; `{{token_budget_for_summary}}` = target summary size, e.g. 500.
**You'll get:** Structured memory with facts learned, decisions made, open questions, dead ends, and a non-binding next-action hint. Output is JSON.

## Purpose

Compress a long agent trajectory into a structured memory record that
preserves the facts, decisions, and unresolved questions needed to keep
making progress toward `current_objective` — without keeping the raw
action / observation history in context. Used in long-running agents
that approach context-window limits, in async agents that wake up later
and need to resume, and in multi-agent setups where a supervisor needs
a digest. Output is structured so it can be re-loaded as the agent's
"memory" prefix on the next turn.

## Prompt

```text
You compress an agent's trajectory into a structured memory record.
Goal: keep enough information that the agent can resume working toward
its objective without re-reading the full trajectory.

Current objective:
{{current_objective}}

Trajectory so far:
{{trajectory_so_far}}

Approximate token budget for the produced summary:
{{token_budget_for_summary}}

Rules:
1. Preserve concrete facts learned from observations (numbers, names,
   dates, citations). These are why the trajectory existed.
2. Preserve decisions made — and WHY — so the agent does not re-litigate
   them.
3. Preserve unresolved questions and dead ends. The agent should not
   re-walk paths it already ruled out.
4. Drop verbatim tool outputs, formatting noise, and redundant
   restatements.
5. Aim for the token budget; going slightly over is acceptable to
   preserve a critical fact, going far over defeats the purpose.

Return ONLY this JSON object:
{
  "objective_state": "<one short paragraph: where we are relative to the objective>",
  "facts_learned": [
    {"text": "<concrete fact>", "source_step": "<step id or short reference, or empty if not traceable>"}
    /* facts the agent should treat as established */
  ],
  "decisions_made": [
    {"decision": "<what was decided>", "reason": "<one short phrase>"}
    /* explicit choices made during the trajectory */
  ],
  "open_questions": ["<one per question still blocking progress>"],
  "dead_ends": ["<short description: what was tried and why it didn't work>"],
  "next_action_hint": "<one sentence suggesting the next reasonable action; not binding on the agent>"
}
```

## Example

**Input:**

```text
current_objective: "Determine when SpaceX's Starship made its first successful orbital flight."
trajectory_so_far: [
  {"step": "s1", "action": "search('Starship orbital flight history')", "observation": "Starship had multiple test flights including IFT-1 (April 2023, exploded), IFT-2 (Nov 2023, lost upper stage), IFT-3 (March 2024, partially successful)..."},
  {"step": "s2", "action": "search('IFT-3 Starship orbital classification')", "observation": "IFT-3 reached space and tested in-orbit operations but did not complete a full orbit; SpaceX described it as 'transatmospheric'."},
  {"step": "s3", "action": "search('Starship first full orbital flight')", "observation": "As of mid-2024, no flight had completed a full Earth orbit; later flights focused on reentry and booster recovery."},
  {"step": "s4", "action": "search('Starship 2025 orbital'), observation": "Reports vary; need a primary source to confirm."}
]
token_budget_for_summary: 400
```

**Expected output:**

```json
{
  "objective_state": "We are tracing whether and when Starship completed a full orbital flight. Up to mid-2024 no flight reached full orbit; 2025 status needs a primary source.",
  "facts_learned": [
    {"text": "IFT-1 (April 2023) ended in vehicle loss before orbit.", "source_step": "s1"},
    {"text": "IFT-2 (Nov 2023) lost the upper stage.", "source_step": "s1"},
    {"text": "IFT-3 (March 2024) reached space but did not complete a full orbit; classified as transatmospheric.", "source_step": "s2"},
    {"text": "As of mid-2024, no Starship flight had completed a full Earth orbit.", "source_step": "s3"}
  ],
  "decisions_made": [
    {"decision": "Treat 'orbital' strictly as completing one full Earth orbit, not 'reached space'.", "reason": "IFT-3 reached space but is not counted as orbital."}
  ],
  "open_questions": ["Did any 2025 Starship flight complete a full orbit? Primary source needed."],
  "dead_ends": ["General 'Starship orbital flight history' search returns marketing summaries — too vague to confirm an orbital completion."],
  "next_action_hint": "Search a primary source (SpaceX official blog, NASA, or Wikipedia revision history) for 2025 Starship orbital results."
}
```

## Failure Modes

- **Recency bias** — summary preserves the last 1-2 steps in detail and
  drops earlier facts that are still relevant. Detect by spot-checking
  whether `facts_learned` contains items from across the trajectory,
  not just the tail.
- **Hallucinated facts** — summary asserts something the trajectory did
  not actually establish. Mitigation: each `facts_learned` item has a
  `source_step` field; verify in audits that the source exists and
  supports the fact.
- **Decision laundering** — model retroactively assigns "decisions" the
  agent never made (e.g. invents a "we decided to focus on X"). Detect
  by sampling and checking decisions against the trajectory.
- **Summary bloat** — output approaches the trajectory length itself,
  defeating the compression purpose. Enforce the token budget at parse
  time; if 2x over, re-prompt with a tighter cap.
- **Stale dead ends** — `dead_ends` lists paths that are no longer dead
  (e.g. they failed because of a transient tool error, not because the
  approach was wrong). Mitigation: only include dead ends that the
  trajectory explicitly concluded as wrong, not just paths that
  failed once.
- **Over-confident `next_action_hint`** — hint is treated as binding by
  the executor, ossifying the strategy. The card explicitly says it is
  not binding; the executor / reflection step decides.

## Tuning Notes

- 调用频率：在上下文窗口达到 ~70% 容量时触发，或在每 N 步（典型 N=10）
  触发一次。每步触发会浪费 token 且产生信息抖动。
- 模型差异：summary quality 与 long-context 处理能力强相关；frontier
  模型对长 trajectory 更稳定。中档模型在 trajectory > 30k tokens 时
  容易丢早期事实——这种情况下先做分块 summary，再做 summary-of-summaries。
- 温度：`0.0`–`0.2`。Summary 的稳定性比创造性重要。
- 与 `agent/self-critique-reflection` 的关系：reflection 是策略层的
  反思（"是否在轨道上"）；本卡是状态层的压缩（"目前知道什么"）。
  典型组合：每 N 步先压缩 memory，再做一次 reflection，再继续 plan/
  execute。
- 与 `agent/plan-and-execute-planner` 的关系：长任务的 plan 一旦
  执行到中段，原 plan 可能基于过时假设。压缩后 memory 是 re-plan 的
  良好输入。
- 信息忠实度审计：上线前用 50 个真实 trajectory 跑一遍，把
  facts_learned 和 trajectory 对比，错误率应 <5%；高于此应换更强
  的 summarizer 模型或改 prompt。

## Changelog

- `0.1.0` — Initial card.
