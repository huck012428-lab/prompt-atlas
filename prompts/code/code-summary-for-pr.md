---
id: code/code-summary-for-pr
title: Code Diff Summary for Pull Request
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
  - name: diff
    description: A unified-diff-formatted git diff of the changes (output of `git diff` or `git diff main..HEAD`).
    required: true
  - name: context_hint
    description: One or two sentences from the author about WHY the change exists (a ticket title, a bug description, an objective). Pass empty string if no context available.
    required: false
---

> 🎯 **场景**：把 git diff 转成结构化的 PR 描述——含 summary / 变更点列表 / 风险提示 / 测试建议。比让模型自由写 PR description 更可控，避免遗漏关键变更。适合 PR 自动起稿、code review 准备、release notes 撰写。

## Quick Use

**Use when:** You have a git diff and want a structured PR description (summary, change list, risks, test suggestions) instead of free-form prose.
**Fill in:** `{{diff}}` = the unified-diff text; `{{context_hint}}` = optional one-line author intent.
**You'll get:** A PR-style summary, bullet-list of changes by category, risks/caveats, and suggested test areas. Output is JSON.

## Purpose

Produce a structured PR description from a code diff. Categorizes
changes (feature / bugfix / refactor / docs / tests / dependency
update), identifies high-risk hunks, and suggests test areas. Used
to draft consistent PR descriptions, surface risks before review,
and produce release-note material. Output is structured so the PR
template can be filled programmatically.

## Prompt

```text
You produce a structured PR description from a code diff.

Diff:
{{diff}}

Author context (may be empty):
{{context_hint}}

Steps:
1. Categorize changes. Each hunk fits one of: feature / bugfix /
   refactor / docs / tests / config / dependency / other.
2. For each meaningful change (skip whitespace-only), produce a
   one-line bullet describing what changed.
3. Identify "risk_areas" — hunks that touch security-sensitive
   code, public APIs, data migrations, concurrency primitives, or
   configuration. Be conservative: only flag genuine risk.
4. Suggest "test_areas" — what should reviewers verify or what
   tests should be added.
5. Compose a 1-2 sentence "summary" suitable for the PR title and
   first line.

Return ONLY this JSON object:
{
  "summary": "<1-2 sentence summary>",
  "primary_category": "feature" | "bugfix" | "refactor" | "docs" | "tests" | "config" | "dependency" | "mixed",
  "changes_by_category": {
    "<category>": ["<one-line bullet>"]
  },
  "risk_areas": [
    {"area": "<short description>", "severity": "low" | "medium" | "high", "reason": "<short>"}
  ],
  "test_areas": ["<one bullet per area>"],
  "breaking_changes": ["<short list of breaking changes>"],
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
diff: |
  diff --git a/auth.py b/auth.py
  -    if password == stored_password:
  +    if hmac.compare_digest(password, stored_password):
  diff --git a/test_auth.py b/test_auth.py
  +def test_compare_digest_used():
  +    assert ...
context_hint: "Fix timing attack on password compare reported in security audit."
```

**Expected output:**

```json
{
  "summary": "Replace direct password equality with constant-time comparison to prevent timing attacks (security audit fix).",
  "primary_category": "bugfix",
  "changes_by_category": {
    "bugfix": ["auth.py: replace `==` password compare with `hmac.compare_digest` for constant-time comparison."],
    "tests": ["test_auth.py: add test verifying compare_digest is used."]
  },
  "risk_areas": [
    {"area": "auth.py password comparison", "severity": "high", "reason": "Authentication-critical code; if compare_digest is misused (e.g. wrong types), it could fail-open or fail-closed unexpectedly."}
  ],
  "test_areas": [
    "Run existing auth-related tests; verify normal login still succeeds.",
    "Verify the new test asserts the correct call site."
  ],
  "breaking_changes": [],
  "decision_basis": "Single-file security fix; flagged as high-risk despite small diff because it touches authentication."
}
```

## Failure Modes

- **Whitespace / formatting noise** — model lists every reformatted
  line as a change. Skip whitespace-only hunks; group reformatting
  under one bullet.
- **Risk under-flagging** — touching auth / migration / public API
  not flagged. Audit risk_areas on diffs known to contain such
  changes.
- **Risk over-flagging** — every diff has 5 "high" risks. Track
  distribution.
- **Hallucinated changes** — bullets mention files / functions not
  in the diff. Validate every mentioned identifier appears in the
  diff text.
- **Generic test suggestions** — "add tests" is not actionable.
  Suggest specific functions or scenarios.

## Tuning Notes

- 模型差异：frontier 模型更稳；中档模型在 risk identification 上经常
  漏掉细微风险（如 SQL 字符串拼接、并发原语）。
- 温度：`0.0`–`0.2`。
- diff 大小：建议 <2000 lines。超大 PR 先按 file 切分各跑一遍再合并。
- 与 `code/code-review-checklist` 的关系：那张卡是 review 判断；本卡
  是 description 生成。两者协同：本卡产 PR 起稿 → review-checklist
  做正式 review。
- 与 `code/migration-plan-generator` 的关系：migration 卡是规划"将要
  做的变更"；本卡是描述"已经做的变更"。前者 forward-looking，后者
  retrospective。
- breaking_changes 字段建议接 release notes pipeline——非空时触发
  major version bump 提醒。

## Changelog

- `0.1.0` — Initial card.
