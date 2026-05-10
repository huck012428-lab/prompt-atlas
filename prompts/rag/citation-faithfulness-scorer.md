---
id: rag/citation-faithfulness-scorer
title: Citation Faithfulness Scorer
version: 0.1.0
status: stable
direction: rag
tags: [citation, factuality, scoring, grounding, structured-output]
audience: [eval-team, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: claim
    description: A single atomic claim extracted from the model's answer.
    required: true
  - name: cited_span
    description: The verbatim source span the model cited as support for the claim.
    required: true
---

> 🎯 **场景**：审计某条 citation 是否真支持它声称的 claim（fully / partially / not supported）。RAG citation 质量评估的核心，能抓出"假引用"——citation 本身真实但内容不支持 claim。

## Quick Use

**Use when:** You want to audit whether a citation actually supports the claim it was attached to.
**Fill in:** `{{claim}}` = an atomic claim from the AI answer; `{{cited_span}}` = the verbatim source text the answer cited.
**You'll get:** A fully/partially/not-supported verdict, the supporting phrase, and what's missing. Output is JSON.

## Purpose

For a single (claim, cited_span) pair, decide whether the cited span
actually supports the claim — fully, partially, or not at all. Used to
audit citation faithfulness in RAG outputs at the per-claim level, so
that "hallucinated citations" (a real citation pointing at unrelated
text) can be caught even when the cited document is real. Produces a
structured score per pair, which can be aggregated into citation
precision metrics.

## Prompt

```text
You audit citations. Decide whether the cited span actually supports the
claim it was attached to.

Claim:
{{claim}}

Cited span (verbatim from the source document):
{{cited_span}}

Scoring rubric:
- "fully_supported"     — every part of the claim is directly entailed by
                          the span. No additional inference required.
- "partially_supported" — some parts of the claim are supported by the
                          span, but at least one part requires unsupported
                          inference or is missing from the span.
- "not_supported"       — the span does not entail the claim, or
                          contradicts it.

Be strict. If the claim adds a number, qualifier, or causal link that the
span does not state, that is at most "partially_supported".

Return ONLY this JSON object:
{
  "verdict": "fully_supported" | "partially_supported" | "not_supported",
  "supporting_phrase": "<verbatim sub-string of cited_span that supports the claim, or empty string if none>",
  "missing_or_extra": "<for partially/not_supported: what part of the claim is not in the span, in <=20 words; empty string for fully_supported>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
claim: "The James Webb Space Telescope launched on December 25, 2021 and reached L2 in January 2022."
cited_span: "The James Webb Space Telescope launched on December 25, 2021, on an Ariane 5 rocket from French Guiana."
```

**Expected output:**

```json
{
  "verdict": "partially_supported",
  "supporting_phrase": "The James Webb Space Telescope launched on December 25, 2021",
  "missing_or_extra": "The span does not mention reaching L2 or January 2022.",
  "decision_basis": "Span confirms the launch date but says nothing about L2 arrival, so the second half of the claim is unsupported."
}
```

## Failure Modes

- **Inferential leniency** — model marks a claim "fully_supported" when
  the span only loosely implies it ("rocket launched" → "spacecraft
  reached destination"). Detect by spot-checking a sample where
  `supporting_phrase` does not contain the claim's key noun phrases.
  Mitigation: emphasize "no additional inference required" and add a
  few-shot showing a partial-support case.
- **Surface-string matching as proof** — model treats verbatim word
  overlap as support, even when the span uses the same words in a
  different sense. Detect by checking that `supporting_phrase` is a
  meaningful clause, not a single word echo.
- **Claim atomicity assumption** — when the input claim is actually
  two claims joined by "and" (as in the example), the model may verdict
  the whole as "not_supported" instead of "partially_supported". This is
  upstream's job to fix: split conjunctions into atomic claims before
  calling this card.
- **Citation flipping** — model occasionally emits "supported" when the
  span CONTRADICTS the claim. Detect by sampling `not_supported` and
  `fully_supported` outputs and looking for clear contradictions
  mislabeled as support.

## Tuning Notes

- 模型差异：strong 模型（GPT-4 / Claude Sonnet+）在 partial vs full 区分
  上稳定；中档模型容易把 partial 误判为 full。可考虑跑两遍取 max
  strictness（即 partial 优先于 full）。
- 温度：`0.0`，verdict 稳定性优先。
- 输入要求：`claim` 应该已经被 atomic 化（一个事实=一个 claim）。
  conjunction（"X and Y"）类的复合 claim 在送本卡前先拆。
- 与 `rag/answer-grounding-checker` 的关系：本卡是 per-claim 的微观审计
  （需要明确的 citation span）；answer-grounding-checker 是 per-answer
  的宏观审计（不需要 explicit citation，直接对照 retrieved context）。
- 用作训练信号：`fully_supported` 比例可以作为 RAG 系统 citation
  precision 指标；建议把 `not_supported` 样本送人工抽检以校准。

## Changelog

- `0.1.0` — Initial card.
