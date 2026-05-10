---
id: rag/structured-rag-output-builder
title: Structured RAG Output Builder (table / list / schema from evidence)
version: 0.1.0
status: stable
direction: rag
tags: [synthesis, retrieval, structured-output, extraction]
audience: [app-builder, eval-team, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The user's question (which implies a structured output, e.g. "compare X and Y across Z dimensions").
    required: true
  - name: sources
    description: A JSON array of source objects with id and content.
    required: true
  - name: target_format
    description: "Description of the desired structured output (e.g. comparison table with columns feature/X/Y, list of pros and cons, JSON schema with fields name/price/availability)."
    required: true
---

> 🎯 **场景**：RAG 答案以**结构化形式**返回——比较表、清单、字段化记录等。比让模型自由 prose 后再后处理稳定得多。带 source citations + 缺失字段标记。适合产品比较、结构化抽取、API 响应构造。

## Quick Use

**Use when:** The user's question implies a STRUCTURED answer (comparison table, list, fielded record) and you want the answer in that exact shape with citations, not free prose.
**Fill in:** `{{question}}` = the question; `{{sources}}` = JSON array of sources; `{{target_format}}` = description of the desired output structure.
**You'll get:** A structured output matching target_format, with source citations per cell / item, and explicit "missing" markers where sources don't cover. Output is JSON.

## Purpose

Compose a structured answer (table / list / fielded record) from
RAG-retrieved sources, with per-cell or per-item citations and
explicit markers for fields the sources don't cover. Used in
product comparisons, structured extraction at scale, populating
spec documents from research, and any case where downstream code
expects a specific shape rather than prose. Distinct from
`rag/multi-source-aggregator`: that card produces narrative answer;
this card produces structured data.

## Prompt

```text
You produce a STRUCTURED answer (table / list / fielded record)
from retrieved sources, with citations per cell / item and explicit
markers where sources don't cover a field.

Question:
{{question}}

Sources:
{{sources}}

Target output format:
{{target_format}}

Rules:
1. Build the structure described in target_format.
2. Every cell / field with content cites the source id(s) it came
   from.
3. Cells / fields the sources don't cover get value "not_in_sources"
   (or null with citation = "missing"). Don't invent.
4. If sources conflict, list both with their source ids;
   downstream can decide.
5. If target_format is ambiguous / under-specified, build a
   reasonable structure and describe what you assumed in
   `format_assumptions`.

Return ONLY this JSON object:
{
  "structure_type": "table" | "list" | "record" | "nested",
  "structured_output": <the structured data in shape implied by
    target_format>,
  "citations": [
    {"cell_or_item": "<reference into structured_output, e.g. row 'X', column 'price'>",
     "source_ids": ["<source id>"],
     "support_quote": "<verbatim or close paraphrase>"}
  ],
  "missing_fields": [
    {"cell_or_item": "<reference>", "reason": "<why missing — sources don't cover this aspect>"}
  ],
  "conflicts": [
    {"field": "<reference>", "values": [{"source_id": "<id>", "value": "<...>"}]}
  ],
  "format_assumptions": ["<short> — assumptions made if target_format was ambiguous"],
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
question: "Compare Voyager 1 and Voyager 2 across launch date, current distance from Earth, and primary mission."
sources: [
  {"id": "s1", "content": "Voyager 1 was launched on September 5, 1977, with a primary mission to study Jupiter and Saturn."},
  {"id": "s2", "content": "Voyager 2 was launched on August 20, 1977. It studied Jupiter, Saturn, Uranus, and Neptune."},
  {"id": "s3", "content": "As of late 2024, Voyager 1 is approximately 24.4 billion km from Earth."}
]
target_format: "comparison table with columns: spacecraft, launch_date, current_distance_from_earth, primary_mission"
```

**Expected output:**

```json
{
  "structure_type": "table",
  "structured_output": {
    "columns": ["spacecraft", "launch_date", "current_distance_from_earth", "primary_mission"],
    "rows": [
      {
        "spacecraft": "Voyager 1",
        "launch_date": "September 5, 1977",
        "current_distance_from_earth": "approximately 24.4 billion km (late 2024)",
        "primary_mission": "Jupiter and Saturn"
      },
      {
        "spacecraft": "Voyager 2",
        "launch_date": "August 20, 1977",
        "current_distance_from_earth": "not_in_sources",
        "primary_mission": "Jupiter, Saturn, Uranus, Neptune"
      }
    ]
  },
  "citations": [
    {"cell_or_item": "row 'Voyager 1', launch_date", "source_ids": ["s1"], "support_quote": "Voyager 1 was launched on September 5, 1977"},
    {"cell_or_item": "row 'Voyager 1', current_distance_from_earth", "source_ids": ["s3"], "support_quote": "As of late 2024, Voyager 1 is approximately 24.4 billion km from Earth"},
    {"cell_or_item": "row 'Voyager 1', primary_mission", "source_ids": ["s1"], "support_quote": "primary mission to study Jupiter and Saturn"},
    {"cell_or_item": "row 'Voyager 2', launch_date", "source_ids": ["s2"], "support_quote": "Voyager 2 was launched on August 20, 1977"},
    {"cell_or_item": "row 'Voyager 2', primary_mission", "source_ids": ["s2"], "support_quote": "It studied Jupiter, Saturn, Uranus, and Neptune"}
  ],
  "missing_fields": [
    {"cell_or_item": "row 'Voyager 2', current_distance_from_earth", "reason": "No source provides Voyager 2's current distance; sources only mention Voyager 1's distance."}
  ],
  "conflicts": [],
  "format_assumptions": [],
  "decision_basis": "Built the requested 4-column table; one cell (Voyager 2 distance) marked missing due to source gap; no conflicts."
}
```

## Failure Modes

- **Cell hallucination** — cell filled with plausible-looking content
  not in sources. Validate every non-missing cell has a citations
  entry; reject cells without citations or with empty support_quote.
- **Missing fields silently filled** — model invents a value for
  Voyager 2 distance using common-knowledge / training data. Audit
  by sampling cells and checking each cited support_quote actually
  appears in the cited source.
- **Format drift** — target_format says "table"; model returns prose
  with embedded structure. Validate structure_type matches the
  shape described in target_format.
- **Conflict ignored** — sources have different values for same
  field; model picks one silently. The conflicts field exists for
  this; verify on benchmarks with known conflicts.
- **Format_assumptions hand-wave** — when target_format is ambiguous,
  model just builds something without flagging assumptions. The
  field is required when the target_format is genuinely
  under-specified.

## Tuning Notes

- 模型差异：frontier 模型必须的，特别是涉及 nested 结构时。中档模型
  在 nested table / record 上 schema 不稳。
- 温度：`0.0`，结构化输出必须可重现。
- target_format 写法：**具体列名 + 类型** 优于 abstract 描述。
  "table with columns: name (string), price (number, USD), in_stock
  (boolean)" 比 "comparison table" 让模型 schema 更稳。
- 与 `rag/multi-source-aggregator` 的对比：那张卡产 narrative answer
  + conflict 表面化；本卡产 structured data + conflict 字段。前者
  适合 chat output；后者适合机器消费。
- 与 `rag/answer-grounding-checker` 的关系：本卡产含 citations 的
  structured output；那张卡 audit citations 是否扎根 retrieved context。
  生产中两者协同：本卡 → grounding-checker 审 → 不通过的 cell 标
  uncertain。
- missing_fields 的下游：可以驱动**追加检索** —— "我有 missing 字段
  X，再检索一次专门找 X" 的 multi-hop RAG pattern。
- 用作 SFT 数据：(question, sources, target_format, structured_output)
  四元组训 structured RAG generation 能力。

## Changelog

- `0.1.0` — Initial card.
