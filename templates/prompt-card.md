---
id: <direction>/<slug>
title: <Human-readable title>
version: 0.1.0
status: experimental
direction: <rag | agent | rlhf | sft | multimodal | cot | eval>
tags: [<tag-1>, <tag-2>]
audience: [<audience-1>]
models: [generic]
language: en
input_schema: text
output_schema: text
license: CC-BY-4.0
variables:
  - name: example_var
    description: What this slot is for.
    required: true
---

## Quick Use

**Use when:** <one short clause: what problem this card solves, in plain English>.
**Fill in:** `{{var1}}` = <plain English description>; `{{var2}}` = <plain English description>.
**You'll get:** <output described in plain English; mention "Output is JSON" or "Output is plain text" so non-technical users know what to expect>.

## Purpose

One paragraph: when to use this card, what problem it solves, and the kind
of output to expect. Keep it concrete — name the workflow stage (e.g.
"used during eval set construction for retrieval ranking").

## Prompt

```text
You are <role>. <Task description>.

Input:
{{example_var}}

Constraints:
- <constraint 1>
- <constraint 2>

Output format:
<exactly what the model should return>
```

## Example

**Input:**

```text
example_var: "<concrete sample input>"
```

**Expected output:**

```text
<exactly what a correct response looks like>
```

## Failure Modes

- **<Mode name>** — short description of what goes wrong, when it shows up,
  and how to detect it.
- **<Mode name>** — second common failure.

## Tuning Notes

中文使用说明（也可英文）：在哪类模型上常见的踩坑点、对长度/温度/few-shot
数量的敏感性、以及和此卡相关的产品场景。Keep this section practical —
this is where reusers save time.

- 模型差异：<observed differences across model tiers>
- 调优旋钮：<which knobs matter most>
- 场景适配：<how to bend the card for adjacent use cases>

## Changelog

- `0.1.0` — Initial card.
