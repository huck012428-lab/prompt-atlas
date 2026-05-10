---
id: sft/few-shot-example-selector
title: Few-Shot Example Selector (pick best K demonstrations from a pool)
version: 0.1.0
status: stable
direction: sft
tags: [instruction-tuning, classification, ranking, structured-output]
audience: [sft-team, prompt-engineer, llm-trainer, app-builder]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: target_query
    description: The user query (or task instruction) you're about to send to the model and need few-shot demonstrations for.
    required: true
  - name: candidate_examples
    description: A JSON array of available example demonstrations, each an object with `instruction` and `response` fields.
    required: true
  - name: k
    description: How many demonstrations to select (small integer, typically 2 to 6).
    required: true
---

## Quick Use

**Use when:** You have a pool of (instruction, response) demonstrations and want to pick the best K for few-shot prompting a specific target query.
**Fill in:** `{{target_query}}` = the query that will be sent to the model; `{{candidate_examples}}` = JSON array of available demos; `{{k}}` = how many to pick (2-6 typically).
**You'll get:** The selected demonstration indices, a relevance score per selection, and an ordering recommendation. Output is JSON.

## Purpose

Select the best K demonstration examples from a candidate pool for a
specific target query, considering both task similarity (does this
demo show the *same kind* of task?) and complementarity (does this
set of demos collectively cover the variations the model needs to
see?). Used at prompt-construction time, before sending a final
prompt to a model — letting the few-shot prompt adapt per query
rather than using a fixed set. Output is structured so downstream
prompt assembly can splice the chosen demos in the recommended
order.

## Prompt

```text
You select few-shot demonstrations from a pool. Goal: pick the K
demonstrations that will best help a model answer the target query
correctly, considering both per-demo relevance and the diversity of
the chosen set.

Target query (the actual query about to be sent):
{{target_query}}

Candidate examples (each has instruction and response):
{{candidate_examples}}

K (number of demonstrations to select):
{{k}}

Selection criteria:
1. Per-demo relevance: does this demo's instruction look like the
   same KIND of task as the target query (similar input shape,
   similar expected output shape)?
2. Set diversity: the chosen K should NOT be all near-duplicates of
   each other. Prefer demos that collectively show different sub-
   patterns the model might need to handle.
3. Demonstration quality: prefer demos whose response is concise,
   correct-looking, and structurally clean. Avoid demos with overly
   long or rambling responses.
4. Ordering: order the selected demos so that the most directly
   relevant demo comes LAST — language models tend to be most
   influenced by the most recent demo in the prompt.

Return ONLY this JSON object:
{
  "selected": [
    {
      "candidate_index": <0-based index into candidate_examples>,
      "relevance_score": 1-5,
      "selected_for": "<one short phrase: what this demo contributes — 'closest task match', 'covers edge case X', 'demonstrates output format', etc.>"
    }
    /* exactly K entries, ordered as they should appear in the few-shot prompt (last = most directly relevant) */
  ],
  "diversity_note": "<one short phrase about how the selected set covers different sub-patterns, or empty if all selected for similarity>",
  "warning": "<empty string, or a warning if the candidate pool was too small / homogenous to pick K useful demos>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
target_query: "Classify this customer review as positive, negative, or neutral: 'It works fine but the setup was a pain and customer service didn't help.'"
candidate_examples: [
  {"instruction": "Classify the sentiment of: 'Loved every minute of it!'",                "response": "positive"},
  {"instruction": "Classify the sentiment of: 'Terrible. Returned it the next day.'",      "response": "negative"},
  {"instruction": "Classify the sentiment of: 'Does what it says.'",                       "response": "neutral"},
  {"instruction": "Classify the sentiment of: 'The product is great but shipping was slow.'", "response": "neutral"},
  {"instruction": "Translate to French: 'Hello.'",                                          "response": "Bonjour."},
  {"instruction": "Summarize: 'Quarterly report shows 12% revenue growth.'",                "response": "Revenue grew 12% this quarter."}
]
k: 3
```

**Expected output:**

