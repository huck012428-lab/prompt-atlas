---
id: agent/error-recovery-strategy
title: Error Recovery Strategy (retry / abort / escalate)
version: 0.1.0
status: stable
direction: agent
tags: [reflection, planning, structured-output]
audience: [prompt-engineer, app-builder, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: agent_goal
    description: The agent's overall goal.
    required: true
  - name: failed_operation
    description: A short description of the operation that just failed (e.g. "search('Reykjavik population')", "POST /orders with cart_id=123").
    required: true
  - name: error_message
    description: The actual error message returned by the system.
    required: true
  - name: retry_history
    description: A JSON array of prior attempts at the same kind of operation in this session, with their outcomes (success | timeout | error). Empty array if first attempt.
    required: true
---

> 🎯 **场景**：agent 操作失败时——是 retry 还是 abort 还是 escalate？根据错误类型 + 历史尝试 + 目标重要性给决策。避免无脑重试浪费预算，也避免一次失败就放弃。

## Quick Use

**Use when:** An agent operation just failed (tool call, API call, database query) and you need to decide whether to retry, abort the goal, or escalate to a human.
**Fill in:** `{{agent_goal}}` = overall goal; `{{failed_operation}}` = what just failed; `{{error_message}}` = actual error text; `{{retry_history}}` = JSON array of prior attempts.
**You'll get:** A decision (retry / retry_with_modification / abort / escalate) with strategy details and a backoff suggestion. Output is JSON.

## Purpose

Decide the next move when an agent operation fails. Combines three
signals: (1) **error class** — transient (rate limit, timeout) vs
permanent (404, validation, auth); (2) **history** — has the same
operation kind failed N times already?; (3) **goal-criticality** —
is this failure on a sub-step that has alternatives, or on a
critical path? Output is structured so the agent's executor can
immediately act on the decision.

## Prompt

```text
You decide what an agent should do after an operation fails.

Agent goal:
{{agent_goal}}

Failed operation:
{{failed_operation}}

Error message:
{{error_message}}

Retry history for this operation kind:
{{retry_history}}

Steps:
1. Classify the error:
   - "transient"   : Likely succeeds on retry (rate limit, timeout,
                     5xx, network error).
   - "validation"  : Bad input — needs modification before retry
                     (4xx with validation message).
   - "permanent"   : Won't succeed regardless of retry (404, 401,
                     unsupported endpoint).
   - "ambiguous"   : Error message doesn't clearly indicate which
                     class. Lean conservative.

2. Decide:
   - "retry"                — same operation, same parameters.
                              Only for transient errors with low
                              retry_history count (<3).
   - "retry_with_modification"
                              — same operation, modified parameters.
                              For validation errors OR transient
                              errors after 1-2 plain retries failed.
   - "abort"                — give up on this operation; the agent
                              continues toward goal via different
                              path. For permanent errors when an
                              alternative exists.
   - "escalate"             — this failure blocks the goal; surface
                              to a human or fallback channel. For
                              permanent errors with no alternative,
                              OR transient errors after 3+ retries.

3. Provide retry_delay_seconds for retry / retry_with_modification.
   Use exponential backoff: 1s, 4s, 16s for retries 1, 2, 3.

Return ONLY this JSON object:
{
  "error_class": "transient" | "validation" | "permanent" | "ambiguous",
  "decision": "retry" | "retry_with_modification" | "abort" | "escalate",
  "decision_reason": "<one sentence>",
  "retry_delay_seconds": <integer; 0 if not retrying>,
  "modification_suggestion": "<for retry_with_modification: what to change; else empty>",
  "escalation_summary": "<for escalate: short message for the human, including what was tried>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
agent_goal: "Find the population of Reykjavik."
failed_operation: "search(query='Reykjavik popultion 2024')"
error_message: "No results found for query."
retry_history: []
```

**Expected output:**

```json
{
  "error_class": "permanent",
  "decision": "retry_with_modification",
  "decision_reason": "Empty results likely caused by typo 'popultion' instead of 'population'; modifying the query is the right next step.",
  "retry_delay_seconds": 0,
  "modification_suggestion": "Fix typo: change 'popultion' to 'population'. New query: 'Reykjavik population 2024'.",
  "escalation_summary": "",
  "decision_basis": "First attempt; typo is detectable; cheap to retry with fix."
}
```

## Failure Modes

- **Naive infinite retry** — model decides retry on every transient
  error regardless of history. The 3-attempt cap should bind;
  verify by sampling outputs where retry_history has 3+ failures
  and confirming decision shifts to escalate.
- **Permanent errors as transient** — 404 marked transient, leading
  to wasted retries. Sample classification distribution; permanent
  errors should NOT be classified transient.
- **Validation errors as permanent** — model gives up on a 400 that's
  just a fixable input issue. retry_with_modification should fire on
  validation errors with a clear modification path.
- **Ambiguous abuse** — model uses "ambiguous" to dodge the
  classification call. Track ambiguous rate; high rate means the
  prompt needs more discriminating language.
- **Escalation under-trigger** — model prefers retry/abort to
  escalate even when human input is the only way forward. Reflect
  this in the rubric: "no alternative path" → escalate.
- **Backoff math wrong** — `retry_delay_seconds` doesn't follow
  exponential pattern. Validate at parse time.

## Tuning Notes

- 模型差异：本卡对 error message 的细微解读要求高。frontier 模型在
  validation vs permanent 区分上明显更稳。中档模型常把"语义错误"
  （typo 类）误标为 permanent。
- 温度：`0.0`，决策必须可重现。
- 与 `agent/tool-call-repair` 的关系：tool-call-repair 修**单次调用
  的语法**（schema 错），本卡决定**是否重试以及怎么重试**。两者
  协同：先 tool-call-repair → 修好的 call 再失败 → 本卡决定下一步。
- 与 `agent/self-critique-reflection` 的关系：reflection 处理"策略
  层"失败（多次错都解决不了 → 反思整个 trajectory）；本卡处理
  "操作层"失败（单次操作的下一步）。一次失败先用本卡，连续 N 次
  用 reflection。
- retry_history 设计：建议传"同 operation kind 在本 session 的失败
  历史"，不是全部历史。避免历史过长让 prompt 失控。
- escalation_summary 用法：production 中应该 wire 到通知渠道（Slack
  alert / oncall page）。escalation_summary 是给人看的，不是给 agent
  看的。
- 高敏操作（DELETE / 写库 / 支付）：建议默认禁止本卡返回 retry，
  改为 retry_with_modification 或 escalate。误重试写操作可能产生
  duplicate state。
- 用作训练数据：(failed_operation, error, history, decision) 四元组
  可作 reward model 的负样本来源——"naive retry on permanent error"
  是一类清晰的 wrong 决策。

## Changelog

- `0.1.0` — Initial card.
