---
id: agent/clarification-asker
title: Clarification Question Asker
version: 0.1.0
status: stable
direction: agent
tags: [planning, classification, structured-output]
audience: [prompt-engineer, app-builder, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: user_goal
    description: The user's stated goal as received.
    required: true
  - name: available_capabilities
    description: One or two sentences describing what the agent / system can actually do (so the clarifying question stays in-scope).
    required: true
---

> 🎯 **场景**：agent / 助手收到模糊任务时，先判断"该不该问澄清问题"——能直接做就做，不能直接做才问，**只问一个**最有价值的问题。避免无意义重复对话也避免误解任务跑偏。

## Quick Use

**Use when:** Your agent receives an ambiguous goal and you need it to decide whether to proceed, ask one good clarifying question, or refuse.
**Fill in:** `{{user_goal}}` = the user's stated goal; `{{available_capabilities}}` = brief description of what the system can actually do.
**You'll get:** A decision (proceed / clarify / out_of_scope), and if clarifying, exactly ONE question with the ambiguity it resolves. Output is JSON.

## Purpose

Decide whether a user goal needs clarification before acting, and if
yes, produce exactly ONE high-value clarifying question. Used as the
front-door of agent loops to avoid two failure modes: (1) charging
ahead on an ambiguous goal and producing the wrong thing, and
(2) interrogating the user with multiple clarifying questions when
one would suffice. Output is structured so the agent's executor can
branch on the decision without re-parsing.

## Prompt

```text
You decide whether a user goal needs clarification before an agent
acts on it. If yes, produce exactly ONE high-value clarifying
question. If no, signal "proceed".

User goal:
{{user_goal}}

Available capabilities (what the system can actually do):
{{available_capabilities}}

Decision criteria:
1. The goal can be acted on as-is when its missing details have
   reasonable defaults OR when guessing would produce a useful
   first attempt the user can correct.
2. The goal needs clarification when (a) the same words could mean
   genuinely different work and the wrong choice wastes a lot, OR
   (b) a missing identifier / target / scope makes the work
   impossible.
3. The goal is out of scope when the available_capabilities cannot
   serve it. In that case, return decision=out_of_scope rather than
   asking the user a question that won't help.

If asking a question:
- Ask EXACTLY ONE question. Do not chain "and also..." onto it.
- The question must resolve a SPECIFIC ambiguity, not be a generic
  "could you clarify what you mean?".
- Prefer a closed-form question (yes/no, choose one of A/B/C) over
  open-ended when the ambiguity is enumerable.
- Do not phrase the question with hedges that suggest the user did
  something wrong ("you didn't tell me X").

Return ONLY this JSON object:
{
  "decision": "proceed" | "clarify" | "out_of_scope",
  "ambiguity_type": "<empty if proceed; else one of: 'scope', 'target_identifier', 'output_format', 'success_criteria', 'method_choice', 'time_window', 'other'>",
  "ambiguity_description": "<empty if proceed; else one short sentence describing the specific ambiguity>",
  "clarifying_question": "<empty if not clarify; else exactly one question, closed-form when possible>",
  "out_of_scope_reason": "<empty unless decision=out_of_scope; else explain what capability is missing>",
  "default_assumption": "<if decision=proceed: a one-sentence statement of what assumption the agent will use, so the user can correct if wrong>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
user_goal: "Send the report to the team."
available_capabilities: "I can send emails to the user's contacts and post messages in connected Slack workspaces."
```

**Expected output:**

```json
{
  "decision": "clarify",
  "ambiguity_type": "target_identifier",
  "ambiguity_description": "Two ambiguities tie together: 'the report' could be any of several recent files, and 'the team' could be a Slack channel or an email distribution list.",
  "clarifying_question": "Which report should I send (most recent 'Q3 sales' or 'product launch')? And to which team — Slack #marketing or the marketing-leads@ email list?",
  "out_of_scope_reason": "",
  "default_assumption": "",
  "decision_basis": "Both the document and the recipient are ambiguous; sending the wrong combination is high-cost vs asking once."
}
```

(Note: this example violates the "exactly one question" rule by
asking two — included to show the failure mode. A correctly-following
output would pick the higher-value ambiguity to ask first, e.g.
"Which 'team' do you mean — Slack #marketing or the
marketing-leads@ email list?" and let the agent pick the most-recent
report by default once the team is known.)

## Failure Modes

- **Question chaining** — model asks 2-3 questions joined with "and",
  defeating the "one question at a time" UX. Validate at parse time
  that `clarifying_question` contains at most one "?". Re-prompt if
  multiple.
- **Generic clarification** — "could you provide more details?" is
  worthless. Reject any clarifying_question that is shorter than ~10
  words OR doesn't reference a specific noun from the user's goal.
- **Premature clarification** — agent asks for clarification when a
  reasonable default exists. Track the ratio of `clarify` vs
  `proceed`; if `clarify` rate is >50% on a benchmark of normal user
  goals, the agent is too cautious and the experience suffers.
- **Late proceed** — agent proceeds when ambiguity is genuinely
  blocking. Sample `proceed` outputs and check whether the
  default_assumption would actually be acceptable to a typical user;
  if not, the bar for clarification is too high.
- **Out-of-scope misfiled as clarify** — agent asks a clarifying
  question for a goal it fundamentally can't fulfill ("what
  date range should I tax-file for you?" when the system has no
  tax-filing capability). Verify available_capabilities is being
  consulted; if a clarify output's question, when answered, still
  wouldn't be actionable, the decision should have been
  out_of_scope.
- **Defensive phrasing** — "I cannot help unless you tell me..."
  feels accusatory. Sample clarifying_question values and reject
  ones that imply user fault.

## Tuning Notes

- 模型差异：本卡对模型的判断质量要求高；frontier 模型在
  proceed-vs-clarify 平衡上明显优于中档。中档模型常出现
  premature clarification（什么都问一遍）。
- 温度：`0.0`–`0.2`。判断稳定性优先。
- 与 `agent/react-planner-with-tool-schema` 的关系：本卡是 agent loop
  的"前门"——goal 进来先过本卡决定 proceed / clarify / out_of_scope。
  decision=proceed 时把 default_assumption 写入 react-planner 的
  scratchpad 起始上下文。
- 与 `agent/self-critique-reflection` 的关系：clarification 是开始时
  的判断；reflection 是中段的元反思。两者都让 agent 不闷头跑错方向。
- 与 `agent/sub-task-delegator` 的关系：复杂目标先用本卡确认无歧义，
  再用 delegator 分解。否则 delegator 会基于错误的 goal 拆出错误的
  sub-tasks。
- 一次问一个 vs 多次澄清：本卡只问一个。多轮澄清需要在 agent loop
  上层管理（每轮跑一次本卡，问一次，得到答案，再跑一次直到
  decision=proceed）。
- proceed 时记得用 default_assumption：让用户在第一次响应里就能
  看到"我假设了 X，错了请告诉我"——比让用户事后发现误解再纠正
  体验好得多。
- clarification 写作建议：closed-form 问题（yes/no、A/B/C）的转化率
  显著高于 open-ended。能闭合就闭合。

## Changelog

- `0.1.0` — Initial card.
