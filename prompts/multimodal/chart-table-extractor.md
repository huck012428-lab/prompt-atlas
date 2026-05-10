---
id: multimodal/chart-table-extractor
title: Chart and Table Extractor
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
  - name: image
    description: An image containing a chart, plot, or table to extract data from.
    required: true
  - name: chart_type_hint
    description: Optional one-line hint about the chart type (e.g. "bar chart", "line plot", "pivot table", "stacked area"). Pass empty string to let the model classify.
    required: false
---

## Quick Use

**Use when:** You have an image of a chart, plot, or table (e.g. from a paper, dashboard screenshot, slide deck) and want the data as a structured object.
**Fill in:** `{{image}}` = the chart/table image; `{{chart_type_hint}}` = optional hint about the chart type (or empty to classify).
**You'll get:** Detected chart type, axes / column labels, the data series or table rows as JSON, and per-cell confidence. Output is JSON. Requires a vision-language model.

## Purpose

Extract structured data from an image of a chart, plot, or table —
the kind of image you screenshot from a dashboard, paste from a
research paper, or save from a presentation. Returns the chart type,
the axis or column labels, and the data series in a normalized JSON
form, along with per-data-point confidence so downstream code can
filter unreliable extractions. Distinct from
`multimodal/ocr-structured-extraction` (which targets documents with
known field schemas like receipts) — this card targets visualizations
where the structure is encoded graphically rather than as labeled
fields.

## Prompt

```text
You extract structured data from a chart, plot, or table image.

Image: {{image}}

Chart type hint (may be empty):
{{chart_type_hint}}

Steps:
1. Identify the chart type. Choose ONE:
   - "bar"        — bar / column chart, including stacked / grouped
   - "line"       — line plot, including multi-series
   - "scatter"    — scatter plot
   - "pie"        — pie / donut chart
   - "area"       — area / stacked area
   - "table"      — tabular grid of values
   - "heatmap"    — color-coded grid
   - "other"      — does not fit the above; describe in chart_subtype

2. Read the labels:
   - For charts: x-axis label, y-axis label, axis units, title.
   - For tables: column headers, row headers (if any), title / caption.

3. Extract the data. Be specific about values:
   - Read numbers from gridlines, labels, or visible annotations.
   - For bars / lines without explicit value labels, ESTIMATE from
     gridlines, and downgrade per-point confidence accordingly.
   - For colors / category encodings, decode using the legend.

4. Per-data-point confidence:
   - "high"   — value is explicitly labeled in the image.
   - "medium" — value is read from gridlines with clear position.
   - "low"    — value is estimated; gridlines absent or position
                ambiguous.

Return ONLY this JSON object:
{
  "chart_type": "bar" | "line" | "scatter" | "pie" | "area" | "table" | "heatmap" | "other",
  "chart_subtype": "<short clarifying phrase, or empty string>",
  "title": "<chart or table title, or empty>",
  "axes_or_columns": {
    "x_or_columns": "<x-axis label or comma-separated column headers>",
    "y_or_rows": "<y-axis label or row index hint, or empty>",
    "units": "<unit string, or empty>"
  },
  "data": [
    {
      "label": "<series / row identifier>",
      "points": [
        {"x": "<x value or column>", "y": <numeric y or cell value>, "confidence": "high" | "medium" | "low"}
      ]
    }
  ],
  "data_quality": {
    "rows_or_points_extracted": <integer>,
    "trustworthy_for_automation": true | false
  },
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Set "trustworthy_for_automation": true only if MAJORITY of points are
confidence "high" or "medium" AND the chart type was classified
without ambiguity.
```

## Example

**Input:**

```text
image: <bar chart titled "Q3 2024 revenue by region", x-axis labels: "NA", "EU", "APAC", "LATAM", y-axis "Revenue ($M)" gridlines at 0/5/10/15/20, bars at 18, 12, 9, 4 with explicit value labels above each bar>
chart_type_hint: ""
```

**Expected output:**

