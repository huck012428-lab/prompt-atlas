---
id: multimodal/screenshot-to-spec
title: UI Screenshot to Component Spec
version: 0.1.0
status: experimental
direction: multimodal
tags: [vision, extraction, structured-output]
audience: [app-builder, prompt-engineer, ai-pm]
models: [vision-language, frontier-closed]
language: en
input_schema: multimodal
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: image
    description: A UI screenshot — web app, mobile app, design mockup, or wireframe.
    required: true
  - name: platform_hint
    description: Target platform / framework (e.g. "React + Tailwind", "iOS SwiftUI", "Flutter", "design mockup, framework-agnostic"). Pass empty string to leave platform-neutral.
    required: false
---

> 🎯 **场景**：UI 截图 → 结构化组件规格（component tree + 布局 + 交互）。可用于 design-to-code、UI 重做、设计文档生成。需要 vision 模型。**不输出代码**——专注结构识别，代码生成留给下游。

## Quick Use

**Use when:** You have a UI screenshot (web/mobile/wireframe) and want a structured component spec — component tree, layout, interactions — instead of free-text description or raw code.
**Fill in:** `{{image}}` = the UI screenshot; `{{platform_hint}}` = optional target framework hint.
**You'll get:** Component tree (nested), layout description, identifiable interactions, and any design ambiguities. Output is JSON. Requires a vision-language model.

## Purpose

Convert a UI screenshot into a structured spec describing the
component hierarchy, layout system (flex / grid / absolute),
visible interactions (clickable buttons, inputs, navigation), and
design ambiguities. Used as the planning step before code
generation, for UI documentation extraction, and for design
analysis. **Does NOT generate framework code** — that's a separate
downstream step. This separation lets the spec stay framework-
agnostic until the last mile.

## Prompt

```text
You analyze a UI screenshot and produce a structured component spec.
Do NOT generate code — produce structure that a code-gen step could
turn into code.

Image: {{image}}

Platform hint (may be empty):
{{platform_hint}}

Steps:
1. Identify top-level layout. The page divides how? (header / main /
   footer? sidebar + content? card grid? full-screen modal?)

2. Build a component tree. Each node:
   - id: snake_case
   - type: semantic role (header / nav / card / button / input /
     image / icon / text / list / dialog / etc.)
   - children: nested component ids
   - layout: flex / grid / absolute / inline / block
   - bounding_position: top/middle/bottom + left/center/right + size

3. For each interactive component (buttons, links, inputs):
   - capture the label or placeholder text
   - infer the action ("submits form", "opens modal", "navigates to
     X" — use "unclear" if ambiguous)

4. For text content, capture verbatim where readable; mark
   "<illegible>" otherwise.

5. Identify design ambiguities — things the screenshot doesn't make
   clear (hover states, what's behind a dropdown, scroll behavior).

Return ONLY this JSON object:
{
  "platform_inferred": "<best guess of platform if hint was empty; verbatim hint if provided>",
  "top_level_layout": "<short description>",
  "component_tree": [
    {
      "id": "<snake_case>",
      "type": "<semantic role>",
      "label_or_text": "<verbatim or <illegible>>",
      "layout": "flex" | "grid" | "absolute" | "inline" | "block" | "n/a",
      "bounding_position": "<grid-style location + size>",
      "interactive": true | false,
      "inferred_action": "<for interactive: short description, or 'unclear'>",
      "children": ["<child id>"]
    }
  ],
  "design_system_signals": ["<short observation about design system, e.g. 'rounded buttons suggest modern web', 'iOS-style nav bar'>"],
  "ambiguities": [
    {"element": "<short>", "what_unclear": "<short>"}
  ],
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
image: <SaaS app screenshot: top header with logo on left and "Settings" button on right; left sidebar with three menu items (Dashboard, Reports, Users); main content area showing a card titled "Active Users" with a number "1,247" prominently displayed and a small line chart below>
platform_hint: "React + Tailwind"
```

**Expected output:**

