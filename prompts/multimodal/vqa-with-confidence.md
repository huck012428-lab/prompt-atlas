---
id: multimodal/vqa-with-confidence
title: Visual Question Answering with Grounding and Confidence
version: 0.1.0
status: stable
direction: multimodal
tags: [vision, vlm-eval, structured-output, factuality, scoring]
audience: [eval-team, app-builder, llm-trainer, ai-pm]
models: [vision-language, frontier-closed]
language: en
input_schema: multimodal
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: image
    description: The image the question is about (passed as image input to the VLM).
    required: true
  - name: question
    description: The question being asked about the image.
    required: true
---

> 🎯 **场景**：视觉问答 + grounding 区域 + 置信度。回答前先判断"图能不能答这个问题"，能答时指出图里哪一块支持答案、置信度多高。VQA benchmark + 票据问答 + 辅助阅读场景。需要 vision 模型。

## Quick Use

**Use when:** You want to answer a question about an image AND know whether the image actually supports the answer (with grounding region and confidence).
**Fill in:** `{{image}}` = the image; `{{question}}` = the question to answer.
**You'll get:** An answer (or `answerable_from_image: false`), the supporting region, salient features, and a high/medium/low confidence. Output is JSON. Requires a vision-language model.

## Purpose

Answer a question about an image and report whether the image actually
supports the answer, where in the image the support comes from, and
the model's confidence. Used in VLM evaluation pipelines that need to
distinguish "answered correctly" from "answered confidently from
nothing", and in production when a downstream system must decide
whether to trust the answer (e.g. invoice/receipt extraction, medical
imaging assistance, accessibility tools). Output is structured so per-
question correctness and confidence calibration can be tracked.

## Prompt

```text
You answer a question about an image. Report your answer, where in
the image the support is, and how confident you are.

Image: {{image}}

Question:
{{question}}

Steps:
1. Decide whether the image actually contains the information needed
   to answer this question.
2. If yes, answer concisely (1 to 20 words). If no, say so explicitly
   rather than guessing.
3. Locate the visual support — name the region or feature in the
   image that justifies the answer.
4. Report your confidence on a 3-level scale:
   - "high"   — the image clearly and unambiguously supports the answer.
   - "medium" — the image supports the answer but reading it required
                some interpretation.
   - "low"    — the image weakly supports the answer; you are mostly
                guessing.

Return ONLY this JSON object:
{
  "answerable_from_image": true | false,
  "answer": "<short answer text, or empty string if answerable_from_image=false>",
  "grounding": {
    "region_description": "<which part of the image supports the answer, in one short phrase; empty if answerable_from_image=false>",
    "salient_features": ["<concrete visible feature 1>", "<feature 2>"]
  },
  "confidence": "high" | "medium" | "low",
  "reason_unanswerable": "<if answerable_from_image=false: why the image cannot answer this; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Rules:
- Do NOT invent facts you cannot see. If the question asks about a
  person's name, intent, or off-frame context, that is usually
  unanswerable from the image alone.
- Do NOT mark "high" confidence on inferences (mood, age, occupation,
  brand). Reserve "high" for directly visible facts.
- Counting questions: if you can verify by visible separation,
  confidence may be "high"; if items overlap or are partial,
  downgrade to "medium" or "low".
```

## Example

**Input:**

```text
image: <photo of a kitchen counter with three apples, two bananas, and an orange in a bowl>
question: "How many pieces of fruit are in the bowl?"
```

**Expected output:**

```json
{
  "answerable_from_image": true,
  "answer": "Six",
  "grounding": {
    "region_description": "the fruit bowl on the kitchen counter",
    "salient_features": ["three apples", "two bananas", "one orange"]
  },
  "confidence": "high",
  "reason_unanswerable": "",
  "decision_basis": "All six pieces are individually distinguishable in the bowl with no occlusion."
}
```

## Failure Modes

- **Confident hallucination** — model answers a question whose answer
  is not actually in the image, with `confidence: "high"`. Detect by
  sampling high-confidence answers and re-asking with the image
  removed; if the model gives the same answer, it was guessing from
  priors. Mitigation: rule "do NOT invent facts" + audit
  high-confidence samples.
- **Refusal-as-unanswerable** — model marks every borderline case as
  `answerable_from_image: false` to avoid risk, hurting useful
  coverage. Track `answerable_from_image: false` rate; if higher than
  expected (e.g. >25% on benign VQA benchmarks), the model is being
  overly cautious — soften the unanswerable bar.
- **Off-frame inference** — model assumes context outside the image
  (location, time of day, country) and answers from priors.
  Mitigation: rule "off-frame context is usually unanswerable"; in
  audits, check that `salient_features` only mention visible items.
- **Counting bias** — VLMs systematically miscounting (off-by-one or
  off-by-many) on cluttered scenes. Don't trust `confidence: "high"`
  on counting questions when items > 8 or items overlap; downgrade
  through prompt engineering or skip these for high-stakes use.
- **OCR-dependent questions** — when the question requires reading
  text in the image, accuracy depends on OCR quality. Confidence can
  mislead — VLM may be confident in a misread number. Mitigation: for
  text-heavy images, pre-process with a dedicated OCR step.
- **Confidence flatness** — model marks every answer "high" or every
  answer "medium". Track distribution; if entropy is low across a
  diverse set, calibration is broken — add few-shots showing each
  level.

## Tuning Notes

- 模型差异：strong VLM 必须的（GPT-4V / Claude Vision / Gemini Pro
  Vision）。弱 VLM 在 grounding 字段上极不稳——经常 hallucinate
  region descriptions。
- 温度：`0.0`，VQA 必须可重现。
- 与 `multimodal/vlm-image-description-verifier` 的关系：verifier 卡
  审 caption 是否匹配图像（caption-image alignment）；本卡是给
  question 找 image 中的 answer + grounding。两者解决相邻但不同的
  问题，不能互相替代。
- 与 `multimodal/structured-caption-generator` 的关系：caption 是无
  question 的全图描述；本卡是有 question 的针对性回答。如果下游需要
  做 N 个固定问题的 VQA eval，用本卡批量；如果只需要可索引 caption，
  用 caption generator。
- 用作 benchmark：跑标准 VQA 数据集（VQAv2、GQA、TextVQA）时，本卡的
  `answer` 字段对照 gold answer，`confidence` 用于 calibration plot。
  期望 high-confidence 样本 accuracy > 90%，medium > 70%，low ~
  random 基线。偏离即是模型 calibration 问题。
- 高敏场景（医疗、法律、安全）：confidence: "high" 仅作为允许下游
  使用的必要条件，不充分；务必再加人工核查或多模型一致性。
- counting 类问题：建议在 prompt 之外加专门的 detection-then-count
  pipeline，VQA 在数量大或遮挡多时不稳。

## Changelog

- `0.1.0` — Initial card.