```json
{
  "chart_type": "bar",
  "chart_subtype": "vertical bar chart, single series",
  "title": "Q3 2024 revenue by region",
  "axes_or_columns": {
    "x_or_columns": "Region",
    "y_or_rows": "Revenue",
    "units": "USD millions"
  },
  "data": [
    {
      "label": "Q3 2024 revenue",
      "points": [
        {"x": "NA",    "y": 18, "confidence": "high"},
        {"x": "EU",    "y": 12, "confidence": "high"},
        {"x": "APAC",  "y": 9,  "confidence": "high"},
        {"x": "LATAM", "y": 4,  "confidence": "high"}
      ]
    }
  ],
  "data_quality": {
    "rows_or_points_extracted": 4,
    "trustworthy_for_automation": true
  },
  "decision_basis": "Bars have explicit value labels; chart type and units unambiguous."
}
```

## Failure Modes

- **Estimation overconfidence** — model marks `high` on values it
  actually estimated from gridlines. Detect by sampling outputs
  where the chart in the image clearly lacks value labels but
  confidence is "high"; reject as inflated.
- **Multi-series confusion** — when a chart has multiple lines /
  stacked bars, model may merge them or assign wrong labels via the
  legend. Detect by checking that `data` contains the expected
  number of series; cross-reference labels with the legend visible
  in the image.
- **Color-decoding errors** — heatmaps and stacked bars depend on
  the legend's color → category mapping. If the legend is small or
  low-contrast, the model may swap categories. Flag low-resolution
  inputs upstream.
- **Pie chart percentage misreading** — pies without percentage
  labels often get rough estimates that don't sum to 100%. Validate
  by summing extracted percentages; if not within 100±5%, downgrade
  confidence.
- **Missing axis units** — axes labeled "Revenue" without "$M" or
  "thousands" lead to ambiguous values. Mitigation: prompt's "units"
  field forces an explicit attempt; pair with `chart_type_hint`
  including unit context for high-stakes use.
- **Chart type misclassification** — area chart classified as line,
  stacked bar classified as grouped. Track classification distribution;
  if `chart_subtype` is frequently "other", the rubric is too narrow
  for your domain.
- **Trustworthy_for_automation inflation** — model marks true even
  when most points are low confidence. Verify the rule logic at
  parse time, don't trust the field alone.

## Tuning Notes

- 模型差异：必须 strong VLM。GPT-4V / Claude Vision / Gemini Pro
  Vision 在 chart-reading 上能力差异较大，建议在你的实际 chart
  分布上小样本 A/B 选模型。中档 VLM 在 estimation 类（无 value
  label 的 bar / line）上失败率显著上升。
- 温度：`0.0`。
- 与 `multimodal/ocr-structured-extraction` 的关系：OCR-extraction
  适合**文档**（receipts、forms、IDs，结构由文字布局决定）；本卡
  适合**可视化**（bars、lines、pies，结构由图形编码决定）。两者的
  prompt、failure modes、所需 VLM 能力都不同，**不要混用**。
- 与 `multimodal/structured-caption-generator` 的关系：caption
  generator 是无 schema 的描述（"图里有什么"）；本卡是有 schema
  的数据抽取（"图里的数据是什么"）。如果用户只是想要 caption，用
  caption generator；想要数据，用本卡。
- 高敏场景（财报、临床数据、政府统计）：本卡的 confidence 字段是
  必要不充分。生产中应当：(1) 后接 sanity check（pie 求和、bar
  排序合理性、value 在合理范围内）；(2) confidence != "high" 的
  样本走人工复核；(3) 对照原始数据源（如果有）做 ground truth
  对比。
- chart 大小敏感性：本卡假设输入图像是高分辨率的（chart 主体
  occupy >40% 画面，文字可读）。低分辨率截图会导致 OCR 错误传染
  到 axis label 和 value 读取。
- 用作训练数据：本卡产出可作为 chart-understanding VLM 的 SFT
  监督信号；建议先用人工核对 50-100 张作为 calibration set。

## Changelog

- `0.1.0` — Initial card.
