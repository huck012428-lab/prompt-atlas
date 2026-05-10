---
id: multimodal/diagram-to-structured-data
title: Diagram to Structured Data
version: 0.1.0
status: stable
direction: multimodal
tags: [vision, extraction, structured-output]
audience: [app-builder, eval-team, ai-pm]
models: [vision-language, frontier-closed]
language: en
input_schema: multimodal
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: image
    description: An image of a diagram, flowchart, system architecture, ER diagram, or process map.
    required: true
  - name: diagram_type_hint
    description: One of "flowchart", "system_architecture", "er_diagram", "sequence_diagram", "tree_org_chart", "state_machine", "mind_map", "other". Pass empty string to let the model classify.
    required: false
---

> 🎯 **场景**：把流程图 / 架构图 / ER 图 / 序列图 / 状态机等图像转成结构化 graph（nodes + edges + relations）。下游 pipeline 可以渲染、分析、转换格式（如转 Mermaid / GraphViz）。需要 vision 模型。

## Quick Use

**Use when:** You have an image of a diagram (flowchart, architecture, ER, sequence, etc.) and want to extract its structure as nodes + edges, not free text.
**Fill in:** `{{image}}` = the diagram image; `{{diagram_type_hint}}` = optional type hint (or empty to classify).
**You'll get:** Structured nodes (with type / label), edges (with source / target / direction / label), and an inferred diagram type. Output is JSON. Requires a vision-language model.

## Purpose

Extract the graph structure of a diagram image — what are the nodes,
how are they connected, what kinds of relationships do the edges
express. Used to digitize whiteboard photos, convert legacy diagrams
to modern formats (Mermaid / GraphViz / D3), feed diagrams into
downstream analysis or generation tools, or audit architecture
diagrams for missing components. Distinct from
`multimodal/chart-table-extractor` (data viz) and
`multimodal/document-layout-analyzer` (page structure).

## Prompt

```text
You extract the graph structure of a diagram image.

Image: {{image}}

Diagram type hint (may be empty):
{{diagram_type_hint}}

Steps:
1. Classify the diagram type. Use the hint if provided; otherwise
   pick the closest match: flowchart / system_architecture /
   er_diagram / sequence_diagram / tree_org_chart / state_machine /
   mind_map / other.

2. Extract NODES:
   - Each visible labeled element / box / circle / actor.
   - Capture: id (synthesized snake_case), label (verbatim text or
     close paraphrase), type (process / decision / start / end /
     entity / actor / state / etc. — depends on diagram type),
     position_hint (top/middle/bottom + left/center/right).

3. Extract EDGES:
   - Each line / arrow connecting nodes.
   - Capture: from_id, to_id, direction (one_way / bi_directional),
     label (text on the edge, if any), kind (default /
     conditional / async-message / inheritance / composition / etc.
     — depends on diagram type).

4. If the diagram contains visual elements that don't map to
   nodes/edges (legends, titles, annotations), include in
   `metadata`.

5. Note any visible-but-ambiguous elements (smudged text,
   overlapping arrows) in `ambiguities`.

Return ONLY this JSON object:
{
  "diagram_type": "<classified type>",
  "nodes": [
    {
      "id": "<snake_case>",
      "label": "<verbatim or close paraphrase>",
      "type": "<diagram-specific type>",
      "position_hint": "<short>"
    }
  ],
  "edges": [
    {
      "from_id": "<node id>",
      "to_id": "<node id>",
      "direction": "one_way" | "bi_directional",
      "label": "<text on edge or empty>",
      "kind": "<diagram-specific>"
    }
  ],
  "metadata": {
    "title": "<diagram title or empty>",
    "legend": ["<legend item>"],
    "annotations": ["<other text>"]
  },
  "ambiguities": [
    {"element": "<short description of unclear element>", "reason": "<short>"}
  ],
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
image: <flowchart with three nodes: a "Start" oval at top, a "Validate Input?" diamond in the middle, and two outcomes — "Process" rectangle on the right (label "Yes" on the arrow) and "Return Error" rectangle on the left (label "No" on the arrow); both lead back down to an "End" oval at bottom>
diagram_type_hint: "flowchart"
```

