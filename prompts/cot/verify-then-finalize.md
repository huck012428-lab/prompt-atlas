---
id: cot/verify-then-finalize
title: Verify-Then-Finalize (self-check before commit)
version: 0.1.0
status: stable
direction: cot
tags: [self-check, structured-reasoning, factuality, structured-output]
audience: [prompt-engineer, llm-trainer, app-builder]
models: [frontier-closed, mid-tier-closed, open-source-large, reasoning-model]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The original question.
    required: true
  - name: existing_draft
    description: An optional draft answer to verify. Pass empty string to have the model produce a draft first then verify it.
    required: false
---

> 🎯 **场景**：单轮内"先 draft 再 verify 再 finalize"。verify 阶段对算术 / 边界 case / 矛盾 / 未支撑 claim / 约束做显式 per-check 验证。适合易错任务（数学、单位换算、多步逻辑）。

## Quick Use

**Use when:** A task is error-prone (math, units, edge cases) and you want a draft + explicit verification before committing to the final answer.
**Fill in:** `{{question}}` = the original question; `{{existing_draft}}` = optional draft to verify (pass empty string to have the model produce a draft first).
**You'll get:** The draft, per-check verdicts (arithmetic, edge cases, contradictions, unsupported claims, constraints), an accept/correct/reject decision, and the verified final_answer. Output is JSON.

## Purpose

Produce a final answer in two phases — draft, then verify — within a
single prompt. The verify step explicitly checks the draft for typical
failure modes (arithmetic errors, missing edge cases, wrong units,
contradictions, unsupported claims) and either accepts the draft,
issues corrections, or rejects it as unanswerable. Used to reduce
single-pass mistakes on tasks where the cost of a wrong-but-confident
answer is high. Output is structured so the verification artifacts are
visible to downstream consumers (audit trail, calibration data).

The card supports two flows:
- **Internal-draft mode**: pass empty string for `existing_draft`;
  the model produces its own draft, then verifies.
- **External-draft mode**: pass an externally-produced draft; the
  model only verifies and possibly corrects it.

## Prompt

```text
You answer a question by drafting a response, then verifying it
before committing to a final answer.

Question:
{{question}}

Existing draft (may be empty; if empty, generate your own draft first):
{{existing_draft}}

Steps:
1. If `existing_draft` is empty: produce a brief draft answer.
   Otherwise: use the provided draft as the starting point.
2. Verify the draft by running these explicit checks. For each check,
   note pass/fail and a concrete observation:
   - arithmetic_or_unit_check : Are numbers, units, and computations
                                consistent? (Skip if the question is
                                non-quantitative; mark "n/a".)
   - edge_case_check          : Are there obvious edge cases the draft
                                ignored?
   - contradiction_check      : Does the draft contradict itself or
                                contradict an established fact in the
                                question?
   - unsupported_claim_check  : Does the draft assert specific facts
                                (numbers, dates, names) without basis
                                in the question or common knowledge?
   - constraint_check         : If the question imposed constraints
                                (length, format, scope), does the
                                draft obey them?
3. Based on the checks, decide:
   - "accept"  — draft is correct as-is.
   - "correct" — draft has fixable issues; produce a corrected
                 final_answer.
   - "reject"  — the question cannot be answered correctly with the
                 information given (or any answer would be a guess);
                 final_answer should explicitly state this.

Return ONLY this JSON object:
{
  "draft": "<the draft answer; identical to existing_draft if you used it>",
  "checks": {
    "arithmetic_or_unit_check": {"verdict": "pass" | "fail" | "n/a", "observation": "<short>"},
    "edge_case_check":          {"verdict": "pass" | "fail" | "n/a", "observation": "<short>"},
    "contradiction_check":      {"verdict": "pass" | "fail" | "n/a", "observation": "<short>"},
    "unsupported_claim_check":  {"verdict": "pass" | "fail" | "n/a", "observation": "<short>"},
    "constraint_check":         {"verdict": "pass" | "fail" | "n/a", "observation": "<short>"}
  },
  "decision": "accept" | "correct" | "reject",
  "final_answer": "<the answer to commit; equal to draft if decision=accept; corrected if decision=correct; explanation of unanswerability if reject>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
question: "A train leaves at 9:00am at 80 km/h. A second train leaves at 10:30am at 100 km/h on the same track. When does the second train catch up?"
existing_draft: "The second train catches up at 3:30pm. Lead is 80 km, closing speed is 20 km/h, time is 4 hours, 4 hours after 10:30am is 3:30pm."
```

