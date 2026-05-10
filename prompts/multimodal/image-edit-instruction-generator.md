---
id: multimodal/image-edit-instruction-generator
title: Image Edit Instruction Generator (before/after to instruction)
version: 0.1.0
status: experimental
direction: multimodal
tags: [vision, generation, structured-output]
audience: [app-builder, eval-team, llm-trainer]
models: [vision-language, frontier-closed]
language: en
input_schema: multimodal
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: before_image
    description: The original image before editing.
    required: true
  - name: after_image
    description: The image after editing.
    required: true
  - name: instruction_style
    description: One of "natural" (how a user would describe the edit), "technical" (Photoshop-style with specific operations), "minimal" (shortest possible).
    required: true
---

> 🎯 **场景**：给两张前后对比图，反向生成"如何从 before 到 after"的编辑指令。用于训练 image-editing 模型的 SFT 数据建设、Photoshop 操作教学、design 版本对比说明。需要 vision 模型。

## Quick Use

**Use when:** You have a before/after image pair and want to generate the natural-language edit instruction that would produce the change — for image-edit-model training data, design diffs, or tutorial generation.
**Fill in:** `{{before_image}}` = original; `{{after_image}}` = edited; `{{instruction_style}}` = `natural` / `technical` / `minimal`.
**You'll get:** The edit instruction in the requested style, list of detected changes, and complexity rating. Output is JSON. Requires a vision-language model.

## Purpose

Reverse-engineer the edit instruction from a before/after image
pair. Used in training data construction for image-editing models
(e.g. InstructPix2Pix-style), design version comparison documentation,
and tutorial generation. Output structured so simple vs complex edits
can be sorted, and so the same pair can yield instructions in multiple
styles.

## Prompt

```text
You analyze a before/after image pair and generate an edit instruction
that would produce the change.

Before image: {{before_image}}
After image:  {{after_image}}

Instruction style: {{instruction_style}}

Style meanings:
- "natural"   : How a user would describe the edit ("make the sky
                 sunset", "add a hat on the dog").
- "technical" : Photoshop / image-editor terminology ("apply
                 gaussian blur radius 5px", "increase saturation
                 +30").
- "minimal"   : Shortest unambiguous instruction.

Steps:
1. Identify what changed. Compare globally then per-region.
2. Categorize the changes:
   - "object_added"      : New object/element in after.
   - "object_removed"    : Object/element in before but not after.
   - "object_modified"   : Object present in both, attributes changed.
   - "color_or_lighting" : Color / saturation / brightness / shadow
                            changes, no object change.
   - "geometric"         : Crop / resize / rotate / perspective.
   - "style_or_filter"   : Artistic style change (e.g. photo →
                            painting).
   - "background_only"   : Background changed, foreground same.

3. Generate the instruction in the requested style.

4. Rate complexity: "simple" (1-2 changes, 1 type) / "compound"
   (multiple changes coordinated) / "complex" (many changes, hard
   to articulate fully).

Return ONLY this JSON object:
{
  "detected_changes": [
    {"category": "<from list>", "description": "<short>"}
  ],
  "instruction": "<the generated instruction in requested style>",
  "alternative_instruction_minimal": "<the same edit in minimal style for reference>",
  "complexity": "simple" | "compound" | "complex",
  "ambiguity_note": "<if change could be described multiple equally-valid ways>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

Before: photo of a dog. After: same photo, dog is wearing a red bow tie.

**Expected output:**

```json
{
  "detected_changes": [
    {"category": "object_added", "description": "Red bow tie added on the dog's neck."}
  ],
  "instruction": "Add a red bow tie on the dog.",
  "alternative_instruction_minimal": "Add a red bow tie.",
  "complexity": "simple",
  "ambiguity_note": "",
  "decision_basis": "Single object addition, clearly identifiable; instruction is unambiguous."
}
```

## Failure Modes

- **Phantom changes** — model claims a change that isn't actually
  present. Validate by carefully comparing before/after; don't
  trust the model's claims uncritically.
- **Missed subtle changes** — changes in lighting / minor color
  shifts not detected. Sample edge cases.
- **Style drift** — `natural` style outputs Photoshop language or
  vice versa. Sample by style and verify match.
- **Compound under-detection** — multi-change edit collapsed to one
  description. Check detected_changes list size on known compound
  edits.
- **Position / size hallucination** — model says "moved the dog to
  the left" when dog stayed in place but background shifted.
  Spatial changes are hard; mark high complexity.

## Tuning Notes

- 模型差异：strong VLM 必须的。中档 VLM 在精细 color / lighting
  changes 上失败率高。
- 温度：`0.0`–`0.3`。
- 与 `multimodal/vlm-image-description-verifier` 的关系：那张卡审
  caption 是否匹配图；本卡审两图差异。语义不同。
- 与 `multimodal/structured-caption-generator` 的关系：那张卡描述单
  图；本卡比较两图。
- 用作 image-edit 模型 SFT 数据：(before_image, instruction,
  after_image) 三元组就是 training pair，本卡产 instruction。建议
  跑前用 image-similarity 先粗筛"有显著差异"的对，否则会产生大量
  trivial instructions。
- 高分辨率 + 同源拍摄敏感：训练数据要求两图除编辑外完全一致；不同
  曝光 / 不同角度 / 不同压缩 artifact 会让 instruction 含噪声。

## Changelog

- `0.1.0` — Initial card.
