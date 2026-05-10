---
id: multimodal/ocr-structured-extraction
title: OCR + Structured Extraction from Document Images
version: 0.1.0
status: stable
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
    description: The document image (receipt, invoice, form, ID, screenshot) to extract from.
    required: true
  - name: target_fields
    description: A JSON array describing the fields to extract. Each item is an object with name (string), type (string, number, date, currency, boolean), required (boolean), description (string).
    required: true
  - name: document_type_hint
    description: One-line hint about the document type (e.g. US receipt, German invoice, passport ID page). Pass empty string if unknown.
    required: false
---

> 🎯 **场景**：从文档图（票据 / 发票 / 表单 / ID）按指定 schema 抽取类型化字段——不是裸 OCR，是 OCR + 结构化 + 类型转换。每个字段带置信度，trustworthy_for_automation 标记是否可放心自动化。需要 vision 模型。

## Quick Use

**Use when:** You want to extract a fixed set of typed fields from a document image (receipt, invoice, form, ID page).
**Fill in:** `{{image}}` = the document image; `{{target_fields}}` = JSON array describing the fields to extract (name, type, required, description); `{{document_type_hint}}` = optional locale or document-type hint.
**You'll get:** Each field with its typed value, per-field confidence, and notes; plus a `trustworthy_for_automation` flag. Output is JSON. Requires a vision-language model.

## Purpose

Extract a fixed set of named fields from a document image, returning
both the OCR text and a typed structured object. Used in receipt /
invoice / form / ID processing pipelines where downstream systems need
typed fields (numbers as numbers, dates as ISO-8601 dates, currency as
amount + symbol) rather than a wall of OCR text. Unlike a generic VLM
caption or VQA, this card commits to a target schema declared at call
time. Output is structured so missing fields and confidence per field
are surfaced rather than silently filled.

## Prompt

```text
You extract structured fields from a document image. Read the image,
then fill out the target schema. Use the schema to guide what to look
for; do NOT add fields beyond the schema.

Image: {{image}}

Target fields:
{{target_fields}}

Document type hint (may be empty):
{{document_type_hint}}

Rules:
1. For each target field: extract the value if present in the image,
   coerced to the requested type.
   - "string"   : verbatim text from the image, normalized for
                  trivial whitespace.
   - "number"   : numeric value as a JSON number.
   - "date"     : ISO-8601 (YYYY-MM-DD) when full; YYYY-MM if day
                  missing; YYYY if only year visible.
   - "currency" : object with {"amount": <number>, "currency": "<ISO 4217 code or symbol>"}.
   - "boolean"  : true / false.
2. If a field is required but cannot be located in the image, set
   `value: null`, `confidence: "low"`, and add a one-phrase note in
   `notes` explaining why.
3. If an optional field is not present, omit it from `extracted` (do
   not include null entries for missing optional fields).
4. Per-field confidence:
   - "high"   — value is clearly visible and unambiguous.
   - "medium" — value is visible but reading required interpretation
                (faded ink, partial occlusion, common OCR confusions).
   - "low"    — value is hard to read or inferred from context.

Return ONLY this JSON object:
{
  "extracted": {
    "<field_name>": {
      "value": <typed value or null>,
      "confidence": "high" | "medium" | "low",
      "notes": "<short note, or empty string>"
    }
    /* one entry per requested field that was extracted or marked null */
  },
  "raw_text_snippets": ["<verbatim text snippet 1 from image>", "<snippet 2>"],
  "completeness": {
    "required_fields_filled": <integer>,
    "required_fields_total": <integer>,
    "trustworthy_for_automation": true | false
  },
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Set "trustworthy_for_automation": true ONLY if every required field
has confidence "high" or "medium" AND required_fields_filled equals
required_fields_total.
```

## Example

**Input:**

```text
image: <photo of a US grocery receipt: "WHOLE FOODS MARKET, 03/14/2024, Apples $4.99, Bread $5.50, Subtotal $10.49, Tax $0.84, TOTAL $11.33">
target_fields: [
  {"name": "merchant", "type": "string", "required": true, "description": "Store or merchant name"},
  {"name": "date", "type": "date", "required": true, "description": "Transaction date"},
  {"name": "total_amount", "type": "currency", "required": true, "description": "Final total paid"},
  {"name": "tax_amount", "type": "currency", "required": false, "description": "Tax amount if shown"}
]
document_type_hint: "US grocery receipt"
```

