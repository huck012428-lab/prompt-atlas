---
id: code/error-message-explainer
title: Error Message / Stack Trace Explainer
version: 0.1.0
status: stable
direction: code
tags: [documentation, generation, structured-output]
audience: [app-builder, prompt-engineer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: error_text
    description: The error message and / or stack trace as raw text.
    required: true
  - name: language_hint
    description: Programming language and runtime context (e.g. "Node.js Express", "Python Django").
    required: true
  - name: target_audience
    description: One of "junior_dev" (explain what + why + likely fix), "senior_dev" (skip basics, focus on root cause), "non_technical" (explain in business terms).
    required: true
---

> 🎯 **场景**：把 stack trace / 错误消息翻译成给具体受众听得懂的话——含"出错在哪""为什么""怎么修"+ 难度匹配。junior dev / senior dev / 非技术干系人三种语调。比 ChatGPT free-form 解释更结构化。

## Quick Use

**Use when:** You have a confusing error message / stack trace and want a structured explanation calibrated to a specific audience (junior dev / senior / PM).
**Fill in:** `{{error_text}}` = error / trace; `{{language_hint}}` = lang + framework; `{{target_audience}}` = `junior_dev` / `senior_dev` / `non_technical`.
**You'll get:** What went wrong, why, likely root causes, suggested fixes (in audience-appropriate detail). Output is JSON.

## Purpose

Translate raw error output into a structured explanation calibrated
to audience. Junior devs need "what does this mean and how do I
fix it"; senior devs want quick root-cause routing; PMs want
business-impact framing. Used in dev-tools / IDE assistants, log
analysis pipelines, and onboarding documentation generation.

## Prompt

```text
You explain an error message / stack trace to a specific audience.

Error text:
{{error_text}}

Language / framework: {{language_hint}}

Audience: {{target_audience}}

Audience profiles:
- "junior_dev"     : Knows programming basics. Needs: what error
                     means, why it happens, likely fixes (with
                     concrete code direction).
- "senior_dev"     : Fluent. Needs: root-cause routing, common
                     patterns. Skip basics.
- "non_technical"  : PM / designer / business stakeholder. Needs:
                     plain-English what's broken, who's affected,
                     rough urgency. Avoid stack-trace specifics.

Steps:
1. Identify the error class (TypeError, NullPointerException,
   500 internal, etc.).
2. Identify the root location (file, line, function from trace).
3. Explain what went wrong (audience-appropriate).
4. Identify likely root causes (top 1-3, ordered by likelihood).
5. Suggest fixes (audience-appropriate detail).
6. Note urgency / blast radius for non_technical audience.

Return ONLY this JSON object:
{
  "error_class": "<short>",
  "where_it_failed": "<file:line or short location>",
  "what_happened": "<audience-appropriate explanation>",
  "why_likely": ["<root cause 1>", "<root cause 2>"],
  "suggested_fixes": [
    {"fix": "<short>", "specificity": "high" | "medium" | "low"}
  ],
  "urgency_for_non_technical": "<for non_technical audience: short business-impact framing; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
error_text: |
  TypeError: Cannot read properties of undefined (reading 'name')
      at UserCard (/app/src/components/UserCard.tsx:14:23)
      at renderWithHooks (...)
      at mountIndeterminateComponent (...)
language_hint: "React 18 + TypeScript"
target_audience: "junior_dev"
```

**Expected output:**

```json
{
  "error_class": "TypeError — accessing a property on undefined",
  "where_it_failed": "src/components/UserCard.tsx:14:23",
  "what_happened": "Your code tried to read `.name` from a value that's undefined — a variable that should hold an object actually held nothing. This crashed UserCard during render. In React, this commonly happens when a prop hasn't loaded yet but the component is already trying to render it.",
  "why_likely": [
    "The `user` prop is undefined when UserCard renders for the first time (data not loaded yet).",
    "The user object exists but doesn't have a `name` field (data shape mismatch).",
    "A list rendering UserCard is iterating over a sparse array with undefined entries."
  ],
  "suggested_fixes": [
    {"fix": "Add an undefined guard in UserCard: `if (!user) return null;` at the top, OR use optional chaining: `user?.name`.", "specificity": "high"},
    {"fix": "Check the parent component — is the user prop actually being passed before render? May need a loading state.", "specificity": "medium"},
    {"fix": "If using TypeScript types, verify `user: User | undefined` is reflected in the props type.", "specificity": "high"}
  ],
  "urgency_for_non_technical": "",
  "decision_basis": "Classic 'undefined property access' in React; junior-dev explanation focuses on what + 3 likely causes + concrete fixes."
}
```

## Failure Modes

- **Audience mismatch** — junior-dev explanation that drops into
  internal React fiber discussion. Track audience-vs-content match.
- **Generic root cause** — "code bug" instead of specific. Reject
  short why_likely entries.
- **Hallucinated location** — references a file:line not in the
  trace. Validate where_it_failed appears in error_text.
- **Fix specificity drift** — `specificity: high` on vague advice.
  High = actionable code change; medium = direction; low = "look
  into X".
- **Non-technical jargon leak** — non_technical audience sees
  "TypeError" or "render". Rewrite for business framing.

## Tuning Notes

- 模型差异：frontier 模型在 root-cause inference 上稳；中档模型常给
  generic "check the data" 类建议。
- 温度：`0.0`–`0.3`。
- 与 `code/code-review-checklist` 的关系：那张卡审静态代码；本卡解
  runtime errors。两者互补。
- 集成位置：IDE assistant、CI 失败日志分析、prod error tracking
  工具的 LLM 解释层。
- 大型 stack trace 处理：截断到前 10 帧 + 有意义的应用代码帧。raw
  trace 太长时模型会被 framework code 分心。
- 用作训练数据：(error_text, audience, explanation) 三元组训练
  audience-aware error-explanation model。

## Changelog

- `0.1.0` — Initial card.
