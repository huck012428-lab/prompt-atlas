---
id: agent/budget-aware-planner
title: Budget-Aware Agent Planner
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
  - name: user_goal
    description: The user's goal.
    required: true
  - name: tool_catalog
    description: JSON list of tools, each with name + estimated_cost (per-call cost in tokens or USD).
    required: true
  - name: budget
    description: A budget object with `tokens` (max total token cost) and/or `usd` (max dollar cost). At least one must be present.
    required: true
---

> 🎯 **场景**：在 token / 美元预算约束下规划 agent 任务——不是无限制 plan-and-execute，而是"在 X 预算内尽量完成任务"。会自动剪掉昂贵但低收益的 step、按 cost-per-information 排序、必要时主动 escalate。适合产品级 agent + cost-sensitive 部署。

## Quick Use

**Use when:** You're running an agent under explicit token or dollar budget and need a plan that completes the goal within budget — not a maximalist plan that overshoots.
**Fill in:** `{{user_goal}}` = the goal; `{{tool_catalog}}` = JSON tools each with estimated_cost; `{{budget}}` = budget object.
**You'll get:** A budget-aware plan with per-step cost estimates, total estimated cost, and (if needed) cost-cutting trade-offs you should know about. Output is JSON.

## Purpose

Plan agent execution within a hard budget. Input includes per-tool
costs and a total budget; output is a plan whose summed costs fit.
When the obvious "best" plan exceeds budget, the card identifies
trade-offs (drop a verification step, use a cheaper tool, accept
lower confidence) and reports them honestly. Used for cost-sensitive
production agents where infinite-budget plans aren't an option.

## Prompt

```text
You produce a plan that fits within a budget.

User goal:
{{user_goal}}

Tool catalog (each tool has estimated_cost):
{{tool_catalog}}

Budget (at least one of tokens / usd):
{{budget}}

Steps:
1. Produce an initial maximalist plan ignoring budget. Compute its
   estimated_cost.
2. If maximalist plan fits in budget, return it as the final plan.
3. If it overshoots, iteratively:
   - Identify the most expensive step.
   - Decide: drop (skip a verification / redundant step), substitute
     (use a cheaper tool), or compress (combine multiple tool calls
     into one).
   - Repeat until plan fits, OR until further cuts would harm goal
     completion.
4. If even the cheapest plan can't reach the goal within budget, set
   "fits_budget": false and explain.

For each step provide: tool, brief description, estimated_cost,
why_kept (or why_dropped if cut from maximalist).

Return ONLY this JSON object:
{
  "fits_budget": true | false,
  "infeasibility_reason": "<if fits_budget=false: why; else empty>",
  "plan": [
    {
      "step_id": "s1",
      "tool": "<tool name>",
      "description": "<short>",
      "estimated_cost": "<cost number with unit>",
      "depends_on": []
    }
  ],
  "tradeoffs_made": [
    {"trade_off": "<short>", "what_dropped": "<short>", "what_kept": "<short>", "impact": "low" | "medium" | "high"}
  ],
  "estimated_total_cost": "<sum>",
  "budget_remaining": "<difference>",
  "confidence_in_completion": "high" | "medium" | "low",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
user_goal: "Find the population of Reykjavik and write a 50-word summary."
tool_catalog: [
  {"name": "search", "estimated_cost": "1000 tokens"},
  {"name": "verify_against_official", "estimated_cost": "3000 tokens"},
  {"name": "summarize", "estimated_cost": "500 tokens"}
]
budget: {"tokens": 2000}
```

**Expected output:**

```json
{
  "fits_budget": true,
  "infeasibility_reason": "",
  "plan": [
    {"step_id": "s1", "tool": "search", "description": "Search for Reykjavik population.", "estimated_cost": "1000 tokens", "depends_on": []},
    {"step_id": "s2", "tool": "summarize", "description": "Compose 50-word summary using search result.", "estimated_cost": "500 tokens", "depends_on": ["s1"]}
  ],
  "tradeoffs_made": [
    {"trade_off": "Skipped verify_against_official", "what_dropped": "Cross-check against authoritative source (would catch out-of-date results)", "what_kept": "First-pass search + summary", "impact": "medium"}
  ],
  "estimated_total_cost": "1500 tokens",
  "budget_remaining": "500 tokens",
  "confidence_in_completion": "medium",
  "decision_basis": "Maximalist plan was 4500 tokens (search + verify + summarize); skipping verify hits budget at cost of medium-impact accuracy reduction."
}
```

## Failure Modes

- **Trade-off invisibility** — model cuts steps without surfacing
  what was lost. The `tradeoffs_made` field is non-optional when
  cuts happened; verify it's populated.
- **Budget bypass** — plan summed cost exceeds budget despite
  fits_budget=true. Validate sum at parse time.
- **Quality false-confidence** — confidence "high" after dropping
  every verification step. Tie confidence rating to what was kept;
  if verification dropped, max confidence is "medium".
- **Cheapest-tool over-substitution** — substitutes everywhere even
  when cheap tool can't actually fulfill the step. Check
  substitutions are valid for the step's purpose.
- **Inadmissible drops** — drops a step the goal can't be reached
  without (e.g. drops the search step). The fits_budget=false path
  exists for this; verify it triggers when cuts harm goal.

## Tuning Notes

- 模型差异：本卡需要同时做 cost arithmetic + 价值取舍判断。frontier
  模型在 trade-off honesty 上更稳；中档模型容易"为了 fit budget 强行
  返 fits_budget=true"。
- 温度：`0.0`–`0.2`。
- 与 `agent/plan-and-execute-planner` 的关系：那张卡是无 budget 约束
  规划；本卡是带 budget 约束。budget tight 时用本卡，宽松时用那张。
- 与 `agent/sub-task-delegator` 的关系：本卡按 cost 优化 plan；sub-
  task-delegator 按 capability 派 plan。两者可叠加：sub-task 先派给
  worker，再用本卡为每个 worker 的子目标做 budget-aware planning。
- budget 单位选择：tokens 适合知道 token 价格的场景；usd 适合多模型
  混合调用（每模型 token 价不同）。两者可同时给，模型按 binding
  约束规划。
- estimated_total_cost 是 hint：实际 cost 受 tool 输出长度、retry 次数、
  上下文累积影响。生产中 add 1.3-1.5x buffer。
- 与计费 / 限流系统的接口：本卡产出的 plan 应当被 executor 在每步前
  check 实际 budget remaining；预估和实际有偏差时按真实数据 abort。

## Changelog

- `0.1.0` — Initial card.
