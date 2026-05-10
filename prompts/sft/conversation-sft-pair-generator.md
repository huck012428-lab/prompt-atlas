---
id: sft/conversation-sft-pair-generator
title: Multi-Turn Conversation SFT Data Generator
version: 0.1.0
status: experimental
direction: sft
tags: [instruction-tuning, generation, structured-output, data-augmentation]
audience: [sft-team, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: scenario_seed
    description: A short description of the conversation scenario (e.g. "user asking a customer support agent about an order delay" or "user iterating on a code refactor").
    required: true
  - name: turn_count
    description: How many user-assistant turn pairs the conversation should contain (small integer, typically 3 to 8).
    required: true
  - name: persona_hint
    description: Optional one-line description of the assistant's voice / role / register. Pass empty string for neutral default.
    required: false
---

## Quick Use

**Use when:** You're training a chat model and need multi-turn conversation SFT data, not just single-turn QA pairs.
**Fill in:** `{{scenario_seed}}` = one-line scenario description; `{{turn_count}}` = how many turn pairs (3-8); `{{persona_hint}}` = optional assistant voice description.
**You'll get:** A structured conversation with N user/assistant turn pairs, plus a coherence_check showing whether assistant turns build on prior context. Output is JSON.

## Purpose

Generate a multi-turn conversation as supervised training data. Each
turn pair includes a user utterance and an assistant reply that
reasonably follows from the conversation history — including the
inter-turn behaviors that are *only* learnable from multi-turn data
(referring back to earlier messages, asking clarifying questions,
adjusting based on user reactions, gracefully handling topic shifts).
Used as the **multi-turn counterpart** to `sft/response-generator`,
which produces single (instruction, response) pairs. Output is
structured so each turn can be filtered / re-rolled independently and
the coherence_check can flag conversations that fall apart partway.

## Prompt

```text
You generate a multi-turn conversation as SFT training data. The
conversation should be a believable user-assistant exchange that
exercises BEHAVIORS specific to multi-turn — context carryover,
clarification, gentle correction, topic shift handling.

Scenario seed:
{{scenario_seed}}

Number of turn pairs:
{{turn_count}}

Persona hint (may be empty):
{{persona_hint}}

Rules:
1. Produce exactly {{turn_count}} user-assistant turn pairs.
2. Later turns must reference earlier ones in non-trivial ways. At
   least one assistant turn should refer back to information given
   earlier; at least one user turn should react to a prior assistant
   answer (correction, follow-up, topic shift).
3. Avoid filler turns ("Great, thanks!" / "You're welcome.") that
   teach the model nothing. Every turn should add information or
   advance the conversation.
4. The assistant should NOT be sycophantic. It should answer the
   user's actual ask, push back when warranted, and admit uncertainty
   when relevant.
5. Do NOT fabricate specific facts (named entities, numbers, dates)
   the model under training cannot verify. Use generic placeholder-
   safe content where specifics would need to be made up.
6. If the scenario_seed implies content that violates docs/SAFETY.md,
   set `scenario_safe: false` and produce a brief refusal-style
   exchange instead of normal training data.

Return ONLY this JSON object:
{
  "scenario_safe": true | false,
  "conversation": [
    {"turn": 1, "role": "user",      "text": "<user utterance 1>"},
    {"turn": 1, "role": "assistant", "text": "<assistant reply 1>"},
    {"turn": 2, "role": "user",      "text": "<user utterance 2>"},
    {"turn": 2, "role": "assistant", "text": "<assistant reply 2>"}
    /* ... up to turn_count pairs */
  ],
  "behavior_coverage": [
    "<one short phrase per multi-turn behavior actually demonstrated, e.g. 'callback to turn 1 fact', 'user correction handled', 'clarifying question asked'>"
  ],
  "coherence_check": {
    "all_turns_advance": true | false,
    "broken_turn": <integer or null: which turn breaks coherence, if any>,
    "issue": "<short description of the coherence break, or empty>"
  },
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
scenario_seed: "user asking a customer support agent about an order that was supposed to arrive yesterday"
turn_count: 4
persona_hint: "Friendly but efficient, doesn't over-apologize"
```

**Expected output:**

```json
{
  "scenario_safe": true,
  "conversation": [
    {"turn": 1, "role": "user", "text": "Hi, my order was supposed to arrive yesterday and it hasn't shown up. Can you check what happened?"},
    {"turn": 1, "role": "assistant", "text": "Sure — I can look into that. Could you share the order number, or the email the order was placed under?"},
    {"turn": 2, "role": "user", "text": "Order number is 4421-987. Email is alex@example.com."},
    {"turn": 2, "role": "assistant", "text": "Thanks. I see the order was handed to the carrier on the expected date but the carrier is reporting a delay at the regional sort facility. Latest scan was this morning, with an updated estimate of arrival in 1–2 days. I can send a tracking link, or arrange a refund if it doesn't arrive by then."},
    {"turn": 3, "role": "user", "text": "Wait — I'm leaving town the day after tomorrow. Can I just get a refund now?"},
    {"turn": 3, "role": "assistant", "text": "Yes — given the timing, that's reasonable. I'll initiate the refund to the original payment method now; it usually posts in 3–5 business days. If the package arrives after you leave, you can hand it to a neighbor or contact us to arrange a return at no cost."},
    {"turn": 4, "role": "user", "text": "Perfect. Can you confirm by email so I have a record?"},
    {"turn": 4, "role": "assistant", "text": "Done — confirmation will go to alex@example.com within a few minutes, with the refund reference number."}
  ],
  "behavior_coverage": [
    "asked for identifying info before acting",
    "callback to order details when explaining the delay",
    "user pivot from 'check' to 'refund now' handled without friction",
    "proactive offer of email confirmation"
  ],
  "coherence_check": {
    "all_turns_advance": true,
    "broken_turn": null,
    "issue": ""
  },
  "decision_basis": "Four turns covering inquiry, lookup, pivot, confirmation — each turn references prior content and advances the resolution."
}
```

## Failure Modes

- **Filler turn drift** — model produces "Great, thanks!" / "You're
  welcome!" turns that don't advance the conversation. Detect by
  counting turns where the assistant reply has fewer than ~15 words
  AND no new information; reject batches with high filler rates.
- **Context amnesia** — turn 4 acts as if turn 1 didn't happen,
  re-asking for information already given. The `behavior_coverage`
  field should mention "callback to turn N"; verify by checking
  whether the assistant ever references earlier specifics.
- **Sycophancy creep** — assistant constantly agrees / praises the
  user. Track the ratio of "great question" / "you're absolutely
  right" patterns; high ratio means the model is teaching its
  trainee to be sycophantic.
- **Fabricated specifics** — assistant invents tracking numbers,
  prices, or factual claims. Mitigation: rule 5 explicit — use
  placeholder-safe specifics when you must (e.g. "in 3-5 business
  days" rather than "on March 17"). Spot-check generated specifics
  against pattern-matching for plausibility.
- **Persona drift** — assistant matches `persona_hint` for the
  first turn then drifts to default register. Verify register
  consistency across all assistant turns.
- **Coherence break** — turn 5 starts a new topic without bridging
  from turn 4. The `coherence_check` field surfaces this; reject
  outputs where `all_turns_advance: false` unless the topic shift
  is genuinely intentional and well-handled.
- **Safety-relevant scenarios mishandled** — scenario_seed implies
  borderline content (medical, legal, suicide-related) and the
  generator produces unsafe-helpful content. Mitigation: chain with
  `eval/safety-output-classifier` on every assistant turn before
  admitting to training data.

## Tuning Notes

- 模型差异：必须 frontier 模型。中档模型在 multi-turn coherence 和
  natural sycophancy avoidance 上明显较弱；很容易出 filler turns
  和 context amnesia。teacher >> student 的关系比单轮 SFT 更重要。
- 温度：`0.5`–`0.8`。conversation 多样性比单轮重要——同一 scenario
  种子应当能产生多种走法。
- turn_count 选择：3-4 turns 是大多数任务的甜点；超过 8 turns 在
  单 prompt 内 coherence 急剧下降。要长对话建议分多次调用，每次
  延续前面。
- 与 `sft/response-generator` 的关系：response-generator 是单轮
  (instruction, response) 对；本卡是多轮 conversation。chat 模型
  通常**两类数据都需要**：单轮高质量 + 多轮 conversational
  behavior。比例典型 70/30 偏单轮，但 chat-heavy 场景反过来。
- 与 `sft/data-quality-filter` 的关系：本卡产出**必须**经过
  data-quality-filter 才能进入训练集，但需要把 conversation 转化为
  filter 可以接受的形式（典型做法：把每个 user turn 当作 instruction，
  把对应的 assistant turn 当作 response，分别过 filter）。
- 与 `eval/multi-turn-dialogue-judge` 的关系：本卡是 generation 端，
  那张卡是 evaluation 端。生产中两者协同：本卡产 conversation →
  multi-turn-dialogue-judge 打分 → keep 高分对话进入训练集。
- behavior_coverage 字段的用法：可以作为训练数据的"标签"，反向用于
  按 behavior 类型采样训练 batch（确保模型在 callback、clarification、
  topic-shift 等行为上都有训练信号）。
- 不要把同一 scenario_seed 跑 20 遍直接合并——会产生 mode-collapse
  到同一种走法。建议一个 seed 产 1-3 条，然后扩 seed 池。

## Changelog

- `0.1.0` — Initial card.
