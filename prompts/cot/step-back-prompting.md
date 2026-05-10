---
id: cot/step-back-prompting
title: Step-Back Prompting (abstract first, then solve)
version: 0.1.0
status: stable
direction: cot
tags: [structured-reasoning, decomposition-cot, structured-output]
audience: [prompt-engineer, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large, reasoning-model]
language: en
input_schema: text
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The question or task to solve.
    required: true
---

> 🎯 **场景**：Step-Back 技术——先"退一步"问出更抽象的元问题（"这个问题属于哪类"、"涉及什么原理"），用元问题的回答作为推理脚手架，再回到原题。降低被表面细节带偏的概率，对原理性 / 法律 / 物理 / 数学题特别有效。

## Quick Use

**Use when:** A question's surface details might mislead direct reasoning, and reasoning from a more general principle would be more reliable.
**Fill in:** `{{question}}` = the original question.
**You'll get:** A more abstract "step-back" question, the answer to it, and the answer to the original question grounded in the principle. Output is JSON.

## Purpose

Apply Step-Back Prompting (Zheng et al.) — instead of jumping
directly to the answer, first generate a higher-level question that
abstracts away the question's surface specifics, answer that
abstract question, then use the abstract answer as a principle to
ground the answer to the original question. Used on tasks where
direct reasoning is prone to surface-feature errors: physics word
problems, legal interpretation, deep-domain trivia, multi-condition
queries. Output is structured so the abstraction step and the final
answer are independently inspectable.

## Prompt

```text
You solve a question using "step-back" prompting: first abstract the
question into a more general principle question, answer the principle
question, then return to the specific question grounded in that
principle.

Original question:
{{question}}

Steps:
1. Generate a "step-back" question that:
   - Removes the specific entities, numbers, or constraints in the
     original.
   - Asks about the underlying principle, category, or rule that
     governs questions of this type.
   - Should be answerable in 1-2 sentences from general knowledge.
2. Answer the step-back question concisely (1-3 sentences). State
   the principle / rule / category.
3. Apply the principle to the original question to derive the
   final answer. Show the application explicitly: "By the principle
   that X, applied to {original question's specifics}, the answer is Y."

If the question doesn't benefit from abstraction (e.g. it's a direct
lookup, or the question already names the principle), set
"step_back_useful": false and answer directly in `final_answer`.

Return ONLY this JSON object:
{
  "step_back_useful": true | false,
  "step_back_question": "<the abstract question, or empty if step_back_useful=false>",
  "step_back_answer": "<the principle / rule / category, 1-3 sentences>",
  "application": "<one or two sentences explicitly applying the principle to the original question, or empty if step_back_useful=false>",
  "final_answer": "<the answer to the original question>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
question: "If I drop a 5kg bowling ball and a 0.5kg apple from a 3-meter cliff at the same time, in a vacuum, which hits the ground first?"
```

**Expected output:**

```json
{
  "step_back_useful": true,
  "step_back_question": "In a vacuum, does mass affect how fast an object falls under gravity?",
  "step_back_answer": "No. In a vacuum, all objects accelerate at the same rate (g ≈ 9.8 m/s² on Earth) regardless of mass — Galileo's principle of equivalence. Mass affects gravitational force but also inertia, and the two cancel.",
  "application": "Since both the bowling ball and the apple fall in a vacuum and start at the same height, they accelerate identically and reach the ground at the same time.",
  "final_answer": "They hit the ground at the same time.",
  "decision_basis": "The surface details (5kg vs 0.5kg) tempt a 'heavier falls faster' answer; stepping back to the equivalence principle prevents that error."
}
```

## Failure Modes

- **Cosmetic step-back** — the "step-back" question is just the
  original with names removed, not actually more abstract. Detect
  by checking that step_back_question contains domain-general words
  (principle, rule, category, mechanism, concept) more often than
  domain-specific entities.
- **Wrong principle** — model abstracts to the wrong governing
  principle (e.g. invokes momentum conservation for a kinematics
  problem). Sample outputs and check application correctness.
- **Step-back that loses essential context** — abstraction discards
  the very thing that makes the question non-trivial (e.g. drops
  "in a vacuum" qualifier and then gives the air-resistance answer).
  Mitigation: rule "removes surface specifics" should preserve
  conditions that change which principle applies.
- **Forced step-back** — model insists on stepping back when the
  question is a direct lookup ("What's the boiling point of water at
  sea level?"). The `step_back_useful: false` path exists for this;
  if the rate is <5%, the bar for "useful" is too lax.
- **Application gap** — step_back_answer is correct but `application`
  doesn't actually use the principle to derive the answer. Audit
  outputs where final_answer is correct but application is empty
  or generic.
- **Confidence collapse on hard questions** — for genuinely difficult
  questions, model produces a vague step-back-answer to avoid
  committing. The principle should be a concrete claim; reject vague
  ones.

## Tuning Notes

- 模型差异：本卡对模型的"识别问题类别"能力要求高。frontier 模型在
  step_back 抽象的精准度上明显更稳；中档模型容易产生 cosmetic step-back。
- 温度：`0.0`–`0.3`。abstraction 必须可重现。
- 适用问题类型（按 ROI）：
  - **高**：物理 / 数学带表面诱导（"重的物体下落更快"陷阱）、法律
    场景（"违反规定"vs"违反原则"）、医学（症状与原理映射）
  - **中**：deep-domain trivia（"哪个朝代的什么事件"——先识别朝代特征）
  - **低**：直接 lookup（boiling point of water at sea level）
  - **不适合**：纯创造性写作（步入抽象反而限制）
- 与 `cot/least-to-most-decomposition` 的对比：least-to-most 把问题
  拆成更简单的**子问题序列**，是水平分解；step-back 把问题升维成
  **更抽象的问题**，是垂直抽象。前者适合 compositional 任务，后者
  适合原理性任务。
- 与 `cot/structured-reasoning-with-rationale-summary` 的关系：
  本卡是更"结构化"的特殊形式——sub_steps 退化成 step_back_question +
  application 两步。可以认为 step-back 是 structured-reasoning 的
  专用变种。
- 与 `cot/self-consistency-aggregator` 的关系：step-back 减少单路径
  方差（通过抽象去 noise）；self-consistency 通过多采样投票去 noise。
  两者正交，可叠加（多次跑 step-back 再投票）。
- 用作训练数据：(question, step_back_q, step_back_a, application,
  final_answer) 五元组可作为 Step-Back SFT 训练数据；建议手工 spot
  check 抽象质量后再入训练集。

## Changelog

- `0.1.0` — Initial card.