**Expected output:**

```json
{
  "extracted": {
    "merchant": {"value": "Whole Foods Market", "confidence": "high", "notes": ""},
    "date": {"value": "2024-03-14", "confidence": "high", "notes": ""},
    "total_amount": {"value": {"amount": 11.33, "currency": "USD"}, "confidence": "high", "notes": "USD inferred from US-grocery hint and $ symbol"},
    "tax_amount": {"value": {"amount": 0.84, "currency": "USD"}, "confidence": "high", "notes": ""}
  },
  "raw_text_snippets": ["WHOLE FOODS MARKET", "03/14/2024", "TOTAL $11.33", "Tax $0.84"],
  "completeness": {
    "required_fields_filled": 3,
    "required_fields_total": 3,
    "trustworthy_for_automation": true
  },
  "decision_basis": "All required fields read clearly; date converted to ISO and currency resolved from US hint."
}
```

## Failure Modes

- **OCR confusion** — common errors (O ↔ 0, l ↔ 1, comma ↔ period in
  numbers, year-month-day order). Detect by sampling outputs where
  `confidence` is "high" but downstream validation rejects (e.g. amount
  doesn't sum). Mitigation: add a separate validator step that re-asks
  the model to verify suspicious extractions.
- **Hallucinated values for missing required fields** — model invents
  a plausible value rather than returning null. The rule explicitly
  forbids this; spot-check by hiding a required field in test images
  and verifying `value: null` and `confidence: "low"`.
- **Currency/locale drift** — model assumes USD when the image is in
  EUR or JPY. Mitigation: pass an explicit `document_type_hint` with
  country / currency expectation; fall back to symbol detection.
- **Date format ambiguity** — `03/04/2024` is March 4 in US format and
  April 3 in EU format. Mitigation: `document_type_hint` should
  include locale; if unspecified, model should mark `confidence:
  "medium"` and note the ambiguity.
- **Multi-page or multi-column documents** — extraction may grab
  fields from the wrong section (e.g. line items merged with totals).
  Mitigation: pre-process to crop to the relevant section, or use
  multiple calls with different document_type_hints.
- **Schema bleed** — model adds fields not in the target schema
  ("loyalty_card_number" appearing in `extracted` even though it
  wasn't requested). Reject extras at parse time.
- **trustworthy_for_automation inflation** — model marks true even
  when one required field has "low" confidence. Verify with the
  explicit rule logic at parse time, don't trust the field as-is.

## Tuning Notes

- 模型差异：必须 strong VLM（GPT-4V / Claude Vision / Gemini Pro
  Vision 等）。中档 VLM 在 OCR 准确度和 schema 遵循上同时退化，
  生产中不建议作为唯一抽取器。
- 温度：`0.0`，extraction 必须可重现。
- 与 `multimodal/structured-caption-generator` 的关系：caption-generator
  是无 schema 的全图描述（"图里有什么"）；本卡是有 schema 的针对性
  抽取（"图里**指定字段**的值是什么"）。前者用于 indexing / 描述；
  后者用于 ETL pipeline。
- 与 `multimodal/vqa-with-confidence` 的关系：VQA 是单问题问答；
  本卡是多字段批量抽取。如果你只需要 1-2 个字段，VQA 更轻量；
  如果需要 5+ 字段或固定 schema，本卡的 token 经济性更好。
- 高敏场景（医疗、金融、法律）：本卡的 `trustworthy_for_automation`
  字段是必要不充分条件。生产中应当：(1) 后接 deterministic 校验
  （sum 校验、format 校验、外部库查询）；(2) 对 `confidence: "medium"`
  以下的样本走人工复核 queue。
- 多 locale 支持：如果你的 pipeline 跨国，建议为每种 locale 维护一份
  document_type_hint 模板，效果显著优于让模型猜。
- 与传统 OCR + 后处理 pipeline 的关系：传统流水（Tesseract / Azure
  Document Intelligence）在已知文档类型上仍然更便宜更稳；本卡的
  优势在 unknown / mixed-format 文档和需要"读懂语义后再抽"的场景。

## Changelog

- `0.1.0` — Initial card.