```json
{
  "platform_inferred": "React + Tailwind",
  "top_level_layout": "Three-region layout: top header bar, left sidebar nav, main content area (flex-row with sidebar fixed and main flex-grow).",
  "component_tree": [
    {
      "id": "page_root",
      "type": "container",
      "label_or_text": "",
      "layout": "flex",
      "bounding_position": "full-page",
      "interactive": false,
      "inferred_action": "",
      "children": ["header", "body_row"]
    },
    {
      "id": "header",
      "type": "header",
      "label_or_text": "",
      "layout": "flex",
      "bounding_position": "top, full-width, small height",
      "interactive": false,
      "inferred_action": "",
      "children": ["logo", "settings_button"]
    },
    {
      "id": "logo",
      "type": "image",
      "label_or_text": "<illegible>",
      "layout": "n/a",
      "bounding_position": "top-left",
      "interactive": true,
      "inferred_action": "navigates to home",
      "children": []
    },
    {
      "id": "settings_button",
      "type": "button",
      "label_or_text": "Settings",
      "layout": "n/a",
      "bounding_position": "top-right",
      "interactive": true,
      "inferred_action": "opens settings page or modal",
      "children": []
    },
    {
      "id": "body_row",
      "type": "container",
      "label_or_text": "",
      "layout": "flex",
      "bounding_position": "below-header, full-width",
      "interactive": false,
      "inferred_action": "",
      "children": ["sidebar", "main_content"]
    },
    {
      "id": "sidebar",
      "type": "nav",
      "label_or_text": "",
      "layout": "flex (vertical)",
      "bounding_position": "left, narrow, full-height",
      "interactive": false,
      "inferred_action": "",
      "children": ["nav_dashboard", "nav_reports", "nav_users"]
    },
    {"id": "nav_dashboard", "type": "nav_link", "label_or_text": "Dashboard", "layout": "n/a", "bounding_position": "sidebar-top", "interactive": true, "inferred_action": "navigates to /dashboard", "children": []},
    {"id": "nav_reports", "type": "nav_link", "label_or_text": "Reports", "layout": "n/a", "bounding_position": "sidebar-mid", "interactive": true, "inferred_action": "navigates to /reports", "children": []},
    {"id": "nav_users", "type": "nav_link", "label_or_text": "Users", "layout": "n/a", "bounding_position": "sidebar-bottom", "interactive": true, "inferred_action": "navigates to /users", "children": []},
    {
      "id": "main_content",
      "type": "main",
      "label_or_text": "",
      "layout": "block",
      "bounding_position": "right of sidebar, large",
      "interactive": false,
      "inferred_action": "",
      "children": ["active_users_card"]
    },
    {
      "id": "active_users_card",
      "type": "card",
      "label_or_text": "Active Users",
      "layout": "block",
      "bounding_position": "main-top",
      "interactive": false,
      "inferred_action": "",
      "children": ["card_value", "card_chart"]
    },
    {"id": "card_value", "type": "text", "label_or_text": "1,247", "layout": "n/a", "bounding_position": "card-center, large", "interactive": false, "inferred_action": "", "children": []},
    {"id": "card_chart", "type": "image", "label_or_text": "line chart", "layout": "n/a", "bounding_position": "card-bottom, small", "interactive": false, "inferred_action": "", "children": []}
  ],
  "design_system_signals": ["Standard SaaS dashboard layout (header / sidebar / main)", "Card-based content"],
  "ambiguities": [
    {"element": "active_users_card", "what_unclear": "Whether the card is clickable to drill down into details."},
    {"element": "card_chart", "what_unclear": "Time range / data points of the line chart not visible at this resolution."}
  ],
  "decision_basis": "Standard three-region SaaS dashboard captured as a tree of 13 components; chart and card-click ambiguous from screenshot."
}
```

## Failure Modes

- **Component over-fragmentation** — every span of text becomes a
  separate component. The tree should reflect logical groupings;
  text inside a button is part of the button.
- **Action over-confidence** — model claims "submits form" when it
  could be a navigation. Use "unclear" when ambiguous; don't
  confabulate handler types.
- **Missing interactive elements** — buttons styled flat or icons
  not flagged as interactive. Audit interactive=true coverage on
  benchmark screenshots.
- **Hallucinated children** — component tree contains elements not
  visible. Validate by sampling and checking visible text matches
  label_or_text fields.
- **Layout misclassification** — flex vs grid is hard from image
  alone for some patterns. The hint helps; on framework-known
  layouts (Tailwind classes vaguely visible? CSS-in-JS?) the model
  can do better.
- **Platform-bias** — when no hint, defaults to "web" even for
  obvious mobile screenshots. Sample mobile screenshots without
  hint and verify platform_inferred classifies correctly.

## Tuning Notes

- 模型差异：strong VLM 必须的。中档 VLM 在 component_tree 嵌套层级
  上崩塌——不会区分容器 vs 内容元素。
- 温度：`0.0`–`0.2`。
- platform_hint 至关重要：定义了 layout 字段的语义（CSS flex vs
  iOS UIStackView vs Flutter Row）和 design_system_signals 的精度。
  生产中尽量传 hint。
- 与 `multimodal/structured-caption-generator` 的关系：caption 卡描述
  整图（"a screenshot showing X"）；本卡解析 UI 结构（component 层级）。
  前者用于 SEO / search index；后者用于 design-to-code pipelines。
- 与 `multimodal/diagram-to-structured-data` 的关系：那张卡处理图
  diagrams（flowchart / architecture），节点是抽象概念；本卡处理
  UI screenshots，节点是 UI components。语法相似但 type 字段值
  完全不同。
- 下游 code generation：本卡输出做"中间表示"；接一个 generator prompt
  把 JSON tree → 框架代码（React JSX / SwiftUI / Flutter Widget）。
  分两步比一步从图到代码效果显著好。
- 高分辨率敏感：UI 截图截屏缩放后，icon 和小字常错。生产中建议
  原分辨率传入。
- 不要把本卡输出当生产代码——它是 spec，不是代码。组件 id 是供下游
  code-gen 用，不是 React 组件名。

## Changelog

- `0.1.0` — Initial card.
