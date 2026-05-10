---
id: rag/multihop-eval-synthesizer
title: Multi-hop RAG Eval Question Synthesizer
version: 0.1.0
status: experimental
direction: rag
tags: [multi-hop, synthesis, eval-set, generation]
audience: [llm-trainer, eval-team]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: passage_a
    description: First source passage.
    required: true
  - name: passage_b
    description: Second source passage covering a different but related entity/fact.
    required: true
---

## Quick Use

**Use when:** You want to generate a multi-hop QA evaluation question from two related passages.
**Fill in:** `{{passage_a}}` = first source passage; `{{passage_b}}` = second source passage covering a related but different fact.
**You'll get:** A question that requires both passages to answer, plus the gold answer and supporting spans from each. Output is JSON.

## Purpose

Generate a multi-hop evaluation question that *requires* combining information
from two different passages — neither passage alone is sufficient to answer.
Used to build RAG eval sets that stress-test retrievers and graders beyond
single-passage lookup. Output is a JSON record with the question, gold answer,
and the specific spans from each passage that must be combined.

## Prompt

```text
You design multi-hop evaluation questions. Read the two passages and create
ONE question that:
  1. Requires a fact from passage A AND a fact from passage B to answer.
  2. Cannot be answered correctly using only one passage.
  3. Has a single, unambiguous answer in 1–10 words.

Passage A:
{{passage_a}}

Passage B:
{{passage_b}}

Return ONLY a JSON object:
{
  "question": "<the multi-hop question>",
  "answer": "<short gold answer>",
  "supporting_span_a": "<verbatim span from passage A that contributes>",
  "supporting_span_b": "<verbatim span from passage B that contributes>",
  "hop_relation": "<one short phrase describing how A and B are bridged, e.g. 'shared organization', 'temporal sequence'>"
}

Do not invent facts not present in the passages. If the passages cannot
support a true multi-hop question, return:
{ "question": null, "answer": null, "supporting_span_a": "", "supporting_span_b": "", "hop_relation": "insufficient" }
```

## Example

**Input:**

```text
passage_a: "Marie Curie won the Nobel Prize in Physics in 1903 alongside her husband Pierre and Henri Becquerel."
passage_b: "Henri Becquerel discovered spontaneous radioactivity in 1896 while studying uranium salts."
```

**Expected output:**

```json
{
  "question": "Which discovery from 1896 contributed to the work that won the 1903 Nobel Prize in Physics?",
  "answer": "spontaneous radioactivity",
  "supporting_span_a": "Nobel Prize in Physics in 1903 alongside her husband Pierre and Henri Becquerel",
  "supporting_span_b": "Henri Becquerel discovered spontaneous radioactivity in 1896",
  "hop_relation": "shared person bridges date and discovery"
}
```

## Failure Modes

- **Pseudo multi-hop** — question can actually be answered from passage A
  alone; passage B is decorative. Detect by re-running an answerer with each
  passage individually and checking whether either is sufficient.
- **Hallucinated bridge** — model invents a connection not actually supported
  by the passages. The `supporting_span_a` / `supporting_span_b` requirement
  catches most of these (they will be empty or paraphrased).
- **Degenerate questions** — "What did X discover?" using only passage B.
  Mitigation: filter outputs where `hop_relation == "insufficient"` or where
  spans look like single-passage answers.

## Tuning Notes

- 模型差异：必须用强模型（GPT-4 级或 Claude Sonnet+），7B 模型生成的 multi-hop
  90% 以上是伪 multi-hop。
- 温度：`0.7` 增加问题多样性；批量生成后再用单 passage 校验剔除伪 multi-hop。
- 数据准备：passage A 和 passage B 之间最好有"轻度桥接"——共享实体、时间、
  组织。完全无关的 passage 对会迫使模型编造 bridge。
- 产出建议：每对 passage 生成 3–5 题再过滤，保留率通常 30–50%。

## Changelog

- `0.1.0` — Initial card.
