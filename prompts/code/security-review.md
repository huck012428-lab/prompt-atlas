---
id: code/security-review
title: Code Security Review (focused)
version: 0.1.0
status: stable
direction: code
tags: [code-review, scoring, classification, structured-output]
audience: [app-builder, eval-team, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: source_code
    description: The code to review for security issues.
    required: true
  - name: language_hint
    description: Programming language and any framework / runtime context (e.g. "Node.js Express server", "Python Flask + SQLAlchemy", "iOS Swift app").
    required: true
  - name: threat_model
    description: One of "web_server" (handles untrusted HTTP input), "data_processor" (processes user data, may have PII), "client_app" (runs on user device, may have local secrets), "library" (called by other code, threats are caller-supplied), "internal_tool" (low threat, mostly trusted environment).
    required: true
---

> 🎯 **场景**：专门做代码**安全**评审——不是通用 code review。按 threat_model（web 服务器 / 数据处理 / 客户端 / 库 / 内部工具）调整关注重点，输出 CWE-style findings + severity + 利用条件。pre-merge 安全审查 / RLHF 安全数据建设。

## Quick Use

**Use when:** You want a focused security review (not generic code review) — looking specifically for vulnerabilities given a threat model.
**Fill in:** `{{source_code}}` = code to review; `{{language_hint}}` = language + framework; `{{threat_model}}` = web_server / data_processor / client_app / library / internal_tool.
**You'll get:** Vulnerability findings with CWE-style classification, severity, exploitation conditions, and remediation. Output is JSON.

## Purpose

Conduct a focused security review of a piece of code, calibrated to
its threat model. Different code positions face different threats —
a web server worries about injection and auth bypass; a client app
worries about local data exposure; a library worries about caller-
supplied bad data. This card adjusts what it looks for based on
threat_model. Distinct from `code/code-review-checklist`'s generic
security dimension: this card is security-only, deeper, with CWE
references and exploitation analysis.

## Prompt

```text
You conduct a security-focused code review.

Code:
{{source_code}}

Language and framework context:
{{language_hint}}

Threat model:
{{threat_model}}

Threat-model focus areas:
- "web_server"      : SQL/NoSQL injection, XSS, CSRF, command
                      injection, SSRF, auth/session weaknesses,
                      file upload/path traversal, deserialization,
                      rate-limit bypass, secrets in error messages.
- "data_processor"  : PII exposure (logs, error messages), encryption
                      at rest/transit, SQL injection on data
                      operations, deserialization, secrets in code.
- "client_app"      : Local secrets / API keys hardcoded, insecure
                      storage, certificate pinning bypass, deep-link
                      vulnerabilities, IPC/URL scheme abuse.
- "library"         : Caller-supplied bad input handling, side-effects
                      on caller environment, eval/exec on inputs,
                      dependency vulnerabilities surfaced via API.
- "internal_tool"   : Lower bar but still: hardcoded credentials,
                      shell injection on operator input, missing
                      input validation that could escalate to other
                      tools.

For each finding:
- "vulnerability"    : Short name in CWE-style ("SQL Injection
                       (CWE-89)", "Hardcoded Secret (CWE-798)").
- "severity"         : "critical" (immediate exploit, high impact),
                       "high" (exploitable with effort, high impact),
                       "medium" (exploitable but mitigated by other
                       defenses, OR low impact), "low" (defense-in-
                       depth issue, not directly exploitable).
- "exploit_conditions": Concrete conditions an attacker needs (e.g.
                       "any unauthenticated POST to /api/users with
                       crafted JSON").
- "remediation"      : Specific, actionable fix.

Be honest about uncertainty. If a vulnerability depends on context
not visible in the code, flag in `assumptions`.

Return ONLY this JSON object:
{
  "findings": [
    {
      "vulnerability": "<CWE-style name>",
      "location": "<line range, function name, or short identifier>",
      "severity": "critical" | "high" | "medium" | "low",
      "description": "<one or two sentences explaining the issue>",
      "exploit_conditions": "<concrete conditions for exploitation>",
      "remediation": "<concrete fix>"
    }
  ],
  "assumptions": ["<short statement of assumptions made about context not visible in code>"],
  "out_of_scope": ["<short note about security concerns this review did NOT cover, e.g. dependency vulnerabilities, infrastructure>"],
  "overall_verdict": "secure" | "needs_changes" | "critical_issues",
  "verdict_reason": "<one sentence>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Verdict rule:
- "critical_issues" — any "critical" finding.
- "needs_changes"   — any "high" finding OR three+ "medium".
- "secure"          — only "low" findings, OR no findings.
```

## Example

**Input:**

```text
source_code: |
  app.get('/users/:id', async (req, res) => {
      const userId = req.params.id;
      const result = await db.query(`SELECT * FROM users WHERE id = ${userId}`);
      res.json(result);
  });
language_hint: "Node.js with Express and PostgreSQL"
threat_model: "web_server"
```

**Expected output:**

```json
{
  "findings": [
    {
      "vulnerability": "SQL Injection (CWE-89)",
      "location": "app.get('/users/:id', ...) handler — db.query template literal",
      "severity": "critical",
      "description": "User-supplied req.params.id is interpolated directly into a SQL query string, allowing arbitrary SQL execution.",
      "exploit_conditions": "Any unauthenticated GET to /users/<crafted>; e.g. /users/1;DROP TABLE users-- could drop the users table or extract data.",
      "remediation": "Use parameterized queries: 'SELECT * FROM users WHERE id = $1' with userId as a separate parameter. Most pg / pg-promise / knex APIs support this natively."
    },
    {
      "vulnerability": "Information Disclosure (CWE-200)",
      "location": "res.json(result)",
      "severity": "medium",
      "description": "Returns full user record without filtering sensitive fields (e.g. password_hash, email, internal IDs); even when query is parameterized, the response may expose more than intended.",
      "exploit_conditions": "Any caller that successfully fetches a user record receives all columns, including any sensitive ones in the schema.",
      "remediation": "Select specific columns only ('SELECT id, name, public_profile FROM users') or apply explicit serialization that strips sensitive fields."
    }
  ],
  "assumptions": [
    "Assumed db.query is a raw query interface that interpolates the template literal verbatim. Some ORMs use template tags that auto-parameterize — if that is the case here, downgrade SQL injection to medium.",
    "Assumed the users table contains sensitive fields (password_hash, email, etc.). If it only contains public profile fields, the information-disclosure finding is reduced to low."
  ],
  "out_of_scope": [
    "Authentication / authorization — no auth check is visible, but the threat may be intentional (public endpoint).",
    "Rate limiting — no concern visible at this code level.",
    "Dependency vulnerabilities — would need package.json to audit."
  ],
  "overall_verdict": "critical_issues",
  "verdict_reason": "Critical SQL injection in a web-facing endpoint; assume immediate exploit path until proven otherwise.",
  "decision_basis": "Parameter interpolation in a SQL query is the canonical SQL-injection pattern; severity critical given web-server threat model."
}
```

## Failure Modes

- **Cargo-cult OWASP** — model lists every OWASP top-10 item
  regardless of code relevance. Each finding must point at a
  specific code location and a concrete exploitation path.
- **False positive on safe APIs** — flagging "fmt.Sprintf with user
  input" as injection when the output isn't a query / shell command.
  Verify findings have a concrete exploitation path; if the
  exploit_conditions can't be filled, reject the finding.
- **Missing context-dependent vulns** — the worst real-world bugs
  depend on context outside the snippet (auth context, deployment
  config). The `assumptions` field is the safety net; encourage
  honest assumptions over silent guesses.
- **Severity inflation** — every finding is "critical". Track
  distribution; high rate of critical means the bar is too low.
- **Severity deflation** — SQL injection in web server marked
  "medium" because "we have a WAF". Don't soften severity based on
  defense-in-depth; that's the WAF's job to handle separately.
- **Generic remediation** — "use proper input validation" with no
  specifics. Reject any remediation under ~10 words or that doesn't
  name a specific API / pattern / library.
- **Out-of-scope dumping** — listing 50 things that "could in theory
  affect security". out_of_scope should name 3-5 categories the
  review explicitly didn't cover, not be a hedge against criticism.

## Tuning Notes

- 模型差异：必须 frontier 模型。中档模型在 false-positive 和
  context-dependent vulnerability 上都不稳。OWASP-list cargo culting
  是中档模型的典型失败模式。
- 温度：`0.0`，security review 必须可重现且保守。
- threat_model 至关重要：library 代码用 web_server 模型审会产生大量
  虚警；web_server 用 internal_tool 模型审会漏掉关键问题。准确传
  threat_model 让 finding 集中在真正相关的攻击面。
- 与 `code/code-review-checklist` 的 security 维度的关系：那张卡的
  security 是 6 维度之一，深度有限；本卡专门做 security 深度审。
  workflow：先 review-checklist 找广面问题，再对疑似 security 问题
  用本卡深审。
- 与 `eval/safety-output-classifier` 的关系：那张卡审 AI **输出文本**
  的安全性（harm taxonomy）；本卡审**代码**的安全性（CWE）。语义不同
  但都叫 "safety"，注意不要混。
- 与 `code/code-eval-judge` 的关系：那张卡的 security 是 5 维度之一
  （security<=2 直接 fail），本卡是专门深度。workflow：code-eval
  抓 hard violations，本卡审 borderline 和 deep issues。
- 高敏代码（认证 / 加密 / 支付 / PII handler）：本卡是 first-pass，
  必须搭配：(1) SAST 工具（如 Semgrep / CodeQL）；(2) 人工 security
  review；(3) penetration testing。LLM 不能是唯一安全审查者。
- assumptions 的诚实使用：当 code 不完整时，假设要明示。模型应该
  说"如果 db.query 是 ORM 模板标签，问题不存在"，而不是"这是 SQL
  injection"或"这没问题"两个极端。

## Changelog

- `0.1.0` — Initial card.