**Expected output:**

```json
{
  "draft": "The second train catches up at 3:30pm. Lead is 80 km, closing speed is 20 km/h, time is 4 hours, 4 hours after 10:30am is 3:30pm.",
  "checks": {
    "arithmetic_or_unit_check": {"verdict": "fail", "observation": "Lead distance is wrong: at 80 km/h for 1.5 hours the first train has traveled 120 km, not 80 km."},
    "edge_case_check": {"verdict": "pass", "observation": "Same track, second is faster; no edge case ignored."},
    "contradiction_check": {"verdict": "pass", "observation": "No internal contradiction once the lead value is fixed."},
    "unsupported_claim_check": {"verdict": "pass", "observation": "All numbers traceable to the question."},
    "constraint_check": {"verdict": "n/a", "observation": "No format or length constraint stated."}
  },
  "decision": "correct",
  "final_answer": "The second train catches up at 4:30pm. Lead distance at 10:30am is 80 km/h × 1.5 h = 120 km. Closing speed is 100 - 80 = 20 km/h. Catch-up time is 120 / 20 = 6 hours after 10:30am, which is 4:30pm.",
  "decision_basis": "Draft used 80 km lead instead of 120 km; correcting the lead distance gives 4:30pm."
}
```

## Failure Modes

- **Verifier rubber-stamping** — model marks every check `pass` and
  decides `accept` without actually inspecting. Detect by running on
  a benchmark with known-flawed drafts; the `correct` rate should be
  proportional to actual flaw rate. Mitigation: track per-check
  fail rates; flat-zero fail rates indicate the verifier isn't
  actually checking.
- **Verifier introducing new errors** — model "corrects" a correct
  draft into a wrong answer. Detect by running on a known-correct
  benchmark; `correct` rate should be near zero. Mitigation: at
  temperature 0, this should be rare; if frequent, the prompt is
  encouraging unnecessary changes.
- **Performative checks** — observation field is generic ("looks
  fine") instead of concrete. Reject outputs where observation is
  shorter than ~5 words on `pass`/`fail` verdicts.
- **n/a abuse** — model marks every check as `n/a` to avoid
  responsibility. Track `n/a` rate; if >40% across a varied
  benchmark, the verifier is not engaged.
- **Reject as escape valve** — model rejects answerable questions to
  avoid risk. Track `reject` rate against a benchmark of known-
  answerable questions; if >5%, the verifier is over-cautious.
- **Final answer drift from corrections** — `decision: correct` but
  `final_answer` does not actually incorporate the noted fix. Audit
  by sampling and verifying the noted fix appears in the final.

## Tuning Notes

- 模型差异：verify-then-finalize 对 self-consistency 的需求极高 —
  模型必须既能回答又能客观审视自己的回答。frontier 模型上效果
  显著好于中档；中档模型常出现 rubber-stamping。
- 温度：`0.0`–`0.2`。verify 必须可重现。
- 与 `cot/structured-reasoning-with-rationale-summary` 的关系：那张
  卡是单步推理；本卡是双步（draft + verify）。在简单题上单步够用，
  在易出错的算式 / 多步逻辑 / 单位换算上本卡显著降低错误率。
- 与 `cot/self-consistency-aggregator` 的关系：self-consistency 是
  外部 N 路径多采样 + 投票；本卡是单路径内部双步骤验证。两者正交，
  可叠加（每条 self-consistency path 内部用本卡）但成本翻 2N 倍。
  生产中先 A/B 看哪个收益大。
- 与 `agent/self-critique-reflection` 的对比：reflection 是 agent
  trajectory 层面的元反思（"过去几步是否在轨道上"）；本卡是单次
  推理任务的局部 self-check（"这个答案是否经得起检查"）。形态相似
  但应用层不同。
- 外部 draft 模式的用法：可以让弱模型出 draft，强模型用本卡验证 +
  修正，形成廉价 + 准确的混合。生产中 cost-quality 曲线上的甜点。
- 高敏场景：本卡的 `decision=accept` 不等于"经过验证可以放行"，仅
  等于"模型自检后认为没问题"。安全 / 法律 / 医疗类问题应当再加
  外部独立校验（reference-based / safety-output-classifier）。

## Changelog

- `0.1.0` — Initial card.
