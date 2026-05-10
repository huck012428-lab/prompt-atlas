---
id: code/commit-message-generator
title: Conventional Commit Message Generator
version: 0.1.0
status: stable
direction: code
tags: [documentation, generation, structured-output]
audience: [app-builder, prompt-engineer]
models: [generic, frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: diff
    description: Unified-diff-formatted git diff of staged changes.
    required: true
  - name: convention
    description: One of "conventional_commits" (feat/fix/docs/etc with scope), "imperative_simple" (just imperative title), "verbose" (title + body explaining why).
    required: true
---

> 🎯 **场景**：从 git diff 生成 commit message——按 conventional commits / 简单 imperative / 详细 三种风格。重点是**写"为什么"而不是"做了什么"**（diff 本身就是"做了什么"）。pre-commit hook / git GUI 集成场景。

## Quick Use

**Use when:** You're writing a commit message and want it generated from the diff in a specific style — conventional commits, simple imperative, or verbose with body.
**Fill in:** `{{diff}}` = unified-diff text; `{{convention}}` = `conventional_commits` / `imperative_simple` / `verbose`.
**You'll get:** A well-formed commit message in the requested convention, plus alternatives. Output is JSON.

## Purpose

Generate a commit message from a git diff in a specific convention.
Focuses on "why" the change matters (the diff already shows what
changed). Used in pre-commit hooks, IDE git integrations, and
CI tooling that auto-suggests messages. Output structured so
multiple alternatives can be presented for user choice.

## Prompt

```text
You generate a commit message from a git diff.

Diff:
{{diff}}

Convention: {{convention}}

Convention meanings:
- "conventional_commits" : Format <type>(<scope>): <imperative
                           summary>. Types: feat, fix, docs, style,
                           refactor, perf, test, chore. Scope is
                           optional but recommended.
- "imperative_simple"    : Just an imperative title (50 chars max),
                           no type prefix. "Add user export
                           endpoint", "Fix off-by-one in pagination".
- "verbose"              : Imperative title + blank line + body
                           explaining WHY the change exists. Body
                           wraps at 72 chars.

Rules:
1. Title: imperative mood ("Add" not "Added" or "Adds"). Active
   voice. Under 50 characters.
2. Don't restate the obvious from the diff. "Update file X" is bad;
   "Fix off-by-one in pagination" is good.
3. For "verbose": body explains WHY the change exists — the user
   problem solved, the bug encountered, the constraint addressed.
4. For breaking changes (in conventional_commits style), add `!`
   after type/scope: `feat!: change auth API`.

Return ONLY this JSON object:
{
  "primary_message": "<the recommended commit message>",
  "convention_used": "conventional_commits" | "imperative_simple" | "verbose",
  "alternative_messages": ["<one or two alternatives>"],
  "is_breaking_change": true | false,
  "breaking_change_note": "<if breaking: short description; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
diff: |
  diff --git a/src/auth/password.py b/src/auth/password.py
  -    if password == stored_password:
  +    if hmac.compare_digest(password, stored_password):
convention: "conventional_commits"
```

**Expected output:**

```json
{
  "primary_message": "fix(auth): use compare_digest to prevent password timing attack",
  "convention_used": "conventional_commits",
  "alternative_messages": [
    "fix(auth): replace password equality with constant-time compare",
    "security(auth): use hmac.compare_digest for password check"
  ],
  "is_breaking_change": false,
  "breaking_change_note": "",
  "decision_basis": "Single-file security fix replacing == with compare_digest; classic timing-attack mitigation."
}
```

## Failure Modes

- **Restating the obvious** — "Update password.py file". Reject any
  message that's a literal restatement of file changes.
- **Wrong tense** — "Added user login" instead of "Add user login".
  Imperative is the convention; verify.
- **Length over 50** — title violates length norm. Truncate or
  re-prompt.
- **Missing breaking-change marker** — change clearly removes a
  public API but is_breaking_change=false. Audit for public
  function/API removals.
- **Verbose body that says nothing** — body exists but only restates
  title. Reject.

## Tuning Notes

- 模型差异：本卡相对简单，中档模型够用。
- 温度：`0.2`–`0.4`. 多个 alternatives 需要轻微多样性.
- 与 `code/code-summary-for-pr` 的关系：那张卡是 PR 描述（多文件、
  multi-section）；本卡是单 commit message。前者用于 PR description,
  后者用于 commit log.
- conventional commits 进阶: 配合 conventional-changelog 工具自动生
  CHANGELOG.md, 是版本化项目的标配.
- 集成: 推荐在 commit-msg hook 或 git GUI 客户端用本卡 — staged diff
  → 本卡 → 生成 message → 用户 review / accept. 不要全自动化（用户
  应当 review 关键 commit）.
- 大型 diff: 多文件大 diff 应当先用 `code/code-summary-for-pr` 抽
  high-level 变更, 再用本卡精炼到 commit title.

## Changelog

- `0.1.0` — Initial card.
