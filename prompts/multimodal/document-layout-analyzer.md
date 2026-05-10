---
id: multimodal/document-layout-analyzer
title: Document Layout Analyzer
version: 0.1.0
status: stable
direction: multimodal
tags: [vision, extraction, structured-output, vlm-eval]
audience: [app-builder, eval-team, ai-pm]
models: [vision-language, frontier-closed]
language: en
input_schema: multimodal
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: document_image
    description: An image of a document page (PDF page screenshot, scanned page, slide screenshot, web page screenshot).
    required: true
  - name: document_type_hint
    description: One-line hint about the document type (e.g. "academic paper page", "legal contract section", "presentation slide", "screenshot of a SaaS app dashboard"). Pass empty string if unknown.
    required: false
---

> 🎯 **场景**：分析文档页面的**版式结构**——识别 header / footer / 正文段落 / 表格 / 图片 / 列表 / 引用等区块及其阅读顺序。和 OCR 抽取互补——OCR 给字段值，本卡给"页面长什么样"。适合 PDF 拆分、内容审核、智能阅读流水。

## Quick Use

**Use when:** You want to understand a document page's STRUCTURE (where headers, body, tables, images live; what reading order is) — not extract specific fields.
**Fill in:** `{{document_image}}` = the page image; `{{document_type_hint}}` = optional one-line hint about the doc type.
**You'll get:** A list of identified regions with type, bounding-box-style location, and reading order; a hierarchy if applicable; and any flagged anomalies. Output is JSON. Requires a vision-language model.

## Purpose

Identify the structural regions of a document page — title,
section headers, body paragraphs, tables, figures, captions, lists,
footnotes, footers — along with their relative positions and the
reading order. Used in document-processing pipelines as the layer
that sits between raw OCR and content-level extraction: knowing
"this paragraph is a footnote, not body text" or "this image has a
caption below it" prevents downstream confusion. Distinct from
`multimodal/ocr-structured-extraction` (which extracts specific
typed fields) and `multimodal/structured-caption-generator` (which
describes images, not document pages).

## Prompt

```text
You analyze a document page's layout. Identify the structural regions
and their reading order. Do NOT transcribe full text — describe
structure.

Document image:
{{document_image}}

Document type hint (may be empty):
{{document_type_hint}}

Region types:
- "title"            : The document or page title.
- "section_header"   : A heading that introduces a section or
                       subsection.
- "body_paragraph"   : A standard paragraph of running text.
- "list"             : Bulleted or numbered list.
- "table"            : Tabular content with rows and columns.
- "figure"           : An image, chart, or diagram embedded in the
                       page (does NOT include the image's caption).
- "caption"          : A caption for an adjacent figure or table.
- "footnote"         : A footnote referenced from body text.
- "footer"           : Page-bottom content (page number, document
                       metadata).
- "header"           : Page-top content (running header, document
                       metadata).
- "sidebar"          : Side content (annotations, related links).
- "code_block"       : Monospace code or data, set off from body.
- "quote"            : A pulled quotation set off from body.
- "other"            : Doesn't match any of the above; describe in
                       region_subtype.

For each region:
- Identify a relative location: 9-grid (top-left/top-center/
  top-right/middle-left/middle-center/middle-right/bottom-left/
  bottom-center/bottom-right) plus an estimated rough size
  (small/medium/large/full-width).
- Identify reading order: 1-N integers, where 1 is what a human
  reader would read first. Don't worry about decorative elements
  (header, footer, sidebar) — give them order=null.

Return ONLY this JSON object:
{
  "regions": [
    {
      "id": "r1",
      "type": "<one of the region types>",
      "region_subtype": "<short clarifying label, especially for type=other; else empty>",
      "relative_location": "<9-grid label>",
      "estimated_size": "small" | "medium" | "large" | "full-width",
      "short_summary": "<1 phrase: what this region is/contains, no full transcription>",
      "reading_order": <integer or null>
    }
    /* one entry per identified region */
  ],
  "hierarchy": [
    {"parent_id": "<id>", "child_ids": ["<id>"], "relation": "contains" | "captions" | "footnotes"}
    /* zero or more relations; empty array if no hierarchy */
  ],
  "anomalies": ["<one short phrase per layout anomaly: e.g. 'caption appears above figure', 'footnote without referenced number'>"],
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
document_image: <screenshot of an academic paper page with title at top, two-column body, a figure with caption in the right column, footer with page number 3>
document_type_hint: "academic paper page"
```

**Expected output:**