**Expected output:**

```json
{
  "diagram_type": "flowchart",
  "nodes": [
    {"id": "start", "label": "Start", "type": "start", "position_hint": "top-center"},
    {"id": "validate_input", "label": "Validate Input?", "type": "decision", "position_hint": "middle-center"},
    {"id": "process", "label": "Process", "type": "process", "position_hint": "middle-right"},
    {"id": "return_error", "label": "Return Error", "type": "process", "position_hint": "middle-left"},
    {"id": "end", "label": "End", "type": "end", "position_hint": "bottom-center"}
  ],
  "edges": [
    {"from_id": "start", "to_id": "validate_input", "direction": "one_way", "label": "", "kind": "default"},
    {"from_id": "validate_input", "to_id": "process", "direction": "one_way", "label": "Yes", "kind": "conditional"},
    {"from_id": "validate_input", "to_id": "return_error", "direction": "one_way", "label": "No", "kind": "conditional"},
    {"from_id": "process", "to_id": "end", "direction": "one_way", "label": "", "kind": "default"},
    {"from_id": "return_error", "to_id": "end", "direction": "one_way", "label": "", "kind": "default"}
  ],
  "metadata": {"title": "", "legend": [], "annotations": []},
  "ambiguities": [],
  "decision_basis": "Standard input-validation flowchart: start, decision diamond, two branches by yes/no, both terminate at end."
}
```

## Failure Modes

- **Missed edges** — model identifies all nodes but misses some
  connecting arrows, especially overlapping or curved ones. Audit
  edge counts on a benchmark of known diagrams.
- **Wrong direction** — bi-directional arrows marked one-way (or
  vice versa). Sample outputs and verify against image.
- **Label drift** — verbatim text in image becomes paraphrased
  ("Validate Input?" → "Check input validity"). For
  fidelity-sensitive use (digitizing existing diagrams), prefer
  verbatim by reinforcing the rule in prompt.
- **Type mis-classification** — flowchart with one decision
  classified as "state_machine" because the diamond looks like a
  state. The hint helps; if your domain has consistent diagram
  types, always pass hint.
- **Spatial position confusion** — `position_hint` for nodes that
  overlap or are very close. The 9-grid is coarse; downstream
  layout engines should rely on edges, not positions.
- **Missing context** — diagram has a title or legend that the
  model omits. Track `metadata` field richness; if always empty
  on diagrams known to have titles, the rubric needs reinforcement.

## Tuning Notes

- 模型差异：必须 strong VLM. 中档 VLM 在多 edge / overlapping arrows
  / handwritten labels 上失败率明显更高。
- 温度：`0.0`，extraction 必须可重现。
- diagram_type_hint 选择：影响 nodes/edges 的 type 字段语义。
  flowchart 用 process/decision/start/end；ER 用 entity/relationship；
  sequence 用 actor/message。准确 hint 让 type 字段直接可用于下游
  渲染。
- 与 `multimodal/chart-table-extractor` 的关系：chart 是数据可视化
  （bar/line/pie/heatmap），关心数值；本卡是关系图（flowchart/
  architecture/ER），关心连接。两者完全不同。
- 与 `multimodal/document-layout-analyzer` 的关系：layout-analyzer
  识别"页面有哪些区块"，本卡识别"图里有哪些节点和连接"。可串联：
  layout 找到 figure 区域 → 本卡解析 figure 内的图。
- 输出后用法：直接转 Mermaid / GraphViz / D3 是常见下游。建议加一
  个轻量 generator prompt 把本卡 JSON 转成目标语法。
- 高分辨率敏感：低分辨率 / 截图缩放过的图，箭头方向和文字常错。
  上传前确保图清晰可读。
- 用作 VLM benchmark：(diagram_image, ground_truth_graph) 对可作为
  diagram understanding 的 evaluation 数据，本卡的 output 用
  graph-edit-distance 对比。

## Changelog

- `0.1.0` — Initial card.
