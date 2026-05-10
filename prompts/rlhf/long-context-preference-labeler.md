---
id: rlhf/long-context-preference-labeler
title: Long-Context Pairwise Preference Labeler
version: 0.1.0
status: experimental
direction: rlhf
tags: [preference-labeling, pairwise, structured-output]
audience: [rlhf-team, llm-trainer]
models: [frontier-closed]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: long_input
    description: The long input the model was responding to (long document, long conversation, multi-turn context). Typically >2000 tokens.
    required: true
  - name: response_a
    description: First long-form response candidate.
    required: true
  - name: response_b
    description: Second long-form response candidate.
    required: true
---

> 🎯 **场景**：长输入 + 长输出场景的 pairwise 偏好——比短答 pairwise 难得多，judge 容易被长度 / 开头印象 / 局部细节带偏。本卡用结构化 multi-section 比较 + 局部 vs 全局加权 + 长输出特有的 failure mode 检测。

## Quick Use

**Use when:** You're labeling preferences on long-form pairs (long context input + long-form responses, e.g. research summaries, long-form Q&A, multi-turn dialogue) where short-answer pairwise heuristics break down.
**Fill in:** `{{long_input}}` = long context / document / conversation; `{{response_a}}` and `{{response_b}}` = the long-form responses to compare.
**You'll get:** Per-section judgment, overall verdict, and detected long-context-specific failure modes (mid-content drift, hallucinated continuation). Output is JSON.

## Purpose

Label pairwise preference for long-form responses to long inputs.
Short-answer pairwise judging breaks down when responses are
multi-section (the judge's overall verdict can be dominated by the
opening or one prominent section). This card structures the comparison
into per-section judgments + a weighted aggregation, and explicitly
checks for long-form failure modes (lost-in-the-middle drift,
hallucinated continuation, structural completeness). Used for RLHF
data on long-form tasks: research summaries, document Q&A, code
explanation of large codebases, multi-turn dialogue endings.

## Prompt

```text
You judge a pairwise preference between two long responses to a
long input. Be careful: long-form judging has specific failure
modes you need to actively avoid.

Long input:
{{long_input}}

Response A:
{{response_a}}

Response B:
{{response_b}}

Steps:
1. Identify the structural sections of each response (intro,
   sections / paragraphs, conclusion). For multi-section responses,
   you'll judge per-section. For unsectioned long prose, treat as
   first-half / second-half.

2. Per section / half, score 1-5 on:
   - groundedness    : Is this section accurately based on the
                        long_input?
   - relevance       : Does it advance answering the implicit goal of
                        the input?
   - quality         : Is the writing clear, non-redundant?

3. Identify long-form failure modes (mark which response, if any):
   - "mid_content_drift"     : Response loses thread / contradicts
                                earlier in itself.
   - "lost_in_middle"        : Response under-uses content from the
                                middle of long_input.
   - "hallucinated_continuation": Later sections invent content not
                                  in long_input.
   - "false_completeness"    : Response feels complete but actually
                                missed major topics.
   - "format_collapse"       : Loses structure mid-response (bullets
                                start as paragraphs, headings disappear).

4. Aggregate:
   - Per-response score = weighted average across sections, weighting
     each section by its evident importance to the input.
   - Pick winner / tie based on aggregate, BUT downgrade the winner's
     score if it has a major failure mode (lost-in-middle on a key
     topic = severe).

Return ONLY this JSON object:
{
  "section_judgments": [
    {
      "section_label": "<short>",
      "response_a": {"groundedness": 1-5, "relevance": 1-5, "quality": 1-5},
      "response_b": {"groundedness": 1-5, "relevance": 1-5, "quality": 1-5}
    }
  ],
  "long_form_failures": {
    "response_a": ["<failure mode>"],
    "response_b": ["<failure mode>"]
  },
  "aggregate_scores": {
    "response_a": <float>,
    "response_b": <float>
  },
  "verdict": "a" | "b" | "tie",
  "decision_basis": "<one or two sentences>"
}
```

## Example

**Input:**

```text
long_input: <a 5000-word research paper about Voyager mission instruments>
response_a: <800-word summary covering instruments, mission timeline, and scientific findings>
response_b: <800-word summary that opens strong but spends 60% on instrument minutiae and never reaches the scientific findings section>
```

**Expected output:**

```json
{
  "section_judgments": [
    {
      "section_label": "Mission overview",
      "response_a": {"groundedness": 5, "relevance": 5, "quality": 4},
      "response_b": {"groundedness": 5, "relevance": 5, "quality": 5}
    },
    {
      "section_label": "Instrument details",
      "response_a": {"groundedness": 5, "relevance": 4, "quality": 4},
      "response_b": {"groundedness": 5, "relevance": 3, "quality": 4}
    },
    {
      "section_label": "Scientific findings",
      "response_a": {"groundedness": 5, "relevance": 5, "quality": 4},
      "response_b": {"groundedness": 1, "relevance": 1, "quality": 1}
    }
  ],
  "long_form_failures": {
    "response_a": [],
    "response_b": ["lost_in_middle", "false_completeness"]
  },
  "aggregate_scores": {"response_a": 4.6, "response_b": 3.0},
  "verdict": "a",
  "decision_basis": "Response A covers all three implicit-goal sections evenly; Response B opens strong but skips scientific findings entirely — a major lost-in-middle failure that drops it well below A."
}
```

## Failure Modes

- **Opening-paragraph dominance** — judge weights the first paragraph
  too heavily. Mitigation: per-section scoring + explicit aggregate.
- **Length bias on long-form** — judge prefers the longer response
  even when it's worse. The structured per-section approach helps but
  doesn't eliminate; track length-vs-winner correlation on
  benchmarks.
- **Failure mode under-detection** — judge marks no failures even on
  responses that obviously skip half the input's topics. Sample low-
  scoring responses and verify failure mode list is non-empty.
- **Section labeling drift** — judge invents section labels not in
  the responses. Constrain to actual visible structure or first /
  second halves.

## Tuning Notes

- 模型差异：必须 frontier 模型 with strong long-context handling
  (Claude / Gemini Pro 1.5 / GPT-4 Turbo+). 中档模型在 long-form
  judging 上经常 collapse 到 length-bias 或 first-paragraph bias.
- 温度：`0.0`。
- 输入长度：long_input + 两个 response 加起来通常 >10K tokens. 选 model
  时确认 context window. 超出时按章节切分跑多次再融合（每次一段
  long_input + 对应的两个 response 段）.
- 与 `rlhf/pairwise-preference-labeler` 的关系：pairwise 是一般 case,
  本卡是 long-form 专用. 短答用 pairwise; long-form (>500 tokens
  per response) 用本卡.
- 与 `eval/multi-turn-dialogue-judge` 的关系：那张卡判 turn-by-turn
  对话; 本卡判 single long response. 多轮长对话两者结合用.
- 在 RLHF 数据建设中：long-form preference data 比 short-form 贵
  10-50x（标注成本和判官成本都高）. 本卡是降本的方法之一: structured
  judging 让判官更可靠, 减少 noise 让训练效率更高.

## Changelog

- `0.1.0` — Initial card.
