---
id: code/test-case-generator
title: Test Case Generator
version: 0.1.0
status: stable
direction: code
tags: [test-generation, generation, structured-output]
audience: [app-builder, prompt-engineer, llm-trainer]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: source_code
    description: The function, method, or class to generate tests for.
    required: true
  - name: language_hint
    description: Programming language and test framework (e.g. "Python with pytest", "TypeScript with Vitest", "Java with JUnit 5"). Pass empty string if obvious from the code.
    required: false
  - name: coverage_focus
    description: Comma-separated coverage priorities chosen from happy_path, edge_cases, error_handling, boundary_conditions, regressions. Pass empty string for the default balanced set.
    required: false
---

> 🎯 **场景**：给一段代码（函数/方法/类）生成测试用例，按 happy path / 边界 / 异常 / 错误处理分类。每个测试自带"为什么测这个"的理由。适合 PR 自审、增加测试覆盖率、教学场景。

## Quick Use

**Use when:** You want to generate test cases for a function or class with explicit coverage of happy path, edge cases, and error handling.
**Fill in:** `{{source_code}}` = the code to test; `{{language_hint}}` = optional language + test framework; `{{coverage_focus}}` = optional priorities.
**You'll get:** A categorized list of test cases each with input, expected output, rationale, and priority. Output is JSON.

## Purpose

Generate test cases for a function or class, organized by category
(happy path, edge cases, error handling, boundary conditions,
regressions) with explicit rationale for why each test exists. Used
for PR self-review, raising test coverage on legacy code, and
teaching new engineers what "good test coverage" looks like for a
given piece of logic. Output is structured so each test can be
filtered, prioritized, or fed into an automated test-writer.

This card produces test *specifications* (input, expected output,
rationale), not the test code itself. Generate the actual test
syntax separately, or chain with a code-generation prompt that
takes these specs as input.

## Prompt

```text
You generate test cases for a piece of code. Goal: produce a
categorized list of tests covering happy path, edge cases, error
handling, and boundary conditions, with rationale for each.

Source code:
{{source_code}}

Language and test framework hint (may be empty):
{{language_hint}}

Coverage focus (may be empty; if empty use a balanced set across all
categories):
{{coverage_focus}}

Categories:
- happy_path           : Normal expected inputs producing expected
                          outputs.
- edge_cases           : Unusual but valid inputs (empty collections,
                          single-element, max/min values, null where
                          permitted).
- error_handling       : Invalid inputs that SHOULD raise / return
                          error (wrong types, out-of-domain values).
- boundary_conditions  : Off-by-one territory (n vs n-1 vs n+1, first
                          and last elements, exactly-at-threshold).
- regressions          : Tests for known prior bugs in this code,
                          inferred from comments or visible patterns.

Rules:
1. Generate 4-12 test cases total. Fewer is better when the code is
   small.
2. Each test must have a CONCRETE input and a CONCRETE expected
   output (or expected exception type). "Some valid input" is not
   acceptable.
3. The `rationale` MUST name what the test exercises beyond what
   prior tests in the list cover. Don't generate two tests for the
   same condition.
4. If the code's behavior is genuinely ambiguous on some input, set
   `expected_output: "undefined behavior"` and explain in `rationale`.
5. Do NOT invent functions or APIs the source code doesn't show.

Return ONLY this JSON object:
{
  "tests": [
    {
      "id": "t1",
      "category": "<one of the five>",
      "name": "<short snake_case identifier for this test>",
      "input": "<concrete input value(s) — primitives written as JSON; complex inputs described compactly>",
      "expected_output": "<concrete expected return value, OR exception type and message hint, OR 'undefined behavior'>",
      "rationale": "<one sentence: what this test specifically exercises>",
      "priority": "high" | "medium" | "low"
    }
    /* 4-12 entries */
  ],
  "coverage_summary": {
    "happy_path": <integer count>,
    "edge_cases": <integer count>,
    "error_handling": <integer count>,
    "boundary_conditions": <integer count>,
    "regressions": <integer count>
  },
  "untested_aspects": ["<aspect of the code not covered by these tests, e.g. 'thread safety', 'I/O failures'>"],
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
source_code: |
  def safe_divide(a, b, default=0):
      """Divide a by b, returning default on division by zero."""
      if b == 0:
          return default
      return a / b
language_hint: "Python with pytest"
coverage_focus: ""
```

**Expected output:**

