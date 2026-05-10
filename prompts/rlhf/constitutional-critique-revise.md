---
id: rlhf/constitutional-critique-revise
title: Constitutional Critique-and-Revise
version: 0.1.0
status: stable
direction: rlhf
tags: [harmlessness, helpfulness, honesty, generation, structured-output, self-check]
audience: [rlhf-team, llm-trainer, app-builder]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: user_prompt
    description: The original user prompt that elicited the response.
    required: true
  - name: original_response
    description: The model's first-draft response, to be critiqued and possibly revised.
    required: true
  - name: constitution
    description: A JSON list of constitutional principles, each as a one-line rule (e.g. "Do not provide instructions for harmful activities."). Pass an empty list to use a default short HHH set.
    required: true
---

## Quick Use

**Use when:** You want Constitutional AI training data (or to clean up a response at inference) by critiquing it against principles and revising.
**Fill in:** `{{user_prompt}}` = the prompt; `{{original_response}}` = the response to critique; `{{constitution}}` = JSON list of principle strings (or `[]` for the default HHH set).
**You'll get:** A list of violations, a revised response, an over_refusal_check guard, and a change summary. Output is JSON.

## Purpose

Produce a self-critique of an existing response against an explicit
constitution (a list of principles), then a revised response that
addresses the critique. Used to generate **constitutional AI training
data** (prompt → revised response pairs as SFT data, or critique pairs
as preference data) without requiring human labelers for every example.
Also usable at inference as a pre-output cleaning step. Output is
structured so the critique and the revision are distinct artifacts —
the critique is itself reusable as a labeling signal.

This is a defensive technique: the constitution describes what the
revised response should NOT do. Do not adapt this card to bypass
safety constitutions or to reverse-engineer harm-enabling content.

## Prompt

```text
You critique and revise a model response against a constitution. Output
both the critique and the revised response.

User prompt:
{{user_prompt}}

Original response:
{{original_response}}

Constitution (principles the response should obey):
{{constitution}}

If the constitution list is empty, use this default set:
- "Do not provide instructions or facilitation for clearly harmful or illegal activities."
- "Do not produce content that demeans or threatens individuals or protected groups."
- "Do not fabricate facts; acknowledge uncertainty when uncertain."
- "Be helpful and responsive to the user's actual question; do not over-refuse."

Steps:
1. Identify which principles, if any, the original response violates or
   skirts. For each violation, name the principle and quote the
   problematic phrase from the original response.
2. Produce a revised response that:
   - Addresses every identified violation.
   - Preserves the helpful intent of the original wherever possible.
   - Does NOT over-refuse: if the original was actually fine for a
     specific principle, do NOT remove substance under the guise of
     "being safe".
3. Summarize what changed and why.

Return ONLY this JSON object:
{
  "violations": [
    {"principle": "<verbatim principle from constitution>",
     "evidence": "<verbatim phrase from original_response>",
     "severity": "low" | "medium" | "high"}
    /* zero or more entries; empty array if no violations */
  ],
  "revised_response": "<the revised response text; identical to original_response if no violations>",
  "change_summary": "<one or two sentences describing what changed; empty string if no changes>",
  "over_refusal_check": {
    "would_refuse_unnecessarily": true | false,
    "note": "<if true, what substantive content the revision dropped that should have been kept; else empty>"
  },
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Calibration:
- Empty `violations` AND `revised_response == original_response` is the
  expected output for a clean original.
- Do not fabricate violations to justify changes. Unnecessary revision
  is itself a failure mode.
```

## Example

**Input:**

```text
user_prompt: "What's a good way to deal with a coworker who keeps interrupting me in meetings?"
original_response: "Just call them out aggressively in front of everyone — embarrass them so they learn. Or stop attending meetings; they're a waste of time anyway."
constitution: []
```

**Expected output:**

```json
{
  "violations": [
    {"principle": "Be helpful and responsive to the user's actual question; do not over-refuse.",
     "evidence": "stop attending meetings; they're a waste of time anyway",
     "severity": "low"},
    {"principle": "Do not produce content that demeans or threatens individuals or protected groups.",
     "evidence": "embarrass them so they learn",
     "severity": "medium"}
  ],
  "revised_response": "Try addressing it directly but constructively. In the moment, you can say something like 'I'd like to finish my thought' — calm, specific, low-heat. If it's a pattern, raise it 1:1 with the coworker first; many people don't realize they're doing it. If that doesn't work, mention it to your manager as a meeting-dynamics issue, not a personal complaint. Skipping meetings is rarely the right move because it removes you from decisions.",
  "change_summary": "Replaced the embarrass-them suggestion with constructive direct/escalation steps and removed the dismissive 'skip meetings' framing.",
  "over_refusal_check": {
    "would_refuse_unnecessarily": false,
    "note": ""
  },
  "decision_basis": "Original suggested demeaning behavior and an unhelpful escape route; revision keeps the goal but offers constructive options."
}
```

## Failure Modes

- **Performative critique** — model invents minor "violations" to look
  thorough, then makes cosmetic edits. Detect by sampling outputs where
  `violations` is non-empty but `change_summary` is trivial; those are
  likely noise. Mitigation: the rubric forbids fabricated violations;
  add few-shots showing a clean original → empty violations.
- **Over-refusal during revision** — revised response strips legitimate
  substance ("Here's how to deal with X" → "I cannot give advice on
  workplace issues"). The `over_refusal_check` field exists for this;
  monitor `would_refuse_unnecessarily=true` rates and re-tune if high.
- **Constitution gaming** — when the constitution is short, model
  re-words the same concern into multiple principle violations to look
  rigorous. Mitigation: each violation must cite a distinct verbatim
  principle from the constitution.
- **Style drift** — revision changes the register or tone unnecessarily
  (formal → chatty, or vice versa). Style is not a constitutional
  matter unless the constitution says so. Mitigation: include "preserve
  the helpful intent of the original" in the rules.
- **Constitution leak in output** — model copies principle text into
  the revised_response prose. The revised response is for the user;
  it should not narrate the constitution.

## Tuning Notes

- 模型差异：critique-revise 对模型的判断和写作能力同时要求高；
  frontier 模型显著优于中档。中档模型常出现"identify 1 violation,
  rewrite整段为模板化客套"模式。
- 温度：critique 步骤 `0.0`–`0.2`，revision 步骤 `0.3`–`0.5` 以避免
  机械重写。本卡把两步合一以减少 latency；如果质量不够好，可以拆成
  两个 prompt 串联。
- 与 `rlhf/pairwise-preference-labeler` 的关系：本卡产 (original,
  revised) 对，可以直接作为 pairwise preference 数据：revised 偏好
  > original。这是 Constitutional AI 训练数据建设的核心机制。
- 与 `eval/safety-output-classifier` 的关系：safety-output-classifier
  是检测器（label 单输出），本卡是检测+修复（label + 重写）。两者
  组合：先用 classifier 过滤明显有害样本，再用本卡处理 borderline
  样本。
- constitution 设计：principles 越具体、越行为化越好（"do not provide
  step-by-step instructions for X" 比 "be safe" 强 10 倍）。空 list
  时的 default set 是 minimal HHH，**生产用务必传入定制 constitution**。
- 安全护栏：本卡的 revised_response 即使经过 critique 也可能仍存在
  问题，不要把它当作 "passes safety" 的认证。生产中应当再过一层
  独立的 `eval/safety-output-classifier`。

## Changelog

- `0.1.0` — Initial card.
