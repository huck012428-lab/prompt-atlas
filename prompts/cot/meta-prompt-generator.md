---
id: cot/meta-prompt-generator
title: Meta-Prompt Generator (generate prompts for a class of tasks)
version: 0.1.0
status: experimental
direction: cot
tags: [generation, structured-output, instruction-tuning]
audience: [prompt-engineer, llm-trainer, ai-pm]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: task_class_description
    description: A description of the class of tasks the meta-prompt should handle (e.g. "summarization of customer support tickets", "factuality scoring of generated medical advice").
    required: true
  - name: example_inputs
    description: A JSON array of 2-5 example inputs that the meta-prompt should be able to handle.
    required: true
---

> 🎯 **场景**：从"任务描述 + 几个示例"反向生成可重用的 meta-prompt——含 role / 步骤 / 输出格式 / failure modes / 调优建议。是 prompt-atlas 卡片的 "card generator" 雏形。适合 prompt 工程师快速搭新场景的起点。

## Quick Use

**Use when:** You're starting a new prompt-engineering task and want a meta-prompt template generated from a description + examples, instead of writing it from scratch.
**Fill in:** `{{task_class_description}}` = what kind of task; `{{example_inputs}}` = JSON array of 2-5 example inputs.
**You'll get:** A reusable meta-prompt with role, steps, output schema, and notes on what to watch for. Output is JSON.

## Purpose

Generate a reusable prompt template for a class of tasks, given a
description and a few examples. The output meta-prompt is structured
similarly to a Prompt Atlas card body: clear role, ordered steps,
explicit output schema, failure modes to watch. Used as the
starting point for prompt-engineering work, replacing "blank-page"
syndrome. Output is structured so the meta-prompt can be filed
into a prompt library or further refined.

## Prompt

```text
You generate a reusable meta-prompt for a class of tasks.

Task class description:
{{task_class_description}}

Example inputs (representative — the meta-prompt should handle
similar inputs):
{{example_inputs}}

Steps:
1. Infer the task's role / persona ("You are a [X]") from the
   description and examples.
2. Identify what information varies between calls (variables) and
   what stays fixed (instructions).
3. Define an output schema appropriate to the task. Prefer JSON for
   programmatic consumers; prose for human consumers.
4. List 3-5 likely failure modes of this kind of task — what could
   go wrong, in plain language.
5. List 2-3 tuning notes — when to consider adjusting (model
   choice, temperature, few-shot count).

Return ONLY this JSON object:
{
  "meta_prompt": "<the generated prompt template, complete enough to use>",
  "variables": [
    {"name": "<snake_case>", "description": "<short>"}
  ],
  "output_schema_description": "<short>",
  "failure_modes": ["<one short bullet per mode>"],
  "tuning_notes": ["<one short bullet per note>"],
  "ready_to_use": true | false,
  "needs_more_info": "<if ready_to_use=false: what would you need to make this better; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
task_class_description: "Score customer support reply drafts on whether they correctly address the customer's issue."
example_inputs: [
  {"customer_message": "My order didn't arrive.", "draft_reply": "We apologize for the inconvenience..."},
  {"customer_message": "Need help canceling subscription.", "draft_reply": "I can help you cancel..."}
]
```

**Expected output (abridged):**

```json
{
  "meta_prompt": "You score a customer support reply draft on whether it addresses the customer's issue. ...",
  "variables": [
    {"name": "customer_message", "description": "The customer's incoming message."},
    {"name": "draft_reply", "description": "The proposed reply draft."}
  ],
  "output_schema_description": "Per-dimension score (issue_addressed, tone, completeness) on 1-5 plus an overall verdict.",
  "failure_modes": [
    "Sycophancy: scoring high purely on warm tone.",
    "Issue misidentification: not catching that the draft answers a different question.",
    "Length bias: longer drafts scored higher regardless of substance."
  ],
  "tuning_notes": [
    "Use frontier judge; mid-tier models conflate tone with issue-addressing.",
    "Temperature 0.0; consistency required for reproducible eval."
  ],
  "ready_to_use": true,
  "needs_more_info": "",
  "decision_basis": "Examples make the variable shape clear; judge-style task suits structured per-dimension scoring."
}
```

## Failure Modes

- **Generic meta-prompt** — output is so abstract it could apply
  to anything. Verify meta_prompt references concepts from the task
  description.
- **Variables wrong** — variable list doesn't match what the
  examples imply varies. Check by walking through example_inputs:
  each varying field should be a variable.
- **Schema mismatch** — output_schema_description doesn't match
  the actual schema in meta_prompt. Cross-validate.
- **Failure modes hand-waved** — "model could be wrong" is not a
  failure mode. Each should be specific to the task class.
- **Pre-mature ready_to_use** — model says ready when more info
  needed (specific edge cases unclear). Sample borderline cases.

## Tuning Notes

- 模型差异：本卡是 meta-task — 需要 frontier 模型。中档模型常产
  generic prompt 或 missing 关键 schema。
- 温度：`0.3`–`0.5`. 需要写作灵活性. 完全 0 温产模板化输出.
- example_inputs 数量：2-5 是甜点. 1 不够推断变量, 5+ 让 prompt 太长.
  典型 3.
- 使用流程: 本卡 → human review → 用 `eval/rubric-generator` 给输出
  task 配 rubric → 跑生成的 meta_prompt → 反复迭代 直到稳.
- 与 `eval/rubric-generator` 的关系: 那张卡是 generate eval rubric;
  本卡是 generate task prompt. 互补 — 从 task 描述出发, 同时拿到
  prompt 和 evaluation rubric, 完整起一个新 task.
- 与 prompt-atlas 卡格式的关系: 本卡产出可以作为新 atlas card 的
  starting point — 加 frontmatter + 例子 + 中文场景 即可.
- 不要把生成的 meta_prompt 直接上生产 — 至少跑一次本卡 + 实际任务
  examples 验证 + 人工 review. 本卡是 起点, 不是终点.

## Changelog

- `0.1.0` — Initial card.