```json
{
  "tests": [
    {"id": "t1", "category": "happy_path", "name": "positive_integers", "input": "a=10, b=2", "expected_output": "5.0", "rationale": "Verifies normal division of positive integers.", "priority": "high"},
    {"id": "t2", "category": "happy_path", "name": "negative_dividend", "input": "a=-10, b=2", "expected_output": "-5.0", "rationale": "Verifies sign propagation through normal path.", "priority": "medium"},
    {"id": "t3", "category": "error_handling", "name": "division_by_zero_default", "input": "a=10, b=0", "expected_output": "0", "rationale": "Verifies the safe-by-default behavior — the core feature of this function.", "priority": "high"},
    {"id": "t4", "category": "error_handling", "name": "division_by_zero_custom_default", "input": "a=10, b=0, default=-1", "expected_output": "-1", "rationale": "Verifies that the custom default is honored on division by zero.", "priority": "high"},
    {"id": "t5", "category": "boundary_conditions", "name": "zero_dividend", "input": "a=0, b=5", "expected_output": "0.0", "rationale": "Verifies zero-as-input goes through normal path, not zero-default.", "priority": "medium"},
    {"id": "t6", "category": "edge_cases", "name": "float_inputs", "input": "a=1.5, b=0.5", "expected_output": "3.0", "rationale": "Verifies the function handles float inputs (the type hint is implicit).", "priority": "low"}
  ],
  "coverage_summary": {
    "happy_path": 2,
    "edge_cases": 1,
    "error_handling": 2,
    "boundary_conditions": 1,
    "regressions": 0
  },
  "untested_aspects": ["very large numbers (overflow behavior is implicit float behavior)", "type errors on non-numeric inputs"],
  "decision_basis": "Six tests covering normal division, sign handling, the safe-zero behavior with default and custom defaults, and zero-as-input boundary."
}
```

## Failure Modes

- **Vague inputs** — `input: "some valid number"`. The rubric forbids
  this; reject any test where input is non-concrete.
- **Duplicate coverage** — two tests labeled differently but exercising
  the same condition. The `rationale` field surfaces this; if you see
  two rationales describing the same behavior, drop one.
- **Hallucinated APIs** — test calls a method the source code doesn't
  expose. Validate test inputs against the source's signature.
- **Missing the actual purpose** — for `safe_divide`, missing the
  zero-default test would be a major coverage gap. Sample outputs
  and check that the function's docstring/name's central guarantee
  has a `priority: high` test.
- **Category drift** — model labels a happy-path test as
  edge_cases. Detect via sampling and consistency check.
- **Untested-aspects gaslighting** — model lists "thread safety" as
  untested even when the function is obviously stateless and pure.
  Use this field as a hint, not a truth.
- **Test count overshoot** — 20 tests for a 5-line function. Cap
  enforces 4-12, but if the model frequently hits 12 on simple code,
  re-prompt with explicit "fewer is better".

## Tuning Notes

- 模型差异：frontier 模型生成的测试 rationale 更精准；中档模型容易
  把 boundary 和 edge cases 混淆。建议针对 critical 函数用 frontier，
  辅助测试用中档以省成本。
- 温度：`0.2`–`0.5`。完全 0 温会让多次调用产生同样的测试集合；略高
  温度增加多样性，但要保留 priority + rationale 的一致性。
- 与 `code/code-review-checklist` 的关系：review 卡识别测试缺口（在
  testability 维度）；本卡产生具体测试用例填补缺口。两者串联：先
  review → 看到 testability 项 → 用本卡生成。
- 与 `code/code-eval-judge` 的关系：本卡产 test specs；eval-judge
  用 specs 判候选代码是否通过。RLHF/SFT 代码训练数据建设标准管线。
- 与 `sft/data-quality-filter` 的关系：本卡产出可作为 (function, tests)
  对的 SFT 数据；用 filter 卡过滤掉低质量 specs（vague inputs / 重复
  coverage 等）。
- 真实测试代码生成：本卡只产 spec。要落地到 pytest / vitest / junit
  代码，建议串一个轻量的"spec → test code"的 generator prompt，那个
  对模型语法准确度要求高，本卡对模型测试**思维**要求高，分开做更稳。
- 高敏代码（金融、医疗、安全相关）：本卡是辅助，不能替代手工设计的
  threat model 和 property-based testing。

## Changelog

- `0.1.0` — Initial card.
