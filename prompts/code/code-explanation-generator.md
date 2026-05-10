---
id: code/code-explanation-generator
title: Code Explanation Generator (audience-aware)
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
  - name: source_code
    description: The code snippet, function, or file to explain.
    required: true
  - name: target_audience
    description: One of "junior_engineer" (knows programming basics, new to this code/domain), "senior_engineer" (skip basics, focus on design choices), "non_technical" (PM / designer; explain WHAT not HOW), "domain_expert" (deep in the problem domain but maybe new to this language/codebase).
    required: true
  - name: focus
    description: Optional one-line hint about what aspect to emphasize (e.g. "why this is faster than the obvious solution", "the security implications", "how the inputs flow"). Pass empty string for a general explanation.
    required: false
---

> 🎯 **场景**：把一段代码的工作原理解释给具体受众听——junior 工程师 / senior 工程师 / 非技术同事 / 领域专家四种语气。输出含解释、关键概念、可能的混淆点。适合 onboarding、技术分享、跨职能沟通。

## Quick Use

**Use when:** You want to explain a piece of code to a specific audience (new hire / PM / domain expert) at the right level — not too basic, not too jargon-heavy.
**Fill in:** `{{source_code}}` = the code; `{{target_audience}}` = one of junior_engineer / senior_engineer / non_technical / domain_expert; `{{focus}}` = optional emphasis.
**You'll get:** A leveled explanation, key concepts list, common confusion points, and a one-line summary. Output is JSON.

## Purpose

Produce a code explanation calibrated to a specific audience. A
junior engineer needs different content from a PM, who needs
different content from a domain expert briefly visiting the codebase.
Used for onboarding new hires, cross-functional communication, code
walkthroughs, and tech-talk preparation. Output is structured so the
explanation, key concepts, and confusion points are separately
addressable — useful for incrementally building docs or training
materials.

## Prompt

```text
You explain a piece of code to a specific audience. Calibrate
content depth, vocabulary, and emphasis to that audience.

Source code:
{{source_code}}

Target audience:
{{target_audience}}

Focus (may be empty):
{{focus}}

Audience profiles:
- "junior_engineer"  : Knows programming fundamentals (loops, functions,
                       basic OO). New to THIS code, possibly new to the
                       language. Wants to understand WHAT the code does
                       and WHY each step. Explain idioms encountered.
- "senior_engineer"  : Fluent in the language. Skip basics. Focus on
                       design choices, trade-offs, non-obvious
                       complexity, edge cases the author considered.
- "non_technical"    : PM / designer / business stakeholder. Explain
                       what the code DOES at the user-facing or
                       business-logic level. Avoid mechanical detail.
                       Use analogies to non-code domains where helpful.
- "domain_expert"    : Knows the problem domain (e.g. is a doctor
                       reading medical-data code) but maybe new to the
                       programming language or this codebase. Map
                       code-side concepts back to domain-side concepts
                       they recognize.

Produce:
1. A multi-paragraph explanation appropriate to the audience.
2. A list of key concepts the explanation depends on (technical or
   domain), each with a one-line definition aimed at the audience.
3. A list of "likely confusion points" — places where the chosen
   audience is most likely to misread the code.
4. A one-line summary the audience could quote ("this function does X").

Return ONLY this JSON object:
{
  "explanation": "<the audience-calibrated explanation; 2-5 short paragraphs separated by \n\n>",
  "key_concepts": [
    {"name": "<concept>", "definition": "<one-line definition for THIS audience>"}
  ],
  "likely_confusion_points": [
    {"point": "<one-line description of the likely misread>", "clarification": "<one-line correction>"}
  ],
  "one_line_summary": "<single sentence the audience can quote>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
source_code: |
  async def fetch_user_orders(user_id: str, since: datetime) -> list[Order]:
      cache_key = f"user_orders:{user_id}:{since.isoformat()}"
      if cached := await cache.get(cache_key):
          return [Order.from_dict(o) for o in cached]
      orders = await db.query(
          "SELECT * FROM orders WHERE user_id = $1 AND created_at >= $2",
          user_id, since
      )
      await cache.set(cache_key, [o.to_dict() for o in orders], ttl=300)
      return orders
target_audience: "non_technical"
focus: ""
```

**Expected output:**

