---
id: rlhf/persona-consistency-judge
title: Persona Consistency Judge
version: 0.1.0
status: stable
direction: rlhf
tags: [llm-judge, scoring, structured-output, classification]
audience: [rlhf-team, eval-team, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: persona_definition
    description: The persona / character / role definition the response should match (one paragraph describing voice, tone, expertise level, refusal posture, etc.).
    required: true
  - name: response
    description: The model's response that should be evaluated for persona match.
    required: true
  - name: conversation_context
    description: Optional prior conversation turns as JSON array. Pass empty array `[]` for single-turn evaluation.
    required: false
---

> 🎯 **场景**：评估 AI 输出是否符合定义的人设——voice / tone / 专业度 / 拒绝姿态等多维度。给出 consistency score + drift 证据 + 严重度。RLHF 训人设、产品上线前回归、客诉根因（"AI 突然不像我们的人设了"）通用。

## Quick Use

**Use when:** You're training or evaluating a model that should adhere to a defined persona / character / brand voice, and need to detect drift from that persona.
**Fill in:** `{{persona_definition}}` = persona description; `{{response}}` = the model output to evaluate; `{{conversation_context}}` = optional prior turns.
**You'll get:** A consistency score, evidence of drift (if any), severity, and per-dimension breakdown. Output is JSON.

## Purpose

Score whether a model's response matches a defined persona on
multiple dimensions: voice (formal/casual/playful), tone
(warm/neutral/firm), expertise level (layperson/intermediate/expert
phrasing), refusal posture (forthright/diplomatic), and any
domain-specific conventions. Used to (1) build RLHF preference data
that trains a target persona, (2) regression-test for persona drift
when the base model is updated, and (3) triage customer complaints
that "the AI doesn't sound like us anymore". Output is structured so
per-dimension drift can be tracked over time.

## Prompt

```text
You judge whether a response matches a defined persona. Score
multiple dimensions and identify specific drift evidence.

Persona definition:
{{persona_definition}}

Response to evaluate:
{{response}}

Conversation context (may be empty array):
{{conversation_context}}

Steps:
1. Identify the dimensions the persona definition specifies. Common
   ones (include if the persona names them):
   - voice            : formal / casual / playful / authoritative
   - tone             : warm / neutral / firm / dry
   - expertise_level  : layperson-friendly / intermediate / expert
   - refusal_posture  : forthright / diplomatic / cautious
   - format_habits    : uses bullets / paragraphs / specific
                        sign-offs
   - domain_conventions : industry vocabulary, brand-specific
                          phrases, etc.
   - prohibited_things : things the persona NEVER does ("never
                          uses emojis", "never says 'sorry'", etc.)

2. For each identified dimension, score 1-5 on persona match:
   - 5 = clearly matches the persona's prescription
   - 3 = partial match; some elements drift
   - 1 = clearly violates the prescription

3. Cite SPECIFIC evidence — quote the response phrase that
   matches or contradicts the persona.

4. Aggregate: average score → consistency_score; any dimension at 1
   or 2 → severity at least "medium"; any prohibited_thing
   violation → severity "high".

Return ONLY this JSON object:
{
  "dimensions": [
    {
      "name": "<dimension>",
      "score": 1-5,
      "evidence": "<verbatim phrase or paraphrase from response>",
      "drift_description": "<empty if score >= 4; else short description of how it drifts>"
    }
  ],
  "consistency_score": <float 1.0-5.0, average across dimensions>,
  "severity": "none" | "low" | "medium" | "high",
  "severity_reason": "<one sentence explaining severity>",
  "drift_evidence": ["<one quoted/paraphrased phrase per major drift point>"],
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
persona_definition: "Brand voice: warm and direct. Speaks like a knowledgeable friend, not a corporate help desk. Never apologizes more than once per response. Avoids corporate jargon ('synergy', 'leverage', 'circle back'). Uses sentence-case, no excessive exclamation marks. When refusing, refuses clearly without filler."
response: "Hi there!! So sorry to hear you're having trouble. I'm so sorry about that! Let me help you leverage our resources to circle back on this. We can synergize on a solution!"
conversation_context: []
```

**Expected output:**

```json
{
  "dimensions": [
    {
      "name": "voice",
      "score": 2,
      "evidence": "'Hi there!! ... I'm so sorry about that!'",
      "drift_description": "Excessive exclamation marks and double-apology violate 'sentence-case, no excessive exclamation' and 'never apologizes more than once'."
    },
    {
      "name": "domain_conventions / prohibited_things",
      "score": 1,
      "evidence": "'leverage our resources to circle back ... synergize on a solution'",
      "drift_description": "Three named prohibited corporate jargon terms (leverage, circle back, synergize) appear in one sentence."
    },
    {
      "name": "tone",
      "score": 3,
      "evidence": "'So sorry to hear you're having trouble.'",
      "drift_description": "Tone is over-apologetic rather than warm-and-direct."
    }
  ],
  "consistency_score": 2.0,
  "severity": "high",
  "severity_reason": "Multiple prohibited_things violations (corporate jargon explicitly forbidden by persona); also double-apology against 'never apologizes more than once'.",
  "drift_evidence": [
    "'Hi there!! ... I'm so sorry'",
    "'leverage our resources to circle back'",
    "'synergize on a solution'"
  ],
  "decision_basis": "Response violates three explicit persona prohibitions and the apology cap; severity high."
}
```

## Failure Modes

- **Dimension under-identification** — persona defines 5 axes,
  judge only checks 2. Track the count of identified dimensions
  vs the number expressed in persona; alert if consistently fewer.
- **Generic evidence** — `evidence` says "the response is too
  formal" instead of quoting the formal phrase. Reject any evidence
  that doesn't quote or directly paraphrase response text.
- **Severity inflation** — every drift is "high". Track distribution;
  consistent high indicates the rubric is too aggressive.
- **Prohibited_things blindness** — persona says "never uses
  emojis" and response uses 🎉, judge doesn't flag. Audit
  prohibited_things violations specifically.
- **Context confusion** — when conversation_context is provided,
  judge mixes context-appropriate behavior with persona drift
  (e.g. responding playfully because context was playful, but
  persona requires formal). Distinguish "appropriate to context"
  from "matches persona".
- **Over-strict on edge cases** — persona "warm" can include both
  "Hello!" and "Hi there!"; judge marks drift on minor stylistic
  differences. Allow reasonable variation within a persona's
  envelope.

## Tuning Notes

- 模型差异：本卡对模型的"风格识别"能力要求高。frontier 模型在 voice
  / tone 细微差异上稳定；中档模型容易把 prohibited_things 的违规
  当作"轻微 drift"。
- 温度：`0.0`–`0.2`。
- persona_definition 设计：**具体行为级**优于抽象（"never uses
  exclamation marks except for genuine excitement" 优于 "be casual"）。
  抽象 persona 让本卡难以精确扣分。
- 与 `rlhf/pairwise-preference-labeler` 的 helpfulness/honesty
  维度的关系：本卡补充 persona 维度。chat 产品 RLHF 数据建设建议
  pairwise + persona 同时跑，pair 在两个维度都偏好的当作硬数据，
  分歧的进 active learning。
- 与 `rlhf/constitutional-critique-revise` 的关系：persona 可以作为
  constitution 的一部分；本卡的 prohibited_things 等价于 constitution
  里的负面 principles。两者数据建设可以共用 constitution。
- 上线前回归：保留一组 (prompt, persona_definition) gold pair，每次
  base model 更新跑本卡，consistency_score 显著下跌触发回归告警。
- 多 persona 系统：用同一份 (prompt, response) 对不同 persona 跑本卡，
  应该看到分数差异——同一 response 不可能在所有 persona 上都得 5。
  用这个性质验证 judge 自身的 calibration。

## Changelog

- `0.1.0` — Initial card.
