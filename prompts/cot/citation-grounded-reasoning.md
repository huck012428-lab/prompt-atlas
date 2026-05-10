---
id: cot/citation-grounded-reasoning
title: Citation-Grounded Reasoning (every claim must cite)
version: 0.1.0
status: stable
direction: cot
tags: [structured-reasoning, citation, grounding, structured-output]
audience: [prompt-engineer, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The question to reason about.
    required: true
  - name: sources
    description: A JSON array of source objects with `id` and `content` fields. The reasoning may ONLY use facts from these sources.
    required: true
---

> 🎯 **场景**：所有事实陈述必须引用 source 的推理 — 比 RAG answer-grounding-checker 更严格：不允许任何无引用的 fact，无引用的就只能是推理 / 综合。适合学术 / 法律 / 医学等"必须可追溯"的高敏推理。

## Quick Use

**Use when:** You need reasoning where EVERY factual claim cites a source — for academic, legal, medical, or compliance contexts where unsourced claims are unacceptable.
**Fill in:** `{{question}}` = the question; `{{sources}}` = JSON array of source objects with id + content.
**You'll get:** A reasoning chain where each step's claims are sourced (or marked as inference / common-knowledge), the final answer with citations, and a flag for any insufficient-source steps. Output is JSON.

## Purpose

Produce reasoning where every factual claim is either (a) cited
from provided sources, (b) explicitly marked as inference from
prior steps, or (c) explicitly marked as common knowledge. Used in
high-stakes settings where claim provenance matters: legal
analysis, medical literature review, regulatory compliance,
research synthesis. Distinct from `cot/structured-reasoning-with-
rationale-summary` which doesn't enforce sourcing.

## Prompt

```text
You answer a question by reasoning, where EVERY factual claim must
be one of: (a) cited from the provided sources, (b) explicit
inference from prior steps, (c) common knowledge.

Question:
{{question}}

Sources:
{{sources}}

Rules:
1. Each step in your reasoning produces one or more concrete claims.
2. Each claim must be tagged:
   - "cited"           : Cite source id(s) the claim comes from
                         (e.g. "[s2]"). Quote or close-paraphrase the
                         supporting span in `support_quote`.
   - "inference"       : Derived from prior steps in this chain.
                         Cite which step(s) it follows from.
   - "common_knowledge": Widely known, not source-cited. Use sparingly
                         and only for genuinely uncontroversial facts.

3. If reasoning requires a fact that is NEITHER in sources NOR
   common knowledge, set the step's "supportable": false and stop.
   Do NOT invent facts.

4. The final_answer must reference the steps that justify it.

Return ONLY this JSON object:
{
  "steps": [
    {
      "step_id": "s1",
      "claim": "<the claim>",
      "tag": "cited" | "inference" | "common_knowledge",
      "source_ids": ["<source id>"] /* for tag=cited */,
      "support_quote": "<verbatim or close paraphrase from source>" /* for tag=cited */,
      "follows_from": ["<step id>"] /* for tag=inference */,
      "supportable": true | false
    }
  ],
  "final_answer": "<the answer with [step_id] citations>",
  "supportable_overall": true | false,
  "missing_information": "<if not supportable_overall: what facts would be needed; else empty>",
  "common_knowledge_count": <integer>,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
question: "Was Voyager 1 the first human-made object to enter interstellar space?"
sources: [
  {"id": "s1", "content": "Voyager 1 entered interstellar space on August 25, 2012, when it crossed the heliopause."},
  {"id": "s2", "content": "Voyager 2 reached interstellar space on November 5, 2018."},
  {"id": "s3", "content": "Voyager 1 was launched in September 1977; Voyager 2 in August 1977."}
]
```

**Expected output:**

```json
{
  "steps": [
    {
      "step_id": "s1",
      "claim": "Voyager 1 entered interstellar space on August 25, 2012.",
      "tag": "cited",
      "source_ids": ["s1"],
      "support_quote": "Voyager 1 entered interstellar space on August 25, 2012, when it crossed the heliopause.",
      "follows_from": [],
      "supportable": true
    },
    {
      "step_id": "s2",
      "claim": "Voyager 2 entered interstellar space on November 5, 2018, six years after Voyager 1.",
      "tag": "cited",
      "source_ids": ["s2"],
      "support_quote": "Voyager 2 reached interstellar space on November 5, 2018.",
      "follows_from": [],
      "supportable": true
    },
    {
      "step_id": "s3",
      "claim": "Among Voyager 1 and Voyager 2, Voyager 1 reached interstellar space first.",
      "tag": "inference",
      "source_ids": [],
      "support_quote": "",
      "follows_from": ["s1", "s2"],
      "supportable": true
    },
    {
      "step_id": "s4",
      "claim": "No other human-made object had entered interstellar space before August 25, 2012.",
      "tag": "common_knowledge",
      "source_ids": [],
      "support_quote": "",
      "follows_from": [],
      "supportable": true
    }
  ],
  "final_answer": "Yes, Voyager 1 was the first human-made object to enter interstellar space, doing so on August 25, 2012 [s1]. Voyager 2 followed in 2018 [s2]. No other spacecraft preceded Voyager 1 to interstellar space (common knowledge).",
  "supportable_overall": true,
  "missing_information": "",
  "common_knowledge_count": 1,
  "decision_basis": "Voyager 1's date is sourced; comparison with Voyager 2 follows by inference; that no other craft was earlier is treated as common knowledge."
}
```

## Failure Modes

- **Hidden assumption** — claim tagged "inference" but actually
  introduces a new fact not in prior steps. Verify follows_from
  steps actually contain the asserted information.
- **Common knowledge abuse** — using common_knowledge for
  controversial / domain-specific claims that should be sourced.
  Track common_knowledge_count; if >25% of steps, the model is
  bypassing the sourcing requirement.
- **Source pretending** — model claims a source supports something
  it doesn't. The support_quote field is the safety net; sample
  cited steps and verify the quote actually appears in the source.
- **Failure to surface gap** — model reaches an unsupportable
  conclusion without setting supportable=false. Audit final answers;
  if supportable_overall=true but the answer leans on an
  unsourced fact, the gap was hidden.
- **Over-citation** — every step has 5 source citations including
  irrelevant ones. Citations should be the smallest sufficient set.

## Tuning Notes

- 模型差异：本卡对模型自律性要求高（不能编造 source 或 quote）。
  frontier 模型显著更稳；中档模型有时 invent quote 字段以"看起来
  cited"。建议：跑一个 quote-faithfulness check（用
  `rag/citation-faithfulness-scorer` 反向审本卡产出）。
- 温度：`0.0`，reasoning 必须可重现。
- common_knowledge_count 监控：理想是接近 0。每多一个 common_knowledge
  就是一个潜在 escape hatch，应当被 reviewer 关注。
- 与 `cot/structured-reasoning-with-rationale-summary` 的关系：那张
  卡是开放式推理；本卡严格要求每步可追溯。前者通用，后者高敏。
- 与 `rag/answer-grounding-checker` 的关系：那张卡 post-hoc 审
  answer 是否扎根 context；本卡 in-process 强制每步可追溯。
  前者审计，后者预防。
- 与 `cot/uncertainty-quantification` 的关系：uncertainty 标 step-
  level 不确定度；本卡标 step-level 出处。两者正交，都重要：高敏
  推理两者叠加用。
- 高敏场景必备：医疗 / 法律 / 学术。本卡 + faithfulness post-check
  + 人工 review 三层是合规推理 pipeline 的标配。

## Changelog

- `0.1.0` — Initial card.
