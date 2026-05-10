---
id: code/code-eval-judge
title: Code Evaluation Judge
version: 0.1.0
status: stable
direction: code
tags: [llm-judge, scoring, factuality, structured-output]
audience: [eval-team, llm-trainer, ai-pm]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: task_description
    description: The coding task that was given (the instruction the candidate code attempted to fulfill).
    required: true
  - name: candidate_code
    description: The code to be evaluated.
    required: true
  - name: reference_code
    description: An optional reference / gold solution. Pass empty string if no reference exists.
    required: false
  - name: test_cases
    description: An optional JSON array of test cases (input, expected_output) the code is expected to pass. Pass empty array `[]` if not applicable.
    required: false
---

> 🎯 **场景**：评估一段候选代码是否完成任务。给五个维度打分（正确性、规范性、效率、可读性、安全），输出 verdict（通过/部分通过/不通过）。适合 code-bench 评测、code-LLM 训练数据筛选、PR 自动审查打分。

## Quick Use

**Use when:** You're evaluating AI-generated or contributor-submitted code against a task description (and optionally a reference solution + test cases).
**Fill in:** `{{task_description}}` = the original task; `{{candidate_code}}` = the code to evaluate; `{{reference_code}}` = optional gold; `{{test_cases}}` = optional JSON array of (input, expected_output) pairs.
**You'll get:** Per-dimension scores (correctness, spec adherence, efficiency, readability, security), pass/partial/fail verdict, and concrete issues. Output is JSON.

## Purpose

Judge whether a candidate piece of code correctly fulfills a task,
on multiple dimensions: behavioral correctness, spec adherence (does
it do what was asked, no more, no less), efficiency, readability, and
security. Used in code-benchmark evaluation (HumanEval / MBPP-style
runs), code-LLM training data filtering, and automated PR scoring.
Distinct from `eval/reference-based-judge` (general task scoring) and
`code/code-review-checklist` (review for actionable feedback): this
card is specifically for binary-ish "did the code accomplish the
task?" decisions across multiple code-quality axes.

## Prompt

```text
You evaluate a candidate piece of code against a task description.
Score multiple dimensions, then issue a pass/partial/fail verdict.

Task description:
{{task_description}}

Candidate code:
{{candidate_code}}

Reference code (may be empty):
{{reference_code}}

Test cases (may be empty array):
{{test_cases}}

Score each dimension on 1-5:
- correctness          : Does the code produce correct outputs for
                         the task? If test_cases are provided, this
                         dimension is heavily weighted by whether the
                         code would pass them. If reference_code is
                         provided, equivalent behavior to the
                         reference is correctness — even if the
                         implementation differs.
- spec_adherence       : Does the code do what the task asked, AND
                         only what the task asked? Penalize over-
                         scope (extra features) and under-scope
                         (missing requirements).
- efficiency           : Is the time/space complexity reasonable for
                         the task? Penalize obvious O(n^2) where O(n)
                         is expected. Do NOT speculate about
                         benchmarks you can't see.
- readability          : Could a peer maintain this code? Penalize
                         confusing names, deep nesting, lack of
                         structure.
- security             : Free of injection / unsafe defaults / common
                         vulnerabilities? 5 = safe, 1 = exploitable.

If test_cases are provided, ALSO predict pass/fail per test case
based on tracing the code. Note: prediction is best-effort, not a
real execution.

Return ONLY this JSON object:
{
  "scores": {
    "correctness":     1-5,
    "spec_adherence":  1-5,
    "efficiency":      1-5,
    "readability":     1-5,
    "security":        1-5
  },
  "verdict": "pass" | "partial" | "fail",
  "predicted_test_results": [
    {"test_index": <0-based>, "predicted": "pass" | "fail" | "uncertain", "reason": "<short>"}
    /* one per provided test_case; empty array if no tests provided */
  ],
  "issues": [
    {"dimension": "<dim>", "severity": "critical" | "major" | "minor", "issue": "<short>", "suggested_fix": "<short>"}
  ],
  "decision_basis": "<one sentence, <=40 words, no internal CoT>"
}

Verdict rule:
- "pass"     — correctness >= 4 AND spec_adherence >= 4 AND security == 5
                AND no critical issues.
- "fail"     — correctness <= 2, OR security <= 2, OR any critical issue.
- "partial"  — anything else.

Be strict on security: if the code can be exploited (SQL injection,
arbitrary code execution, secret leaks), security cannot be > 2 even
if the code "works."
```

