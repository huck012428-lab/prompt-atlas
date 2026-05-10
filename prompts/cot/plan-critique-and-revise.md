---
id: cot/plan-critique-and-revise
title: Plan Critique and Revise
version: 0.1.0
status: stable
direction: cot
tags: [self-check, structured-reasoning, structured-output, decomposition-cot]
audience: [prompt-engineer, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: original_question
    description: The question the plan is trying to answer.
    required: true
  - name: candidate_plan
    description: A reasoning plan as a JSON object — typically the output of cot/least-to-most-decomposition or agent/plan-and-execute-planner.
    required: true
---

> 🎯 **场景**：拿到一个推理计划后，先 critique 再决定执行——发现重复步骤、遗漏 case、依赖错误、不必要复杂等问题，给出修订版。比直接执行错误 plan 再回头修要省 token。

## Quick Use

**Use when:** You've generated a plan (least-to-most decomposition, agent plan, multi-step reasoning) and want to critique-and-revise before execution to catch issues cheaply.
**Fill in:** `{{original_question}}` = the question the plan addresses; `{{candidate_plan}}` = the plan as JSON.
**You'll get:** A critique with specific findings, a revised plan, and a comparison showing what changed and why. Output is JSON.

## Purpose

Take a candidate reasoning or execution plan and critique it before
execution. Common issues caught: redundant steps, missing edge
cases, wrong dependency edges, premature commitment to one approach,
unnecessary complexity. The card produces both the critique
findings and a revised plan, so the executor can use the revised
version directly. Used in any pipeline where plan quality matters
more than plan generation speed.

## Prompt

```text
You critique a candidate plan and produce a revised version.

Original question:
{{original_question}}

Candidate plan:
{{candidate_plan}}

Critique categories:
- "redundancy"      : Two or more steps achieve the same result.
- "missing_step"    : A step needed to answer the question is absent.
- "wrong_dependency": A step claims to need an output that doesn't
                      exist OR doesn't need an output it lists.
- "premature_commit": Plan commits to an approach before evidence
                      supports it.
- "complexity"      : A simpler plan would achieve the same goal.
- "scope_drift"     : A step doesn't contribute to the original
                      question.
- "untestable_step" : A step is too vague to know when it's done.

Steps:
1. Walk through the plan step by step. For each issue you identify,
   add a finding with category, location (which step), severity
   (low / medium / high), and a concrete fix suggestion.

2. Produce a revised plan that addresses high and medium severity
   findings. Low-severity findings can be left unchanged unless
   they're easy fixes.

3. If the original plan is already good (no medium+ findings), set
   "revision_needed": false and return the plan unchanged.

4. If the plan has so many issues that revising piecewise won't
   work, set "rebuild_recommended": true and suggest restarting from
   scratch.

Return ONLY this JSON object:
{
  "revision_needed": true | false,
  "rebuild_recommended": true | false,
  "rebuild_reason": "<if rebuild_recommended: why; else empty>",
  "findings": [
    {
      "category": "<one of the 7 categories>",
      "location": "<step id or 'overall'>",
      "severity": "low" | "medium" | "high",
      "issue": "<one sentence>",
      "fix": "<one sentence>"
    }
  ],
  "revised_plan": { /* same shape as candidate_plan */ },
  "diff_summary": "<one or two sentences describing what changed in revised vs candidate>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
original_question: "What is the average revenue per Apple iPhone sold in Q1 2024?"
candidate_plan: {
  "steps": [
    {"id": "s1", "description": "Find Apple's total revenue for Q1 2024"},
    {"id": "s2", "description": "Find Apple's iPhone revenue for Q1 2024"},
    {"id": "s3", "description": "Find the number of iPhones sold in Q1 2024", "depends_on": ["s2"]},
    {"id": "s4", "description": "Compute average revenue per iPhone", "depends_on": ["s2", "s3"]}
  ]
}
```

**Expected output:**

```json
{
  "revision_needed": true,
  "rebuild_recommended": false,
  "rebuild_reason": "",
  "findings": [
    {
      "category": "scope_drift",
      "location": "s1",
      "severity": "medium",
      "issue": "Step finds total Apple revenue but the question is specifically about iPhone revenue per unit; total revenue is not used by any later step.",
      "fix": "Drop s1; it doesn't feed into the final computation."
    },
    {
      "category": "wrong_dependency",
      "location": "s3",
      "severity": "low",
      "issue": "Finding the number of iPhones sold doesn't depend on knowing iPhone revenue; the dependency 's3 depends on s2' is incorrect.",
      "fix": "Make s3 independent. Both s2 and s3 are starting points; s4 depends on both."
    }
  ],
  "revised_plan": {
    "steps": [
      {"id": "s1", "description": "Find Apple's iPhone revenue for Q1 2024"},
      {"id": "s2", "description": "Find the number of iPhones sold in Q1 2024"},
      {"id": "s3", "description": "Compute average revenue per iPhone (s1 / s2)", "depends_on": ["s1", "s2"]}
    ]
  },
  "diff_summary": "Removed off-scope total-revenue step (was s1); fixed dependency between iPhone revenue and units sold (now parallel, not chained).",
  "decision_basis": "Dropped one scope-drift step and fixed one wrong dependency; revised plan is 3 steps instead of 4 with cleaner DAG."
}
```

## Failure Modes

- **Cosmetic critique** — model lists "the plan could be improved"
  without specifics. Reject findings shorter than ~10 words and
  those without `location`. Each finding must point at a specific
  step or "overall".
- **Critique but no revise** — model lists findings but
  revised_plan is identical to candidate. Verify diff_summary is
  non-empty when revision_needed=true.
- **Over-revise** — model rewrites the plan from scratch when minor
  edits suffice. Track the structural delta between candidate_plan
  and revised_plan; large structural changes should correlate with
  high-severity or rebuild_recommended findings.
- **Severity inflation** — every finding is "high". Track distribution.
- **Missed critical issues** — model OKs a plan with an obvious
  missing step. Sample by running both candidate plan and revised
  plan downstream and comparing answer quality; if the gap is
  small on broken plans, the critique missed something.
- **Rebuild over-trigger** — model recommends rebuild on plans that
  could be patched. Track rebuild_recommended rate; high rate means
  the model gives up rather than revising.

## Tuning Notes

- 模型差异：本卡对模型的"判断 plan 质量"能力要求高。frontier 模型在
  category 区分上稳定（redundancy 不会和 complexity 混淆）；中档
  模型容易把 scope_drift 当作 missing_step。
- 温度：`0.0`–`0.2`，critique 必须可重现。
- 与 `cot/least-to-most-decomposition` 的关系：那张卡产 plan，本卡
  critique plan。最佳 pipeline：least-to-most → 本卡 → 执行。
  额外一次调用换 plan 质量提升通常划算。
- 与 `agent/plan-and-execute-planner` 的关系：同上，那张卡产 agent
  plan，本卡 critique。生产中 plan-and-execute → 本卡 → executor 是
  agent 系统的标配。
- 与 `cot/verify-then-finalize` 的对比：verify-then-finalize 验证
  **答案**；本卡 critique **plan**。前者 post-hoc，后者 pre-hoc。
- 何时不用本卡：plan 极简（≤2 步）时不值得；执行成本极低时不值得。
  本卡的价值在 plan 长 + 执行贵的场景。
- 用作 SFT 数据：(question, candidate_plan, critique, revised_plan)
  四元组可作为 plan-critique 任务的训练数据。

## Changelog

- `0.1.0` — Initial card.
