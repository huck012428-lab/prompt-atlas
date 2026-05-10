---
id: multimodal/handwriting-transcriber
title: Handwriting Transcriber with Per-Word Confidence
version: 0.1.0
status: experimental
direction: multimodal
tags: [vision, ocr, extraction, structured-output]
audience: [app-builder, eval-team, ai-pm]
models: [vision-language, frontier-closed]
language: en
input_schema: multimodal
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: image
    description: An image containing handwritten text — notes, forms, whiteboard photos, signatures.
    required: true
  - name: language_hint
    description: Expected language of the handwriting (e.g. "English", "中文", "Japanese", "mixed English / Chinese"). Pass empty string if unknown.
    required: false
---

> 🎯 **场景**：手写文字转录 + per-word 置信度。比 generic OCR 适合 handwriting 的难处理特征：连笔、个性化字形、模糊、混合语言。每个 word 标置信度，供下游决定要不要复核。

## Quick Use

**Use when:** You have an image of handwritten text (notes, forms, whiteboard, captured letters) and want a transcription with per-word confidence so downstream code can flag words for review.
**Fill in:** `{{image}}` = the handwritten image; `{{language_hint}}` = expected language(s) or empty.
**You'll get:** Transcribed text, per-word confidence, hard-to-read regions list, and an overall reliability flag. Output is JSON. Requires a vision-language model.

## Purpose

Transcribe handwritten text from an image, with explicit per-word
confidence so callers can route uncertain words to human review.
Used in form-digitization workflows, note-archiving systems,
whiteboard-to-doc tools. Distinct from
`multimodal/ocr-structured-extraction` which handles printed
documents with known field schema; this card handles unstructured
handwritten content.

## Prompt

```text
You transcribe handwritten text. Per-word confidence is required
because handwriting recognition is inherently uncertain.

Image: {{image}}

Language hint (may be empty):
{{language_hint}}

Steps:
1. Transcribe the visible handwritten text. Preserve line breaks
   and spatial layout where meaningful (e.g. lists, paragraph
   breaks).

2. For each word, label confidence:
   - "high"      : Clearly legible.
   - "medium"    : Legible but stylized or partially occluded;
                    you're confident.
   - "low"       : Significant ambiguity; you have a guess but
                    other readings possible.
   - "uncertain" : You can identify there's a word but cannot
                    confidently transcribe it.

3. Capture per-word `position_hint` (line N, position M-th word in
   the line) so downstream can highlight specific words.

4. List "hard_to_read_regions" — areas of the image where text is
   present but transcription is unreliable (smudged, torn paper,
   shadow, low contrast).

5. Note any spatial / formatting features: "list with bullets",
   "indented quote", "diagram with text labels", etc.

Return ONLY this JSON object:
{
  "transcription": "<the full transcribed text with line breaks>",
  "words": [
    {"word": "<transcribed word>", "confidence": "high" | "medium" | "low" | "uncertain", "position_hint": "<line / position>"}
  ],
  "hard_to_read_regions": [
    {"description": "<short>", "approximate_location": "<short>"}
  ],
  "formatting_notes": "<short description of the handwritten content's structure>",
  "overall_reliability": "high" | "medium" | "low",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Overall reliability rule:
- "high"   = 90%+ words at high confidence, 0 uncertain.
- "medium" = mostly high/medium with <15% low, <5% uncertain.
- "low"    = significant low/uncertain words.
```

## Example

**Input:**

```text
image: <photo of a handwritten shopping list: "Milk\n2 eggs\nBread (whole grain)\nApples?? (forgot which kind)\nButter">
language_hint: "English"
```

**Expected output:**

```json
{
  "transcription": "Milk\n2 eggs\nBread (whole grain)\nApples?? (forgot which kind)\nButter",
  "words": [
    {"word": "Milk", "confidence": "high", "position_hint": "line 1, word 1"},
    {"word": "2", "confidence": "high", "position_hint": "line 2, word 1"},
    {"word": "eggs", "confidence": "high", "position_hint": "line 2, word 2"},
    {"word": "Bread", "confidence": "high", "position_hint": "line 3, word 1"},
    {"word": "(whole", "confidence": "high", "position_hint": "line 3, word 2"},
    {"word": "grain)", "confidence": "high", "position_hint": "line 3, word 3"},
    {"word": "Apples", "confidence": "medium", "position_hint": "line 4, word 1 — written with what looks like a question mark cluster"},
    {"word": "(forgot", "confidence": "high", "position_hint": "line 4, word 2"},
    {"word": "which", "confidence": "high", "position_hint": "line 4, word 3"},
    {"word": "kind)", "confidence": "high", "position_hint": "line 4, word 4"},
    {"word": "Butter", "confidence": "high", "position_hint": "line 5, word 1"}
  ],
  "hard_to_read_regions": [],
  "formatting_notes": "Vertical shopping list, one item per line, with parenthetical remarks for clarification.",
  "overall_reliability": "high",
  "decision_basis": "Clean handwriting, English shopping list; only minor uncertainty on 'Apples??' due to non-standard punctuation."
}
```

## Failure Modes

- **Confidence inflation** — model marks all words "high" even on
  difficult handwriting. Track confidence distribution; if "high"
  rate is >95% on a known-difficult sample, the calibration is too
  lax.
- **Best-guess silent transcription** — model transcribes uncertain
  words at "high" confidence rather than flagging. Mitigation:
  rule "uncertainty cluster lowers confidence"; sample 'high'
  outputs against ground truth.
- **Character-level error** — common confusions (l ↔ 1, O ↔ 0,
  rn ↔ m, cl ↔ d) silently slip through. For high-stakes (forms,
  legal handwritten notes), pair with human spot-check.
- **Language miscall** — Chinese handwriting transcribed as random
  English-looking words because language_hint was empty. Always pass
  language_hint when known.
- **Layout flattening** — transcription drops spatial structure
  (indentation, list nesting). Pre-warn that some structure may be
  lost; use formatting_notes to capture what was lost.

## Tuning Notes

- 模型差异：strong VLM 必须的。中档 VLM 在 cursive / non-Latin
  handwriting 上失败率高。Claude / Gemini Pro Vision / GPT-4V 大致
  相当；具体 case 上有差异，建议在你的实际样本分布上 small A/B。
- 温度：`0.0`。transcription 必须可重现。
- language_hint 至关重要：mixed-language handwriting 上 hint 让模型
  在 OOV 处不乱猜。
- 与 `multimodal/ocr-structured-extraction` 的关系：那张卡处理印刷
  document with schema (receipts, invoices, IDs)；本卡处理无 schema
  的 handwritten content。
- 与 `multimodal/document-layout-analyzer` 的关系：那张卡做版面识别；
  本卡做内容转录。手写文档建议先 layout-analyzer 找到 region，再用
  本卡转录每个 region。
- 用法：medium / low / uncertain words 应当走人工复核 queue。生产中
  典型 threshold：confidence != "high" 的样本不直接入数据库，进
  human-in-the-loop 系统。
- 高敏 use case（医疗手写处方、法律手写文件）：本卡是 first-pass，
  必须有人工 verification。仅靠 LLM 转录是不可靠的。

## Changelog

- `0.1.0` — Initial card.