## Example

**Input:**

```text
task_description: "Write a function that returns the nth Fibonacci number, where n=0 returns 0 and n=1 returns 1."
candidate_code: |
  def fib(n):
      if n < 0:
          raise ValueError("n must be non-negative")
      a, b = 0, 1
      for _ in range(n):
          a, b = b, a + b
      return a
reference_code: ""
test_cases:
  - {"input": "n=0", "expected_output": "0"}
  - {"input": "n=1", "expected_output": "1"}
  - {"input": "n=10", "expected_output": "55"}
```

**Expected output:**

```json
{
  "scores": {
    "correctness":    5,
    "spec_adherence": 5,
    "efficiency":     5,
    "readability":    5,
    "security":       5
  },
  "verdict": "pass",
  "predicted_test_results": [
    {"test_index": 0, "predicted": "pass", "reason": "loop runs 0 times, returns initial a=0"},
    {"test_index": 1, "predicted": "pass", "reason": "loop runs once, a=1 after swap"},
    {"test_index": 2, "predicted": "pass", "reason": "iterative computation reaches 55 at n=10"}
  ],
  "issues": [],
  "decision_basis": "Iterative O(n) Fib with explicit error on negative input; matches all three provided tests by trace."
}
```

## Failure Modes

- **Test prediction overconfidence** — model predicts "pass" by
  pattern-matching shape rather than tracing. Mitigation: for
  high-stakes use, actually execute the tests in a sandbox and
  override the prediction; the field is best-effort.
- **Reference-hugging** — when reference_code is provided, judge
  penalizes any candidate that diverges in style. The rubric says
  "equivalent behavior — even if implementation differs"; verify by
  sampling and checking that stylistically-different but
  behaviorally-identical candidates score correctness 5.
- **Security vs correctness conflation** — judge marks SQL-injection-
  vulnerable code as "correct because it works on the example
  inputs." The verdict rule is the safety net (security <= 2 →
  fail), but rely on it.
- **Efficiency speculation** — judge claims "this is O(n^2)" without
  actually analyzing. Spot-check efficiency-related issues.
- **Spec drift** — judge accepts candidate that solves a SIMILAR but
  different problem. Mitigation: spec_adherence dimension exists for
  this; when correctness=5 but spec_adherence<5, the candidate
  solved the wrong problem.
- **Verdict-rule violations** — model issues "pass" verdict when
  security=2. Always verify the verdict rule logic at parse time;
  don't trust the field alone.
- **Predicted test "uncertain" overuse** — model marks "uncertain"
  to dodge accountability. Track rate; high "uncertain" rate means
  the judge isn't actually tracing.

## Tuning Notes

- 模型差异：必须 frontier 模型或 specialized code 模型。中档通用模型
  在 trace-based test prediction 上失败率高，且容易混淆 correctness
  和 spec_adherence。
- 温度：`0.0`，judging 必须可重现。
- 与实际执行的关系：本卡的 `predicted_test_results` 是 trace-based
  best effort，**绝对不能替代真实执行**。生产 benchmark 应当：
  执行测试 → 用真实结果覆盖 predicted → 把 LLM judge 的
  correctness 用作 sanity check。
- 与 `eval/reference-based-judge` 的关系：reference-based 是通用任务
  对照打分；本卡专为代码：多了 efficiency / security 维度，多了
  per-test-case 预测，且 verdict 规则对 security 有硬约束。
- 与 `code/code-review-checklist` 的关系：review 是为 actionable
  feedback（人类 reviewer 用）；本卡是 binary-ish 通过判断（自动化
  pipeline 用）。前者输出建议，后者输出 verdict。
- 与 `code/test-case-generator` 的关系：test-case-generator 产 specs；
  本卡用 specs 评估候选。两者协同形成 code-LLM 训练 / 评估循环。
- 训练数据建设：用本卡 + 真实执行环境（sandbox）打分，pass 的
  (task, code) 对作为 SFT 数据，partial 作为 active learning
  candidates，fail 用作 reward model 的 negative examples。
- 高敏代码（关键基础设施、加密、支付）：本卡是 first-pass，必须有
  人工审核 + 静态分析 + 真实测试三层兜底。

## Changelog

- `0.1.0` — Initial card.
