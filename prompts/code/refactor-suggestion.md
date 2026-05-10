---
id: code/refactor-suggestion
title: Refactor Suggestion (with rationale and diff hint)
version: 0.1.0
status: stable
direction: code
tags: [code-review, generation, structured-output]
audience: [app-builder, prompt-engineer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: source_code
    description: The code to refactor.
    required: true
  - name: refactor_goal
    description: The optimization target. One of "readability", "performance", "testability", "modularity", "type_safety". Pass empty string for general refactoring.
    required: true
  - name: language_hint
    description: Programming language and any framework context. Pass empty string if obvious from the code.
    required: false
---

> 🎯 **场景**：给一段代码提结构化的重构建议。每条建议含：什么问题、改成什么、为什么改、改后会动到哪。围绕一个目标（可读性 / 性能 / 可测试性 / 模块化 / 类型安全）展开。适合 PR 改进、技术债梳理、code review 后续。

## Quick Use

**Use when:** You have working code that's not optimal on a specific axis (readability, performance, testability, modularity, type safety) and want concrete refactor suggestions with rationale.
**Fill in:** `{{source_code}}` = the code; `{{refactor_goal}}` = the optimization target (one of 5 enums); `{{language_hint}}` = optional context.
**You'll get:** A list of refactor suggestions each with the issue, the proposed change, rationale, and an impact estimate. Output is JSON. Does NOT produce the rewritten code — chain with a code-rewriter for that.

## Purpose

Suggest concrete refactors for a given piece of code, prioritized
toward a stated goal (readability / performance / testability /
modularity / type safety). Each suggestion comes with the issue it
addresses, the proposed change, the rationale, and an impact
estimate (how many call sites might need updating, whether tests
would break). Used after `code/code-review-checklist` flags issues,
in tech-debt sprints, and as the planning step before automated
code rewriting.

This card produces *suggestions*, not the rewritten code. The
suggestions are explicit and structured enough to feed into a
separate code-rewriter prompt or a human implementation step.

## Prompt

```text
You suggest refactors for a piece of code, oriented toward a specific
goal. Each suggestion is concrete, justified, and includes an impact
estimate.

Source code:
{{source_code}}

Refactor goal:
{{refactor_goal}}

Language / framework context (may be empty):
{{language_hint}}

Goal definitions:
- "readability"   : Clearer names, less nesting, better structure,
                    self-documenting code. Do NOT change behavior.
- "performance"   : Lower time / memory complexity, avoid redundant
                    work, batch operations. Behavior must stay
                    correct; flag if a refactor changes behavior.
- "testability"   : Reduce coupling, expose seams, make pure
                    functions out of side-effecting ones, lift
                    dependencies to parameters.
- "modularity"    : Better separation of concerns; extract reusable
                    units; reduce coupling between modules.
- "type_safety"   : Better type hints, narrower types, eliminate
                    `any` / `Object` / untyped dictionaries, exhaustive
                    pattern matching.

Rules:
1. Produce 1-5 suggestions. Fewer is better when the code is already
   close to the goal.
2. Each suggestion MUST be concrete: name the function/variable/line,
   describe the change in active voice ("replace X with Y", "extract
   Z into a helper"), not vague ("improve the structure").
3. Each suggestion MUST stay within the chosen goal. Do NOT mix
   goals (e.g. don't propose a performance refactor when goal is
   readability).
4. Be honest about behavioral risk. If a suggestion might subtly
   change behavior (numeric precision, ordering, error timing), flag
   it via behavior_change_risk.
5. If the code is already in good shape for the goal, produce zero
   suggestions and set "already_optimal: true".

Return ONLY this JSON object:
{
  "already_optimal": true | false,
  "suggestions": [
    {
      "id": "s1",
      "issue": "<one sentence: the problem the refactor addresses>",
      "proposed_change": "<one or two sentences: what to do, in active voice>",
      "rationale": "<one sentence: why this advances the chosen goal>",
      "impact": {
        "scope": "local" | "module" | "cross_module",
        "lines_changed_estimate": <integer>,
        "behavior_change_risk": "none" | "low" | "medium" | "high",
        "test_breakage_risk": "none" | "low" | "medium" | "high"
      },
      "priority": "high" | "medium" | "low"
    }
    /* zero to five entries; empty if already_optimal=true */
  ],
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
source_code: |
  def process_orders(orders):
      results = []
      for order in orders:
          if order.status == "pending":
              if order.payment_method == "card":
                  if order.amount > 0:
                      result = charge_card(order)
                      if result.success:
                          send_confirmation(order.email)
                          results.append({"id": order.id, "status": "ok"})
                      else:
                          results.append({"id": order.id, "status": "card_failed"})
                  else:
                      results.append({"id": order.id, "status": "skipped_zero"})
              else:
                  results.append({"id": order.id, "status": "skipped_non_card"})
      return results
refactor_goal: "readability"
language_hint: "Python"
```

**Expected output:**

```json
{
  "already_optimal": false,
  "suggestions": [
    {
      "id": "s1",
      "issue": "Function has 4 levels of nesting (for / if / if / if), making the happy path hard to follow.",
      "proposed_change": "Use guard clauses to flatten: 'if order.status != \"pending\": continue', 'if order.payment_method != \"card\": ... continue', 'if order.amount <= 0: ... continue'. Then the charge logic sits at one indentation level.",
      "rationale": "Guard clauses move filter conditions to the top and keep the main work flat — the standard Python readability idiom for this shape.",
      "impact": {
        "scope": "local",
        "lines_changed_estimate": 15,
        "behavior_change_risk": "none",
        "test_breakage_risk": "none"
      },
      "priority": "high"
    },
    {
      "id": "s2",
      "issue": "Status strings ('ok', 'card_failed', 'skipped_zero', 'skipped_non_card') are repeated as magic strings; one typo makes a silent bug.",
      "proposed_change": "Define an enum or string constants: 'class OrderResult(StrEnum): OK = \"ok\"; CARD_FAILED = \"card_failed\"; SKIPPED_ZERO = \"skipped_zero\"; SKIPPED_NON_CARD = \"skipped_non_card\"'. Use these values throughout.",
      "rationale": "Eliminates magic strings, lets a type checker / IDE catch typos, makes the set of possible statuses discoverable.",
      "impact": {
        "scope": "module",
        "lines_changed_estimate": 8,
        "behavior_change_risk": "none",
        "test_breakage_risk": "low"
      },
      "priority": "medium"
    },
    {
      "id": "s3",
      "issue": "The function builds and returns a list of result dicts; there's no type for what the dict shape is.",
      "proposed_change": "Define a small dataclass or NamedTuple 'OrderResult' with id and status fields, and return list[OrderResult].",
      "rationale": "Self-documents the shape, lets type checkers verify all callers.",
      "impact": {
        "scope": "cross_module",
        "lines_changed_estimate": 12,
        "behavior_change_risk": "none",
        "test_breakage_risk": "medium"
      },
      "priority": "low"
    }
  ],
  "decision_basis": "Three readability suggestions: flatten with guard clauses (highest impact), introduce status enum, type the result shape."
}
```

## Failure Modes

- **Vague suggestions** — "make the code cleaner" with no specifics.
  Reject any `proposed_change` that doesn't name a function /
  variable / specific transformation.
- **Goal drift** — performance suggestions sneaking into a
  readability request. The rubric forbids this; sample outputs and
  check that suggestions stay on-goal.
- **Behavior change blindness** — suggesting a refactor that subtly
  changes behavior (e.g. swapping a stable sort to unstable for
  speed) without flagging behavior_change_risk. Audit
  high-priority suggestions specifically.
- **Impact estimation hallucination** — model claims
  "lines_changed_estimate: 50" without actual basis. Use this field
  as a hint, not a truth; compare against ground-truth diff sizes
  on a calibration set.
- **Test breakage underestimation** — model says
  test_breakage_risk: "none" for changes that obviously affect public
  signatures. Spot-check by tracing whether the suggested change
  modifies any function signature or return shape.
- **`already_optimal: true` over-trigger** — model gives up on code
  that has clear improvements. Track rate; if >20% on benchmark
  imperfect code, the bar is too high.
- **Suggestion count overshoot** — model produces 8 suggestions when
  3 would do. The rubric caps at 5; if hitting 5 frequently on
  small code, re-prompt with explicit "fewer is better".

## Tuning Notes

- 模型差异：goal-specific 建议对模型理解能力要求高。frontier 模型在
  type_safety / modularity 上明显更稳；中档模型容易把 readability
  建议（缩进、重命名）当作万能答案。
- 温度：`0.2`–`0.5`。建议需要一些写作灵活性，但太高会引入幻觉。
- 与 `code/code-review-checklist` 的关系：review 是诊断（identify
  issues），本卡是处方（propose fixes）。典型工作流：review → 看到
  major findings → 用本卡按 dimension 选 goal → 拿建议执行。
- 与代码重写的关系：本卡产 suggestion，**不**产新代码。要落地到
  diff，建议串一个轻量的"refactor → diff"代码生成 prompt。这种分工
  让 suggestion 端可以聚焦判断，rewriter 端可以聚焦语法准确度。
- 与 `code/code-eval-judge` 的关系：refactor 后的新代码可以用
  code-eval-judge 验证：是否仍通过原 task / 测试，是否在指定 goal 上
  改善了维度分数。形成 refactor → eval → 接受/拒绝的闭环。
- 多目标场景：本卡只接受单一 goal。要做多目标 refactor（兼顾
  readability + testability），跑两次本卡，分别取建议，由人工或上层
  逻辑合并/排序，避免一个调用同时摇摆多个目标。
- 高风险代码（核心算法、数值精度敏感、并发原语）：建议仅取本卡
  high priority + behavior_change_risk: none 的项；其他降级为讨论
  材料而非自动化 PR。

## Changelog

- `0.1.0` — Initial card.
