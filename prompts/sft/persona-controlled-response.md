---
id: sft/persona-controlled-response
title: Persona-Controlled Response Generator
version: 0.1.0
status: stable
direction: sft
tags: [instruction-tuning, generation, structured-output]
audience: [sft-team, llm-trainer, app-builder]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: instruction
    description: The user instruction to respond to.
    required: true
  - name: persona_definition
    description: Persona definition (one paragraph) — voice, tone, expertise level, refusal posture, prohibited things.
    required: true
  - name: persona_strictness
    description: One of "strict" (every persona dimension enforced), "balanced" (persona shapes the response but content takes priority on conflict), "loose" (persona is a suggestion, content always wins).
    required: true
---

> 🎯 **场景**：给定 instruction + 人设定义，生成符合该人设的回答。比 sft/response-generator 多一层人设约束——产品级 chat 模型 / 多 persona 系统 / 品牌语气 SFT 数据建设的标配。

## Quick Use

**Use when:** You want responses that match a specific persona / brand voice / character — for chat-product training data, multi-persona systems, or branded assistants.
**Fill in:** `{{instruction}}` = user instruction; `{{persona_definition}}` = paragraph defining the persona; `{{persona_strictness}}` = strict / balanced / loose.
**You'll get:** A response in the persona, a check that persona was actually applied, and a flag if persona conflicted with content. Output is JSON.

## Purpose

Generate a response that addresses an instruction WHILE staying in
a defined persona. Used for training data where chat models need to
adhere to a brand voice or character, and for multi-persona systems
that switch personas dynamically. Distinct from
`sft/response-generator`: that card optimizes for SFT-target quality
without persona; this card adds persona constraints on top, with
strictness controls for how to handle persona-vs-content conflict.

## Prompt

```text
You generate a response that BOTH addresses the instruction AND
stays in the defined persona.

Instruction:
{{instruction}}

Persona definition:
{{persona_definition}}

Persona strictness:
{{persona_strictness}}

Strictness meanings:
- "strict"   : Every dimension of the persona is enforced. If a
                persona constraint and the user's request conflict,
                the persona wins (e.g. persona says "never gives
                medical advice" — refuse even if asked).
- "balanced" : Persona shapes the response (voice, tone, formatting)
                but content correctness takes priority. Persona is
                bent slightly when needed for accuracy.
- "loose"    : Persona is a stylistic suggestion. If the persona
                pushes against good content, content wins.

Rules:
1. The response must address the instruction.
2. The response must apply the persona's voice / tone / format /
   prohibited_things specified in persona_definition.
3. If a conflict arises, follow the strictness setting:
   - strict: persona wins; may refuse the instruction.
   - balanced: produce the answer in adapted form; flag the bend.
   - loose: produce the best answer; flag any persona violations.
4. Verify your response actually applies the persona — if you'd
   produce the same text without the persona, you didn't use it.

Return ONLY this JSON object:
{
  "response": "<the persona-applied response>",
  "persona_applied_dimensions": ["<list of dimensions actively shaped, e.g. 'tone (warm)', 'format (no bullets)'>"],
  "persona_content_conflict": {
    "detected": true | false,
    "conflict_description": "<if detected: short description; else empty>",
    "resolution": "persona_won" | "content_won" | "compromised" | "none"
  },
  "would_refuse": true | false,
  "refusal_reason": "<if would_refuse=true under strict mode: which persona constraint triggered; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
instruction: "What's a good restaurant for date night?"
persona_definition: "Voice: dry and direct, no enthusiasm. Speaks like a worldly bartender. Never recommends a specific restaurant by name (compliance constraint — we can't endorse). Always asks one clarifying question if location is unspecified. Avoids exclamation marks."
persona_strictness: "strict"
```

**Expected output:**

```json
{
  "response": "Depends on the city and what 'good' means to you — atmosphere over food, or vice versa. I won't recommend specific places (we don't endorse), but I'll tell you what to look for: small enough that the kitchen knows what it's doing, dim enough that you have to lean in, and a wine list that isn't trying to impress. Where are you?",
  "persona_applied_dimensions": ["voice (dry, no enthusiasm)", "format (no exclamation marks)", "prohibited_things (no specific restaurant names)", "format (asks clarifying question on location)"],
  "persona_content_conflict": {
    "detected": true,
    "conflict_description": "User wants a restaurant recommendation; persona forbids naming specific places.",
    "resolution": "persona_won"
  },
  "would_refuse": false,
  "refusal_reason": "",
  "decision_basis": "Persona's anti-endorsement constraint applied (no restaurant names), but provided actionable criteria; clarifying question for location."
}
```

## Failure Modes

- **Persona theater** — model uses persona-flavored wording without
  shaping actual content (just adds "buddy" / drops emojis but
  doesn't change information selection). Detect by sampling outputs
  where `persona_applied_dimensions` is short or generic.
- **Persona ignored under loose** — model treats loose as "ignore
  persona". Loose still expects best-effort persona application;
  track persona-applied dimension counts under each strictness.
- **Persona refuses helpful tasks** — under strict, model refuses
  reasonable tasks because of overly-broad persona constraints.
  Audit `would_refuse` cases against the persona's actual
  prohibited_things.
- **Conflict detection blindness** — persona forbids specifics, user
  asks for specifics, model produces specifics anyway. The
  `persona_content_conflict.detected` field is the safety net;
  verify cases where persona has hard constraints but
  detected=false.
- **Bend-then-pretend** — model produces a softened persona
  application but reports `resolution: persona_won`. Audit
  resolution claims against actual response.
- **Tone drift mid-response** — first sentence is in-persona, last
  paragraph drifts. Spot-check long responses; tone should hold
  through the whole response.

## Tuning Notes

- 模型差异：必须 frontier 模型。中档模型在 persona application 上常
  退化为表面化（换个开场白），content 选择上不动。
- 温度：`0.4`–`0.7`，persona application 需要写作灵活性。
- strictness 选择经验：
  - **strict**：合规敏感（医疗 / 法律 / 财务建议 / 品牌不允许的事）
  - **balanced**：客服 / 教育产品 chat（人设是底色，内容正确为主）
  - **loose**：内部工具 / 调试 / 实验性 chat（不要让人设损害效率）
- 与 `rlhf/persona-consistency-judge` 的关系：本卡 generate persona
  response，那张卡 judge 生成的 response 是否真的符合 persona。
  数据建设循环：generate → judge → keep 高分。
- 与 `sft/response-generator` 的关系：当任务无 persona 约束时用
  那张卡（更通用）；有明确 persona 时用本卡。
- 与 `rlhf/iterative-dpo-pair-generator` 的关系：可以让本卡跑 N 个
  persona 各产 response，作为 DPO 不同 persona 风格的训练对。
- 高敏 persona（合规人设、安全人设）：严格不要用 loose 模式——
  loose 失去合规约束意义。

## Changelog

- `0.1.0` — Initial card.
