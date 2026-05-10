---
id: rlhf/preference-rationalization-judge
title: Preference Rationalization Judge
version: 0.1.0
status: experimental
direction: rlhf
tags: [llm-judge, scoring, classification, structured-output]
audience: [rlhf-team, eval-team]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: pair
    description: A JSON object with `prompt`, `response_a`, `response_b`, and the labeler's `picked` (a or b) and `rationale`.
    required: true
---

> 🎯 **场景**：审计 RLHF 偏好标签的**理由是否站得住脚**——picked + rationale 是否真的支持那个选择，还是事后合理化。catches 标签噪声 / 标签随机 / 标签理由与实际偏好不符。RLHF 数据质量 audit 必备。

## Quick Use

**Use when:** You're auditing the quality of preference labels in your RLHF dataset and want to detect rationales that don't actually justify the labeler's pick — sign of noisy or rushed labeling.
**Fill in:** `{{pair}}` = JSON with prompt, response_a, response_b, picked, and rationale.
**You'll get:** Rationale validity verdict (supports / weak / contradicts / generic), evidence, and recommendation. Output is JSON.

## Purpose

Audit whether the stated rationale for a preference pick actually
justifies the choice. Common failure modes in RLHF labeling:
"both look fine, picking A" (random), "I prefer A" (no actual
reason), rationale citing a quality the chosen response doesn't
have. This card flags low-quality labels for re-labeling, helping
keep RLHF datasets clean. Used in dataset quality audits and
inter-annotator agreement studies.

## Prompt

```text
You audit a preference label by checking whether the rationale
actually justifies the labeler's pick.

Pair:
{{pair}}

Steps:
1. Read prompt, both responses, and the labeler's picked + rationale.
2. Classify the rationale:
   - "supports"    : Rationale identifies a real difference that
                     does favor the picked response.
   - "weak"        : Rationale points at something real but minor;
                     could go either way reasonably.
   - "contradicts" : Rationale describes a quality the
                     non-picked response actually has more of (or
                     describes a quality both have equally).
   - "generic"     : Rationale could apply to almost any pair
                     ("better quality", "more helpful").

3. If "contradicts" or "generic" — the label may be noisy.
   Recommend re-labeling.
4. Cite evidence: a verbatim phrase from the rationale + a quote
   from the chosen response showing whether the claimed quality
   is actually present.

Return ONLY this JSON object:
{
  "rationale_validity": "supports" | "weak" | "contradicts" | "generic",
  "evidence_from_rationale": "<verbatim phrase>",
  "evidence_from_chosen": "<short evidence whether the rationale's claim is true of the chosen response>",
  "label_confidence": "high" | "medium" | "low",
  "recommendation": "keep" | "re_label" | "drop_from_training",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
pair: {
  "prompt": "Explain how photosynthesis works in 2 sentences.",
  "response_a": "Photosynthesis converts light energy into chemical energy stored in glucose. Plants use chlorophyll to capture sunlight, taking in CO₂ and water to produce glucose and oxygen.",
  "response_b": "Photosynthesis is when plants make food. Plants need sun to do photosynthesis.",
  "picked": "a",
  "rationale": "A is more thorough."
}
```

**Expected output:**

```json
{
  "rationale_validity": "weak",
  "evidence_from_rationale": "A is more thorough.",
  "evidence_from_chosen": "A is indeed more thorough — it names the energy conversion, the biology (chlorophyll), the inputs (CO2, water), and outputs (glucose, oxygen). But the rationale word 'thorough' undersells the actual difference: A is correct and educational, B is vague and barely mentions the mechanism.",
  "label_confidence": "medium",
  "recommendation": "keep",
  "decision_basis": "Rationale is too vague but the pick is correct; label kept but rationale re-write would be useful for training signal quality."
}
```

## Failure Modes

- **Generic-rationale pass-through** — rationale "A is better" gets
  marked "supports" because A IS better. The validity check is
  about the **rationale**, not the **pick**. Audit by sampling
  outputs labeled "supports" with very short rationales.
- **Strict on adequate rationales** — "A is more thorough" is weak
  but functional; flagging every short rationale as "weak" would
  block too much. Calibrate: weak = signal-poor, not just short.
- **Confusing the judge with the labeler** — model judges whether
  IT thinks the pick is right, not whether the rationale supports
  the labeler's pick. Reread prompt: this card is about rationale-
  pick coherence, not about whether the pick is "correct".
- **Drop-recommendation over-trigger** — dropping all weak labels
  loses signal. Track recommendation distribution; "drop" should
  be reserved for clearly-wrong rationales (contradicts type).

## Tuning Notes

- 模型差异：frontier 模型必须的——需要同时 evaluate rationale
  quality + check rationale claim against actual response.
- 温度：`0.0`。
- 数据集 audit pipeline：跑全部 RLHF preference 数据通过本卡，
  contradicts + generic 的 label 进 re-label queue. 比例越高数据
  质量越差。健康数据集 contradicts <2%, generic <15%.
- 与 `rlhf/pairwise-preference-labeler` 的关系：那张卡是**生成**
  preference label 的卡；本卡是**审计**生成的 label 是否合理的卡。
  标 + 审计循环。
- 与 `rlhf/persona-consistency-judge` 的关系：那张卡审 response 是否
  符合 persona; 本卡审 label 是否合理。两个不同审计维度。
- 用法定位：本卡设计为 audit tool, 不应当作训练信号本身。它的输出
  用来过滤 / 重做数据, 而不是直接喂训练。
- 跨 annotator 对比：同一对 pair 多个 annotator 的 rationale 都跑
  本卡, label_confidence 集中度低 = annotators 在这个 pair 上判断
  不一致, 是 ambiguous case 的早期信号.

## Changelog

- `0.1.0` — Initial card.
