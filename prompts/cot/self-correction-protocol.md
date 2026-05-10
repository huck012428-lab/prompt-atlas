---
id: cot/self-correction-protocol
title: Self-Correction Protocol (accept / correct / reject)
version: 0.1.0
status: stable
direction: cot
tags: [self-check, structured-reasoning, structured-output, classification]
audience: [prompt-engineer, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: original_question
    description: The original question.
    required: true
  - name: candidate_answer
    description: A candidate answer to evaluate.
    required: true
  - name: criticism
    description: External criticism of the candidate answer (could be from another model, a rule-based check, or a human reviewer).
    required: true
---

> 🎯 **场景**：拿到一个候选答案 + 外部 criticism，决定是 accept、correct（部分采纳）还是 reject（重新做）。结构化的 self-correction 流程比无脑接受 criticism 或顽固坚持原答案都好。critique-and-revise / RLHF 反馈循环常用。

## Quick Use

**Use when:** You have a candidate answer and external criticism (from another model, a human reviewer, or a rule check) and need to decide whether to accept, correct, or reject the candidate.
**Fill in:** `{{original_question}}` = the question; `{{candidate_answer}}` = candidate; `{{criticism}}` = the external criticism.
**You'll get:** Decision (accept / correct / reject), assessment of which criticism points are valid, and the corrected answer if applicable. Output is JSON.

## Purpose

Process external criticism of a candidate answer with structured
judgment: which criticism points are valid, which aren't, and what
the resolution should be. Used in critique-and-revise loops, RLHF
feedback processing, and human-in-the-loop systems where reviewers
flag issues. Distinct from `cot/verify-then-finalize` which checks
its own answer; this card processes EXTERNAL criticism.

## Prompt

```text
You evaluate external criticism of a candidate answer and decide
how to respond.

Original question:
{{original_question}}

Candidate answer:
{{candidate_answer}}

Criticism (from external source):
{{criticism}}

Steps:
1. Parse the criticism into individual points (one criticism may
   raise multiple issues).

2. For each point, classify:
   - "valid"          : The point is correct; the candidate has
                         this issue.
   - "valid_but_minor": The point is correct but the issue is
                         small / cosmetic.
   - "invalid"        : The point is wrong; the candidate doesn't
                         have this issue OR it's not actually an
                         issue.
   - "ambiguous"      : Could go either way; reasonable people may
                         disagree.

3. Decide overall action:
   - "accept" : All criticism is invalid OR only valid_but_minor.
                Original candidate stands.
   - "correct": At least one valid criticism with substantive
                impact. Produce a revised answer.
   - "reject" : Multiple valid criticisms or one fundamental error.
                Original answer is too broken to patch; restart.

4. If "correct", produce the corrected answer that addresses the
   valid criticism without overcorrecting.

Return ONLY this JSON object:
{
  "criticism_points": [
    {"point": "<short>", "verdict": "valid" | "valid_but_minor" | "invalid" | "ambiguous", "rationale": "<short>"}
  ],
  "action": "accept" | "correct" | "reject",
  "final_answer": "<accepted candidate, OR corrected answer, OR brief note for reject>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
original_question: "What is the capital of Australia?"
candidate_answer: "Sydney is the capital of Australia."
criticism: "This is wrong. The capital of Australia is Canberra, not Sydney. Sydney is the largest city but not the capital."
```

**Expected output:**

```json
{
  "criticism_points": [
    {"point": "Capital is Canberra, not Sydney.", "verdict": "valid", "rationale": "Factually correct — Canberra is the capital."},
    {"point": "Sydney is the largest city.", "verdict": "valid", "rationale": "Factually correct context."}
  ],
  "action": "correct",
  "final_answer": "Canberra is the capital of Australia. Sydney is Australia's largest city, but not its capital.",
  "decision_basis": "Criticism is fully valid; corrected the factual error and incorporated the clarifying context."
}
```

## Failure Modes

- **Sycophantic accept** — model accepts criticism even when invalid
  ("you're right, sorry"). The valid/invalid classification should
  enable refusing bad criticism; track invalid_count distribution.
- **Stubborn rejection** — model marks all criticism invalid to
  preserve original answer. Sample.
- **Over-correction** — model corrects valid_but_minor issues that
  didn't need changing, drifting away from a fine answer. Track
  ratio of action=correct / valid_but_minor count.
- **Missed criticism point** — multi-point criticism collapsed to
  one classification. Check criticism_points list captures all
  raised issues.
- **Ambiguous abuse** — model labels everything ambiguous to dodge.
  Track ambiguous rate.

## Tuning Notes

- 模型差异：本卡需要平衡的判断 (不轻信也不顽固). frontier 模型更稳;
  中档模型容易 sycophancy 接受所有 criticism.
- 温度：`0.0`–`0.2`.
- 与 `cot/verify-then-finalize` 的关系：那张卡 self-verify 自己的答案;
  本卡处理 external criticism. 前者 self-driven, 后者 external-driven.
- 与 `rlhf/constitutional-critique-revise` 的关系：那张卡按 constitution
  自批 + 重写, 是单次端到端; 本卡接受任意来源 criticism. 后者更通用.
- 与 `cot/plan-critique-and-revise` 的关系：那张卡 critique plan; 本卡
  process critique on answer. 不同对象.
- production 用法: human-in-the-loop 系统中, reviewer 写 criticism →
  本卡决定 accept/correct/reject → 自动化处理 vs 升级到 reviewer round 2.
- accept-rate calibration: 健康系统中, 训练好的模型 + 严格 reviewer
  → accept rate 50-70% 是合理范围. 太高 = reviewer 太宽松 OR 模型
  顽固; 太低 = 模型太弱 OR reviewer 太严.

## Changelog

- `0.1.0` — Initial card.
