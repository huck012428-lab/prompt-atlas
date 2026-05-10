---
id: multimodal/structured-caption-generator
title: Structured Image Caption Generator
version: 0.1.0
status: stable
direction: multimodal
tags: [vision, image-description, generation, structured-output, extraction]
audience: [app-builder, eval-team, llm-trainer]
models: [vision-language, frontier-closed]
language: en
input_schema: multimodal
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: image
    description: The image to describe (passed as an image input to the VLM).
    required: true
  - name: focus_hint
    description: Optional one-line hint about what aspect to emphasize (e.g. accessibility alt-text, product catalog, content moderation). Pass empty string for general-purpose captioning.
    required: false
---

## Quick Use

**Use when:** You want a structured caption for an image — discrete fields like scene, subject, objects, action — instead of free-form text.
**Fill in:** `{{image}}` = the image; `{{focus_hint}}` = optional one-line hint about what to emphasize (alt-text, product catalog, moderation, etc.).
**You'll get:** Structured fields (scene_type, primary_subject, objects, salient text, uncertain elements) plus a one-paragraph caption_summary. Output is JSON. Requires a vision-language model.

## Purpose

Produce a structured caption for an image — discrete fields for scene,
salient objects, action, setting, and uncertain elements — instead of a
single free-text paragraph. Used when downstream consumers need to
filter, search, or aggregate by specific attributes (alt-text systems,
product catalogs, content review pipelines, dataset labeling) and
free-text captions are too unstructured to process. Output is JSON so
each field can be validated and indexed independently.

This is the **generator counterpart** to
`multimodal/vlm-image-description-verifier`, which audits whether a
candidate description matches an image. The two are designed to
work together in caption pipelines.

## Prompt

```text
You are a structured image caption generator. Look at the image and
fill out the schema below. Be specific where the image supports it,
and explicit about uncertainty where it does not.

Image: {{image}}

Optional focus hint (may be empty):
{{focus_hint}}

Rules:
1. Only include facts the image directly supports. Do NOT infer
   intent, mood, or off-frame context unless the focus_hint asks for it.
2. List uncertain elements separately rather than mentioning them in
   the main fields. "I think it might be a..." belongs in
   uncertain_elements, not in objects.
3. Adjust verbosity to the focus_hint when present (e.g. accessibility
   alt-text expects 1-2 sentence caption_summary, no objects array).
4. Skip non-applicable fields with "" or [] rather than fabricating.

Return ONLY this JSON object:
{
  "scene_type": "<short phrase: indoor / outdoor / studio / illustration / chart / screenshot / other-with-detail>",
  "primary_subject": "<the main subject of the image, in one short phrase>",
  "objects": ["<distinct visible object/entity 1>", "<2>", "<3>"],
  "action_or_state": "<what is happening or the static scene state, in one phrase>",
  "setting": "<where the scene takes place, in one phrase>",
  "salient_text_in_image": "<verbatim text visible in the image (signs, captions, UI text), or empty string>",
  "caption_summary": "<one or two sentences synthesizing the above for human readers>",
  "uncertain_elements": ["<thing you cannot confirm 1>", "<2>"],
  "decision_basis": "<one sentence, <=30 words, explaining what was easy and what was uncertain about this image>"
}
```

## Example

**Input:**

```text
image: <photo of a brown labrador sitting on a wooden porch at sunset, with a dog leash visible on the floor next to it>
focus_hint: ""
```

**Expected output:**

```json
{
  "scene_type": "outdoor",
  "primary_subject": "brown labrador dog",
  "objects": ["brown labrador", "wooden porch", "leash", "sunset sky"],
  "action_or_state": "the dog is sitting upright",
  "setting": "wooden porch at sunset",
  "salient_text_in_image": "",
  "caption_summary": "A brown labrador sits on a wooden porch at sunset, with a leash on the floor beside it.",
  "uncertain_elements": ["whether the dog is waiting for a walk or just resting", "the exact location"],
  "decision_basis": "Composition and subject are clear; intent and location are not visible from the image alone."
}
```

## Failure Modes

- **Inferred-fact bleed** — model puts intent / mood ("the dog looks
  excited", "a peaceful evening scene") into `objects` or
  `action_or_state` instead of treating these as inferred. Mitigation:
  rule 1 explicit; verify by spot-checking that objects are
  physically visible and not subjective qualities.
- **OCR error in salient_text_in_image** — the verbatim text field
  is wrong, especially for stylized fonts or low-res images.
  Mitigation: pass an OCR pre-pass for high-stakes captioning; treat
  this field as best-effort.
- **Object list bloat** — model lists 15 objects including background
  pixels (sky, ground, wall) that add no information. Cap at the top
  5-7 distinct entities; reject lists where most items are background
  surfaces.
- **Missed primary subject** — for cluttered scenes, the model
  picks an arbitrary object as `primary_subject`. Detect by sampling
  outputs where `primary_subject` is not also the first item in
  `objects`.
- **Hallucinated uncertain_elements** — model lists items in
  `uncertain_elements` that the image does not contain at all
  (e.g. "uncertain whether there is a person, but I don't see one").
  This field is for things that are visible but ambiguous, not for
  imagined scenarios.
- **Focus hint mis-application** — when `focus_hint: "alt-text"` is
  set, model still produces full schema. Mitigation: explicit
  conditional logic in rule 3; consider a separate alt-text-only
  variant card if this fails frequently.

## Tuning Notes

- 模型差异：必须 vision-language 模型（GPT-4V / Claude Vision /
  Gemini Pro Vision）。强 VLM 在 inferred-fact bleed 和 hallucinated
  elements 上表现明显更稳；弱 VLM 倾向于"诗意化"图像描述。
- 温度：`0.0`–`0.3`。captioning 的稳定性比创造性重要，特别是用作
  检索索引时。
- 与 `multimodal/vlm-image-description-verifier` 的关系：本卡是 generator，
  verifier 卡是 auditor。生产中两者可以串联：generator 出 caption →
  verifier 跑回原图核对 → reject hallucination 高的 caption。
- 与 `multimodal/vqa-with-confidence` 的关系：本卡是无问题的全图
  描述；VQA 是针对特定问题的回答。如果你的下游需要的是"针对每张图
  的固定问题集"答案，用 VQA；如果是"通用描述并 indexing"，用本卡。
- focus_hint 的实践：accessibility alt-text、product catalog、
  moderation 三种场景对 caption 的需求差异很大。生产建议：每种
  场景用不同的 focus_hint，且收集 100 个人工 gold 样本评估字段
  fidelity。
- 用作训练数据：本卡产出可以作为 VLM SFT 的 caption 监督信号；建议
  搭配 verifier 过滤 hallucination 率 > 30% 的样本。

## Changelog

- `0.1.0` — Initial card.