```json
{
  "explanation": "This function looks up a user's recent orders. Specifically, it answers: 'show me everything user X bought since some date.'\n\nIt has a small efficiency trick: before going to the database (which is slow), it checks a temporary memory store called a cache. If the same question was asked recently (in the last five minutes), it returns the answer immediately without re-running the database query.\n\nIf the cache doesn't have the answer, it queries the database, sends the result back, AND saves the answer to the cache for next time.",
  "key_concepts": [
    {"name": "cache", "definition": "A temporary memory store that holds recent answers so we don't re-run slow operations every time."},
    {"name": "TTL (time-to-live)", "definition": "How long a cached answer is considered fresh. Here it's 5 minutes — after that the cache forgets and we go back to the database."},
    {"name": "database query", "definition": "The slow but authoritative way to get the data; the function falls back to it when the cache doesn't have a recent answer."}
  ],
  "likely_confusion_points": [
    {"point": "The function looks like it has two different paths, which might suggest two different behaviors.", "clarification": "Both paths return the same kind of result (the user's orders); the only difference is the speed — cache hit is fast, cache miss is slow but still correct."},
    {"point": "The 5-minute TTL might raise the question: what if a user just placed a new order?", "clarification": "If a user places a new order within the 5-minute window, this function might briefly miss it. That's a deliberate trade-off favoring speed; if real-time accuracy matters, the caller should use a different function or the TTL needs to be shorter."}
  ],
  "one_line_summary": "Fetches a user's recent orders, using a 5-minute cache to avoid hitting the database for repeated questions.",
  "decision_basis": "Non-technical audience needs the business-logic view (what the function delivers, when it might be stale) without the async/SQL/cache implementation detail."
}
```

## Failure Modes

- **Audience mismatch** — junior_engineer explanation that drops into
  senior-level detail (TLB cache lines, allocator behavior). Track
  audience-vs-content alignment by sampling outputs; junior
  explanations should average ~Flesch reading-ease 50+, non_technical
  should be 60+, senior can be lower.
- **Code-not-business gap on non_technical** — for non-technical
  audiences, model still describes code structure ("the function uses
  an if-else"). Mitigation: rule "explain at user-facing or
  business-logic level"; sample outputs and check whether explanation
  uses any programming jargon.
- **Domain hand-off failure on domain_expert** — for medical /
  scientific code, model fails to map code variables back to
  domain-side concepts (e.g. "blood_pressure" stays "blood_pressure"
  rather than "systolic vs diastolic component this is computing").
  Pass `focus` to nudge specifically.
- **Hallucinated complexity** — invents trade-offs or design rationale
  the code doesn't actually demonstrate. Verify confusion_points
  point to actual confusable parts of the code.
- **Length inflation** — explanation creeps to 8 paragraphs.
  Cap parse-time to 2000 chars; reject overlong outputs.
- **One_line_summary collapse** — summary is "This function processes
  data" — uselessly generic. Reject if it contains <8 distinct content
  words.

## Tuning Notes

- 模型差异：本卡对**写作能力**要求高于代码理解能力；frontier 模型在
  audience calibration 上显著优于中档。中档模型容易把 senior 和
  junior 解释写得很相似。
- 温度：`0.3`–`0.7`。explanation 需要一些写作灵活性。
- audience 准确性：production 中建议 audience 字段从受众管理系统
  读取（不是用户自填），避免输入误差导致风格不匹配。
- 与 `code/code-review-checklist` 的关系：review 是发现问题，本卡
  是解释代码。当代码作为 onboarding 资料分发时，先 review→修复→再
  解释，避免把有 bug 的版本作为教学材料。
- 与 `cot/structured-reasoning-with-rationale-summary` 的关系：那张
  卡是模型自己分解推理；本卡是模型解释外部代码。两者目标不同：前者
  用于让模型自身行为可审计，后者用于人类理解代码。
- 用作 SFT 数据：本卡产出 (code, audience, explanation) 三元组可以
  作为 code-explanation 任务的训练数据；建议先用人工抽检 audience
  匹配度（约 50 例）做 calibration。
- non_technical 受众的特殊注意：避免技术细节是好的，但**不要**把
  技术细节歪曲成与代码不符的"业务故事"。confusion_points 字段就是
  专门留给 honest-about-trade-offs 用的。

## Changelog

- `0.1.0` — Initial card.