```json
{
  "regions": [
    {"id": "r1", "type": "title", "region_subtype": "", "relative_location": "top-center", "estimated_size": "full-width", "short_summary": "Paper title and authors block.", "reading_order": 1},
    {"id": "r2", "type": "body_paragraph", "region_subtype": "introduction continuation", "relative_location": "middle-left", "estimated_size": "large", "short_summary": "First column of body text continuing introduction.", "reading_order": 2},
    {"id": "r3", "type": "body_paragraph", "region_subtype": "introduction continuation", "relative_location": "middle-right", "estimated_size": "medium", "short_summary": "Right column of body text, top half.", "reading_order": 3},
    {"id": "r4", "type": "figure", "region_subtype": "diagram", "relative_location": "middle-right", "estimated_size": "medium", "short_summary": "Diagram or chart embedded in right column.", "reading_order": 4},
    {"id": "r5", "type": "caption", "region_subtype": "figure caption", "relative_location": "middle-right", "estimated_size": "small", "short_summary": "Caption for the figure above.", "reading_order": 5},
    {"id": "r6", "type": "footer", "region_subtype": "page number", "relative_location": "bottom-center", "estimated_size": "small", "short_summary": "Page number 3.", "reading_order": null}
  ],
  "hierarchy": [
    {"parent_id": "r4", "child_ids": ["r5"], "relation": "captions"}
  ],
  "anomalies": [],
  "decision_basis": "Standard two-column academic page with title, continuing body across columns, and a captioned figure in the right column."
}
```

## Failure Modes

- **Reading order drift on multi-column layouts** — model reads
  left-to-right across columns instead of finishing left column
  first. The document_type_hint is a strong signal; if hint mentions
  multi-column types (academic paper, magazine), prompt biases
  toward column-major reading. Audit reading_order on multi-column
  samples specifically.
- **Caption / figure pairing failure** — model marks the caption but
  doesn't link it to the figure in `hierarchy`. Detect by sampling
  outputs that have a `caption` region but empty hierarchy; reject
  and re-prompt.
- **Sidebar vs body confusion** — model treats a sidebar as a
  separate body column. The document_type_hint is the main control
  here. For unknown types, the model may be wrong.
- **Hallucinated regions** — model lists a region that's not in the
  image (e.g. "footer" when the page has none). Verify by sampling
  and matching short_summary against visible content.
- **Missed regions** — small but important regions (footnotes,
  pull-quotes) not identified. Track expected-vs-found counts on a
  benchmark; if footnotes are missed >30% on docs known to have
  them, the rubric needs an explicit "scan for footnote markers"
  hint.
- **Region type miscategorization** — code blocks marked as body
  paragraphs (or vice versa). Add `code_block` examples in
  document_type_hint or few-shots if your domain has many.
- **Anomaly over-trigger** — every page generates "anomalies"
  entries because the model finds layouts unusual. Check that
  anomalies are actual structural oddities (caption-above-figure)
  not just unusual but valid (multi-language headers).

## Tuning Notes

- 模型差异：必须 strong VLM。中档 VLM 在多列阅读顺序和 figure-caption
  pairing 上失败率明显更高。
- 温度：`0.0`，layout 分析必须可重现。
- 与 `multimodal/ocr-structured-extraction` 的关系：OCR 是字段抽取
  （知道页面里有什么字段值）；本卡是结构识别（知道页面长什么样）。
  典型 pipeline：本卡先识别 region → 按 region 类型路由：body 区域
  跑全文 OCR，table 跑 chart-table-extractor，figure 跑
  structured-caption-generator。
- 与 `multimodal/structured-caption-generator` 的关系：那张卡描述
  **图片本身**；本卡描述**含图片的文档页面**的结构。文档处理流水里
  本卡先跑，识别到 figure region 后再调那张卡。
- 与 `multimodal/chart-table-extractor` 的关系：本卡识别哪一块是
  table；那张卡负责把 table 数据抽出来。pipe 起来。
- document_type_hint 至关重要：academic paper、legal contract、
  invoice、slide deck、web app screenshot 五类的最优解析策略不同。
  没有 hint 时模型默认用最 generic 假设，准确度低 20-30%。
- 高敏文档（合同、医疗报告）：本卡是**结构识别**，不替代法律 / 医疗
  专业判断。识别完结构后，每个 region 内部内容要走专业 verifier。
- 用作 PDF 处理 pipeline：本卡 → 按 region 类型分发到下游卡 → 整页
  reading_order 拼回完整文本流。比纯 OCR 整页一把抓质量高显著。

## Changelog

- `0.1.0` — Initial card.
