---
id: multimodal/image-comparison-explainer
title: Image Pair Comparison Explainer
version: 0.1.0
status: stable
direction: multimodal
tags: [vision, comparative, structured-output]
audience: [eval-team, app-builder, ai-pm]
models: [vision-language, frontier-closed]
language: en
input_schema: multimodal
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: image_a
    description: First image.
    required: true
  - name: image_b
    description: Second image.
    required: true
  - name: comparison_focus
    description: One of "general" (full comparison), "difference_only" (focus on what differs), "similarity_only" (focus on what's shared), "category" (compare on a specific axis like colors / objects / mood).
    required: true
---

> 🎯 **场景**：解释两张图的相似 / 差异——A/B 测试的视觉对比、UI 改版前后说明、产品图片对照、训练数据 augmentation 检查。需要 vision 模型。比单图描述更聚焦在"两图之间的关系"。

## Quick Use

**Use when:** You have two images and want a structured explanation of their similarities and/or differences (UI A/B comparison, product photo comparison, design variant analysis).
**Fill in:** `{{image_a}}` and `{{image_b}}` = the two images; `{{comparison_focus}}` = `general` / `difference_only` / `similarity_only` / `category`.
**You'll get:** Categorized similarities and differences, an overall comparison summary, and visual-evidence references. Output is JSON. Requires a vision-language model.

## Purpose

Explain how two images compare on multiple dimensions: subject,
composition, color/lighting, style, mood. Used in design A/B tests,
product photo comparison, UI change documentation, training-data
verification. Output structured so similarities and differences can
be filtered separately.

## Prompt

```text
You explain how two images compare.

Image A: {{image_a}}
Image B: {{image_b}}

Comparison focus: {{comparison_focus}}

Steps:
1. Compare on dimensions: subject, composition, color, lighting,
   style, mood, salient text/elements.

2. For each dimension where there's a meaningful similarity OR
   difference (per the focus), record:
   - dimension name
   - relation: "same" / "similar" / "different" / "opposite"
   - description (short)
   - which image (a / b / both)

3. If focus is "category", restrict comparison to the named
   category.

4. Compute "overall_similarity" rough score 1-5:
   1 = unrelated images
   3 = different subjects / scenes but related domain
   5 = visually near-identical

Return ONLY this JSON object:
{
  "dimension_comparisons": [
    {"dimension": "<name>", "relation": "same" | "similar" | "different" | "opposite",
     "description": "<short>", "evidence_a": "<short>", "evidence_b": "<short>"}
  ],
  "key_similarities": ["<short>"],
  "key_differences": ["<short>"],
  "overall_similarity": 1-5,
  "summary": "<one or two sentences>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

A: photo of a cat on a sofa. B: photo of a different cat on a different
sofa.

**Expected output:**

```json
{
  "dimension_comparisons": [
    {"dimension": "subject", "relation": "similar", "description": "Both show a domestic cat resting on a piece of upholstered furniture.", "evidence_a": "tabby cat on grey fabric sofa", "evidence_b": "black cat on brown leather sofa"},
    {"dimension": "color", "relation": "different", "description": "A has cool grey palette; B has warm brown palette.", "evidence_a": "grey sofa, neutral lighting", "evidence_b": "brown sofa, warm-tone lighting"},
    {"dimension": "composition", "relation": "similar", "description": "Both medium-shot, animal centered.", "evidence_a": "cat in middle frame", "evidence_b": "cat slightly right of center"}
  ],
  "key_similarities": ["Domestic cat as subject", "Sofa as setting", "Medium-shot composition"],
  "key_differences": ["Cat color (tabby vs black)", "Color palette (cool vs warm)", "Sofa material (fabric vs leather)"],
  "overall_similarity": 3,
  "summary": "Both are 'cat on sofa' photos in similar composition; differ in subject specifics (cat color, sofa material) and overall color palette.",
  "decision_basis": "Same subject category and composition, different specific instances and palettes; mid-similarity (3/5)."
}
```

## Failure Modes

- **Hallucinated differences** — model claims a difference that
  isn't there. Cross-check evidence_a and evidence_b on samples.
- **Missed differences** — focuses on similarities and misses
  obvious diffs. Check key_differences count on benchmark with
  known-different pairs.
- **Score inflation** — every pair gets 4-5. Track distribution.
- **Focus ignored** — model produces general comparison when focus
  was "difference_only". Verify dimension_comparisons aligns with
  focus.

## Tuning Notes

- 模型差异：strong VLM 必须的。
- 温度：`0.0`–`0.2`。
- 与 `multimodal/image-edit-instruction-generator` 的对比：那张卡用
  before/after 反向生成 instruction；本卡用 A/B 解释关系。前者用于
  edit-model 数据建设，后者用于 design comparison 文档。
- 与 `multimodal/vlm-image-description-verifier` 的关系：verifier 审
  caption 与图匹配；本卡比较两图。互补。
- comparison_focus 选择：UI A/B 用 "difference_only"；类别归类用
  "similarity_only"；产品对比用 "category" 指定具体轴。
- 用作 dataset deduplication：在视觉数据集上跑 pairwise，high
  overall_similarity 的对作为重复候选送人工 review。

## Changelog

- `0.1.0` — Initial card.
