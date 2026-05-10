---
id: multimodal/image-classification
title: Custom-Category Image Classification
version: 0.1.0
status: stable
direction: multimodal
tags: [vision, classification, structured-output]
audience: [app-builder, eval-team, llm-trainer]
models: [vision-language, frontier-closed]
language: en
input_schema: multimodal
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: image
    description: The image to classify.
    required: true
  - name: categories
    description: A JSON array of category objects, each with `name` and `description`. Typical 2-10 categories.
    required: true
  - name: classification_mode
    description: One of "single_label" (image fits exactly one category) or "multi_label" (image may fit several).
    required: true
---

> 🎯 **场景**：把图片分到自定义类别——产品分类、内容审核、UGC 标签、客服图文 routing。比 zero-shot CLIP 灵活：分类描述可任意写，也能输出"哪都不属于"。需要 vision 模型。

## Quick Use

**Use when:** You want to classify images into your own custom categories (not a fixed pretrained label set) — content moderation, product catalog tagging, support-ticket image routing.
**Fill in:** `{{image}}` = the image; `{{categories}}` = JSON array of {name, description}; `{{classification_mode}}` = `single_label` or `multi_label`.
**You'll get:** Predicted categories with confidence, reasoning, and an "other" flag if no category fits. Output is JSON. Requires a vision-language model.

## Purpose

Classify an image into user-defined categories. The categories are
described in natural language, allowing arbitrary domain-specific
labels (vs. pretrained image classifiers that have fixed labels).
Used in production routing (which support team handles this image),
content moderation (does the image fit allowed categories), and
catalog tagging (what tags should this product image carry).
Output is structured so confidences can drive automation thresholds.

## Prompt

```text
You classify an image into user-defined categories.

Image: {{image}}

Categories:
{{categories}}

Classification mode: {{classification_mode}}

Steps:
1. Look at the image and consider each category's description.
2. For each category, score 1-5 fit (5 = clearly fits, 1 = clearly
   doesn't fit).
3. Mode-specific output:
   - "single_label" : Pick the single highest-scoring category. If
                       max score is ≤2, set "fits_any: false" and
                       no category is selected.
   - "multi_label"  : List all categories with score ≥4. If none,
                       set "fits_any: false".
4. For each predicted category, provide confidence:
   - "high"   = score 5 with clear visual evidence
   - "medium" = score 4 OR score 5 with some ambiguity
   - "low"    = anything below

5. List the visual features that drove the classification.

Return ONLY this JSON object:
{
  "predicted_categories": [
    {"name": "<category name>", "score": 1-5, "confidence": "high" | "medium" | "low", "visual_evidence": "<short>"}
  ],
  "fits_any": true | false,
  "category_scores": {
    "<category name>": 1-5
  },
  "would_route_to": "<category name OR 'review' if fits_any=false OR score is low>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
image: <photo of a damaged product (cracked phone screen)>
categories: [
  {"name": "warranty_claim", "description": "Image shows a damaged or defective product purchased from us, suitable for warranty handling."},
  {"name": "shipping_damage", "description": "Image shows damage that appears to have happened during shipping (crushed box, broken-in-transit goods)."},
  {"name": "user_misuse", "description": "Image shows damage clearly caused by user error (water damage, dropped damage)."},
  {"name": "not_a_product_image", "description": "Image is not a photo of a product at all (selfie, screenshot, random)."}
]
classification_mode: "single_label"
```

**Expected output:**

```json
{
  "predicted_categories": [
    {"name": "user_misuse", "score": 4, "confidence": "medium", "visual_evidence": "Cracked phone screen with impact pattern consistent with a drop; no signs of shipping packaging damage or factory defect."}
  ],
  "fits_any": true,
  "category_scores": {
    "warranty_claim": 2,
    "shipping_damage": 2,
    "user_misuse": 4,
    "not_a_product_image": 1
  },
  "would_route_to": "user_misuse",
  "decision_basis": "Crack pattern points to drop damage rather than shipping or factory defect; routed to user_misuse for review."
}
```

## Failure Modes

- **Forced classification** — model picks a category even when none
  fit. The `fits_any: false` path exists; verify outputs with low
  scores actually trigger it.
- **Description ignored** — model classifies on label name only,
  not description. Sample outputs and check `visual_evidence`
  references the description's specific features.
- **Confidence inflation** — every prediction "high" confidence.
  Track distribution; expect 30/50/20 high/medium/low on diverse
  inputs.
- **Hallucinated visual evidence** — `visual_evidence` describes
  features not in the image. Audit by sampling and checking against
  image.
- **Single-label split** — in single_label mode, model returns
  multiple predictions. Validate at parse time.

## Tuning Notes

- 模型差异：strong VLM 必须的。中档 VLM 在 description-following 上
  弱——更倾向于按 label name 匹配而忽略 description 中的具体条件。
- 温度：`0.0`，classification 必须可重现。
- categories 数量：2-10 是甜点。1 退化为二分类（可以但不如直接问
  "is this X yes/no"）；>10 模型 attention 分散且无 fits_any 也容易
  随便选。
- categories 描述写法：**视觉化**优于抽象。"image shows shipping
  damage (crushed box, torn tape)" 强于 "shipping damage"。前者让
  模型有具体视觉特征对照。
- 与 `multimodal/structured-caption-generator` 的关系：caption 卡
  描述任意图；本卡分到自定义 label。caption 适合 catalog indexing,
  本卡适合 routing / moderation.
- 与 `eval/safety-output-classifier` 的关系：那张卡分类**文本输出**
  for harm；本卡分类**图像** into 任意 categories。安全 case 上可
  叠加：content moderation = image classify (本卡) + text classify
  (那张卡).
- routing 阈值：confidence=high 自动化；medium 加人工 review；low
  默认进 review queue。具体阈值按业务调。

## Changelog

- `0.1.0` — Initial card.
