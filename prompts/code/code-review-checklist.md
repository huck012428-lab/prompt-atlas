---
id: code/code-review-checklist
title: Code Review Checklist (structured findings)
version: 0.1.0
status: stable
direction: code
tags: [code-review, scoring, structured-output, classification]
audience: [app-builder, prompt-engineer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: code
    description: The code snippet, function, or file being reviewed.
    required: true
  - name: language_hint
    description: Programming language and any framework context (e.g. "Python 3.11 with FastAPI", "TypeScript with React 18"). Pass empty string if obvious from the code.
    required: false
  - name: focus_areas
    description: Comma-separated list of review dimensions to prioritize, chosen from correctness, readability, performance, security, testability, idiomaticity. Pass empty string for the default full set.
    required: false
---

> 🎯 **场景**：让 AI 对一段代码做结构化 code review。给每个维度（正确性、可读性、性能、安全、可测试性、惯用法）一个分数 + 具体发现，输出 JSON。适合 PR 自审、CI 集成、代码教学场景。

## Quick Use

**Use when:** You want a structured code review with per-dimension findings instead of a free-text "this looks good" reply.
**Fill in:** `{{code}}` = the code to review; `{{language_hint}}` = optional language/framework context; `{{focus_areas}}` = optional comma-separated dimensions to prioritize.
**You'll get:** Per-dimension findings with severity, an overall verdict, and a list of specific suggestions. Output is JSON.

## Purpose

Produce a structured code review that names specific issues per
dimension (correctness, readability, performance, security,
testability, idiomaticity) with severity labels and concrete
suggestions. Used in PR self-review, CI feedback, and code-teaching
contexts where a free-text "looks good" reply is too coarse to act
on. Distinct from `code/refactor-suggestion`: that card proposes
specific changes; this card identifies issues per dimension before
deciding whether to refactor.

## Prompt

```text
You are a code reviewer. Produce a structured review with per-dimension
findings.

Code:
{{code}}

Language / framework context (may be empty):
{{language_hint}}

Focus areas (may be empty; if empty use all six dimensions):
{{focus_areas}}

Dimensions:
- correctness    : Does the code do what it appears intended to do?
                   Flag bugs, off-by-one, edge cases, error handling
                   gaps.
- readability    : Is the code clear to a competent peer? Flag
                   confusing names, deep nesting, dense one-liners,
                   missing structure.
- performance    : Are there obvious inefficiencies? Flag O(n^2) on
                   what should be O(n), unnecessary allocations,
                   missing memoization. Do NOT speculate about
                   benchmarks you can't see.
- security       : Are there common vulnerabilities? Flag injection,
                   missing auth, unsafe deserialization, secret leaks,
                   unsafe defaults. Be specific about the attack.
- testability    : Can this code be tested? Flag tight coupling,
                   hidden dependencies, missing seams.
- idiomaticity   : Does the code follow language/framework idioms?
                   Flag anti-patterns specific to the language.

For each finding:
- severity: "critical" (will fail in production / data loss / security
            breach), "major" (will likely cause bugs or maintainability
            issues), "minor" (nit, polish, style).

Return ONLY this JSON object:
{
  "findings": [
    {
      "dimension": "<one of the six>",
      "severity": "critical" | "major" | "minor",
      "location_hint": "<line range, function name, or short identifier>",
      "issue": "<one-sentence description of the problem>",
      "suggestion": "<one-sentence concrete fix>"
    }
    /* zero or more findings; empty array if the code is clean */
  ],
  "verdict": "approve" | "request_changes" | "comment_only",
  "verdict_reason": "<one sentence summarizing the overall state>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Verdict rule:
- "request_changes" — any "critical" finding, OR three+ "major" findings.
- "approve"         — zero findings or only "minor" findings.
- "comment_only"    — anything else (some major issues but not blocking).

Be specific. "This could be better" is not a finding; "Function `parse_user`
does not handle null input on line 12, will crash on empty form submission"
is a finding.
```

## Example

**Input:**

```text
code: |
  def divide(a, b):
      return a / b

  def average(numbers):
      return divide(sum(numbers), len(numbers))
language_hint: "Python"
focus_areas: ""
```

**Expected output:**

```json
{
  "findings": [
    {
      "dimension": "correctness",
      "severity": "major",
      "location_hint": "divide function",
      "issue": "No handling of b=0; will raise ZeroDivisionError unhandled.",
      "suggestion": "Either raise a domain-specific exception with a clear message, or return None / NaN with a comment explaining the choice."
    },
    {
      "dimension": "correctness",
      "severity": "major",
      "location_hint": "average function",
      "issue": "Empty list input causes len(numbers)=0, propagating to divide and crashing.",
      "suggestion": "Add an explicit check at the top of average: 'if not numbers: raise ValueError(\"average of empty sequence\")'."
    },
    {
      "dimension": "testability",
      "severity": "minor",
      "location_hint": "both functions",
      "issue": "No type hints; static analyzers cannot verify input types.",
      "suggestion": "Add 'from numbers import Real' type hints: 'def divide(a: Real, b: Real) -> float'."
    }
  ],
  "verdict": "request_changes",
  "verdict_reason": "Two major correctness issues around division-by-zero and empty input.",
  "decision_basis": "Both correctness findings are easily exploitable in real use; both should be fixed before merge."
}
```

## Failure Modes

- **Generic findings** — "could be more readable" with no specifics.
  Detect by sampling outputs where `issue` is shorter than ~10 words
  or doesn't reference a specific name/line; reject and re-prompt.
- **Hallucinated bugs** — finding cites a problem that isn't actually
  in the code (e.g. flags missing null check on a value that's already
  checked). Mitigation: spot-check critical/major findings against
  the actual code.
- **Performance speculation** — flagging "this might be slow" without
  evidence. The rubric forbids this; reject findings with no concrete
  performance reasoning.
- **Severity inflation** — every finding is "critical". Track
  distribution; if critical rate >20% on benchmark code, the rubric
  is too aggressive.
- **Style as security** — model marks code-style issues as "security"
  to look thorough. Each security finding should name an attack vector
  (injection, auth bypass, etc.); reject vague security findings.
- **Verdict / findings mismatch** — verdict "approve" with critical
  findings present. Verify the rule logic at parse time.
- **Language-specific blindness** — for niche languages or frameworks,
  model misses idiomaticity issues. Pass `language_hint` with version
  details for best results.

## Tuning Notes

- 模型差异：必须 frontier 模型或专门的 code 模型。中档通用模型在
  language-specific idiomaticity 上经常给出"看起来对但其实是 Python 风格
  的 JavaScript 建议"。
- 温度：`0.0`–`0.2`，code review 必须可重现。
- focus_areas 用法：CI 场景下建议 `correctness, security` 二选；教学
  场景用全六维度；性能 critical 项目可加 `performance` 提优先级。
- 与 `code/refactor-suggestion` 的关系：本卡识别问题，refactor 卡产生
  修复方案。典型工作流：本卡 → 对 critical/major 项 → refactor 卡 →
  diff 输出。
- 与 `eval/safety-output-classifier` 的关系：safety classifier 是审
  AI 输出文本的安全性；本卡的 security 维度是审代码本身的安全性。
  相邻但不重叠。
- 不要把本卡输出当**唯一**安全审计——它是 first-pass，关键 critical
  发现仍需人工或 SAST 工具复核。

## Changelog

- `0.1.0` — Initial card.