```json
{
  "selected": [
    {"candidate_index": 0, "relevance_score": 4, "selected_for": "Pure-positive sentiment baseline."},
    {"candidate_index": 1, "relevance_score": 4, "selected_for": "Pure-negative sentiment baseline."},
    {"candidate_index": 3, "relevance_score": 5, "selected_for": "Closest match — mixed sentiment with positive product but negative non-product aspects, mirrors the target's structure."}
  ],
  "diversity_note": "Three sentiment-classification demos covering positive, negative, and the mixed/neutral target pattern; ordered so the mixed-pattern demo comes last.",
  "warning": "",
  "decision_basis": "Picked sentiment-classification demos and put the structurally-closest mixed-sentiment demo last for primacy effect on the target."
}
```

## Failure Modes

- **Off-task leakage** — selector picks the French translation or
  summarization examples for a sentiment query (because they were in
  the pool). Detect by sampling outputs where `selected_for` mentions
  irrelevant tasks; reject and force re-selection.
- **Mode collapse on similarity** — all K selections are near-
  identical (e.g. three positive-sentiment demos for a positive-
  leaning target). The `diversity_note` field surfaces this; flag
  outputs where all selections are tagged with the same `selected_for`
  category.
- **Recency-effect ignored** — selector orders demos arbitrarily,
  ignoring rule 4. Verify that the highest-relevance score is at
  the LAST position; if not, re-order at parse time.
- **Score inflation** — every selection gets relevance_score 5.
  Track distribution; flat-5 means the rubric is collapsing.
- **Pool-too-small false success** — pool only contains 2 useful
  demos for K=4 and selector picks 4 by stretching relevance. The
  `warning` field is for this — verify that warnings appear when
  the pool is small / homogeneous.
- **Demo quality blindness** — selector picks a demo whose
  response is wrong or oddly formatted because the instruction matches.
  Mitigation: chain with `sft/data-quality-filter` on the candidate
  pool BEFORE selection, so the pool only contains high-quality demos.
- **Privacy leak through demos** — candidate pool contains real PII
  that gets propagated into the few-shot prompt. The selector itself
  can't fix this; the upstream data pipeline must scrub PII before
  the pool is built.

## Tuning Notes

- 模型差异：本卡对模型的"判断结构相似性"能力高度依赖。frontier 模型
  在 task-shape matching 上稳定；中档模型可能被 surface 词重叠误导
  （只看到 "classify" 字面就当作匹配，忽略 input/output 结构）。
- 温度：`0.0`–`0.2`。selection 决定性优先。
- K 选择：2-6 是大多数 few-shot 场景的甜点。K=1 退化为最佳单 demo；
  K>8 在 context window 上代价大且收益快速递减。
- 候选池规模：本卡假设 candidate_examples 数量在 10-100 量级。<10
  会让选择缺乏空间；>100 会让 selector 在长 context 里挣扎，建议
  先用 cheap retrieval（embedding 相似度）粗筛到 top-50，再用本卡
  做语义级精选。
- 与 `sft/data-quality-filter` 的关系：filter 是过滤"绝对质量"
  （keep / drop）；本卡是选择"相对相关性"（pick K / order）。生产
  中先用 filter 过 demo 池，再用本卡选最相关的子集。
- 与 retrieval-based selection 的关系：典型工程方案是 embedding
  similarity → top-N → 本卡精选 → top-K。embedding 提速，本卡提质。
  纯 embedding 经常被 surface similarity 误导（同领域词汇但任务结构
  不同），本卡正好补这个短板。
- 应用场景：in-context learning、agent few-shot prompting、动态
  prompt 工程、tool-use few-shot examples。固定 few-shot 集合的
  prompt 可以靠 prompt 优化器一次性挑选；变化的 query 需要 per-query
  selection（这就是本卡）。
- diversity_note 的用法：可以反向用于 demo 池的 coverage 分析——
  长期跑下来，哪些 demo 频繁被 last-position 选择，哪些从未被选，
  反映 demo 池的实际有用性。

## Changelog

- `0.1.0` — Initial card.
