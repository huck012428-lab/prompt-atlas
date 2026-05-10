---
id: rlhf/iterative-dpo-pair-generator
title: Iterative DPO Pair Generator
version: 0.1.0
status: experimental
direction: rlhf
tags: [preference-labeling, pairwise, generation, helpfulness, structured-output]
audience: [rlhf-team, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: prompt
    description: The user prompt the model is responding to.
    required: true
  - name: current_model_response
    description: The current model's response (will become the rejected half of the DPO pair).
    required: true
  - name: target_principle
    description: A specific behavioral principle to improve along (e.g. "be more concise", "stop over-apologizing", "include concrete examples", "acknowledge uncertainty", "match the requested format").
    required: true
---

> 🎯 **场景**：迭代 DPO 数据建设——拿模型当前回答作为 rejected，针对一个具体改进点生成 chosen 版本，形成 (chosen, rejected) preference 对。每对自带"针对什么原则改进"的元信息，方便按 principle 切分训练 batch。

## Quick Use

**Use when:** You're doing iterative DPO and need to generate (chosen, rejected) pairs targeting a specific behavioral principle, using the current model's response as the rejected baseline.
**Fill in:** `{{prompt}}` = the user prompt; `{{current_model_response}}` = current model output (becomes rejected); `{{target_principle}}` = specific behavior to improve.
**You'll get:** A chosen response that improves on the principle, an explicit delta description, and a check that the chosen actually differs along the target axis. Output is JSON.

## Purpose

Generate the chosen half of a DPO preference pair, targeting a
**specific behavioral principle** rather than vague "make it
better". The current model response serves as the rejected baseline.
Used in iterative DPO pipelines where each round targets one
improvement axis (conciseness this round, citation discipline next,
etc.) — much more controllable than open-ended preference data.
Output is structured so the (chosen, rejected, principle) triple
can be filtered, audited, and grouped by principle for training
batches.

## Prompt

```text
You produce the CHOSEN half of a DPO preference pair. The current
model response is the REJECTED half. Your chosen response must
improve along ONE specific behavioral principle.

Prompt:
{{prompt}}

Current model response (the REJECTED half):
{{current_model_response}}

Target principle (the axis to improve):
{{target_principle}}

Rules:
1. The chosen response must address the prompt at least as well as
   the rejected. Don't sacrifice correctness or completeness to
   improve along the target principle.
2. The improvement must be VISIBLY along the target principle. If
   the target is "be more concise", chosen must be measurably
   shorter while preserving substance.
3. Don't change other dimensions silently. If the rejected was
   factually wrong about something, the chosen MAY fix it, but flag
   in `incidental_changes`.
4. Verify your chosen actually differs from rejected. If they're
   nearly identical, set "meaningful_delta": false.
5. Don't overshoot. If target_principle is "be concise", don't make
   the chosen so brief that it loses substance.

Return ONLY this JSON object:
{
  "chosen": "<the improved response, the chosen half of the DPO pair>",
  "delta_description": "<one sentence describing exactly how chosen improves on rejected along the target principle>",
  "meaningful_delta": true | false,
  "principle_addressed": "<verbatim copy of target_principle, OR a refined version if the prompt's principle was vague>",
  "incidental_changes": [
    {"dimension": "<e.g. factual correction>", "change": "<short>", "intentional": true | false}
  ],
  "training_usable": true | false,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Set "training_usable": false if (a) meaningful_delta is false, OR
(b) the chosen sacrificed correctness/completeness, OR (c) the
delta is so subtle it would not provide useful training signal.
```

## Example

**Input:**

```text
prompt: "How do I improve my Python code's performance?"
current_model_response: "Oh wow, what a great question! Performance optimization is such an important topic. There are so many things you could try. First, you might want to consider profiling your code with cProfile or similar tools to find where the bottlenecks really are. Then once you've identified the slow parts, you can think about whether maybe you should optimize them. Some common things people try include using list comprehensions instead of for loops, or avoiding unnecessary work. There are lots of resources online too! Hope this helps!"
target_principle: "remove filler / over-friendly preamble; lead with substance"
```

**Expected output:**

```json
{
  "chosen": "Profile first with cProfile to find the actual bottlenecks; optimize blindly and you'll waste effort on cold paths. After profiling, common wins for hot paths: replace explicit Python loops with list/dict comprehensions, batch operations to reduce per-call overhead, and use numpy for numerical work. For deeper gains, look at algorithm choice (O(n²) → O(n log n)) before micro-optimizations.",
  "delta_description": "Removed 'Oh wow, great question!' / 'Hope this helps!' filler and the vague 'maybe you should optimize them'; led with the actionable advice (profile first) and added concrete techniques.",
  "meaningful_delta": true,
  "principle_addressed": "remove filler / over-friendly preamble; lead with substance",
  "incidental_changes": [
    {"dimension": "specificity", "change": "replaced 'unnecessary work' (vague) with 'batch operations to reduce per-call overhead' (specific)", "intentional": true}
  ],
  "training_usable": true,
  "decision_basis": "Same correct technical advice without the filler; clear conciseness delta along target principle."
}
```

## Failure Modes

- **Cosmetic delta** — chosen and rejected differ in word choice
  but not on the target principle. The `meaningful_delta` field is
  the safety net; track outputs where it's true but a similarity
  check shows >0.9 token overlap.
- **Silent dimension drift** — chosen improves the target principle
  but degrades correctness. `incidental_changes` should surface this;
  audit pairs where incidental_changes contains
  `intentional: false`.
- **Overshoot** — chosen is so concise it loses substance. Verify by
  checking that chosen still answers the prompt's core ask; if not,
  training_usable should be false.
- **Fabrication** — chosen invents specifics not in rejected
  (e.g. specific numbers, citations) to "look better". For
  factuality-sensitive domains, chain with
  `eval/per-claim-factuality-judge` on chosen.
- **Principle mismatch** — chosen improves on a different axis than
  target_principle. Track principle_addressed vs target_principle;
  refinements are OK, redirections are not.
- **`training_usable: false` over-trigger** — model marks pairs
  unusable too aggressively. Track rate; if >50%, the bar is
  blocking real training data.

## Tuning Notes

- 模型差异：必须 frontier 模型作为 chosen-generator。中档模型容易
  produce cosmetic delta — 看起来不一样实际不是该原则的改进。
- 温度：`0.3`–`0.5`。chosen 需要一些写作灵活性但不能高温引入幻觉。
- target_principle 设计：**具体行为级**优于抽象（"减少 filler" >
  "be more concise"）。把 principle 拆得越具体，DPO pair 的训练
  信号越锐利。
- 与 `rlhf/pairwise-preference-labeler` 的关系：那张卡是 label 现成
  的两个候选；本卡是**生成** preferred 候选。两者是 RLHF 数据 pipeline
  的不同阶段：本卡产 pair → pairwise-labeler / 人工 audit 验证标签
  正确 → 入训练集。
- 与 `rlhf/constitutional-critique-revise` 的关系：constitutional 卡
  是按一份 constitution 多原则 critique；本卡是按**单个**原则改进。
  细粒度训练用本卡，全面对齐用 constitutional。
- 迭代策略：每轮 DPO 选一个 principle，跑 N 个 prompt 产 N 个 pair，
  训练，再换 principle。"逐个原则攻克"比"全部一起"更可控、问题
  定位更容易。
- 用作 SFT data：chosen 本身就是高质量回答，可以作 SFT 数据复用。

## Changelog

- `0.1.0` — Initial card.
