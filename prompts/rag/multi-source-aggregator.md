---
id: rag/multi-source-aggregator
title: Multi-Source Answer Aggregator (with conflict surfacing)
version: 0.1.0
status: stable
direction: rag
tags: [synthesis, retrieval, citation, structured-output]
audience: [app-builder, eval-team, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The user's question.
    required: true
  - name: sources
    description: A JSON array of source objects, each with `id`, `uri` (or label), and `content` fields. Typical 3-10 sources.
    required: true
---

> 🎯 **场景**：从多个 retrieved sources 综合答案——不是简单拼接，而是识别 sources 间的**冲突**（同一事实多个版本）、**互补**（不同 source 补不同细节）、**重复**（多 source 说同一事**），分别处理。RAG pipeline 的"answer 合成"阶段。

## Quick Use

**Use when:** You have multiple retrieved sources and need to compose an answer that handles conflicts, complements, and redundancies between them — instead of cherry-picking one.
**Fill in:** `{{question}}` = the question; `{{sources}}` = JSON array of source objects (id, uri, content).
**You'll get:** An aggregated answer with inline citations, a conflicts list (where sources disagreed), and a confidence indicator. Output is JSON.

## Purpose

Compose a single answer from multiple retrieved sources, explicitly
handling three patterns: (1) **agreement** — multiple sources say
the same thing, increasing confidence; (2) **complementarity** —
sources cover different aspects, the answer integrates them;
(3) **conflict** — sources disagree, the answer surfaces the
disagreement rather than picking arbitrarily. Used in production RAG
pipelines as the synthesis step after retrieval. Output is structured
so per-claim citations and conflicts can be displayed to users.

## Prompt

```text
You compose a single answer from multiple retrieved sources. Handle
agreement, complementarity, and conflict explicitly — do not silently
pick one source.

Question:
{{question}}

Sources:
{{sources}}

Rules:
1. Every factual claim in the answer must cite at least one source ID.
2. When sources AGREE on a fact, cite all of them: "[s1, s3]".
3. When sources are COMPLEMENTARY (different aspects), integrate
   them with separate citations.
4. When sources CONFLICT (same fact, different values):
   - Do NOT pick one silently.
   - Add an entry to `conflicts` with the conflicting values and
     their sources.
   - In the answer prose, mention the conflict explicitly: "Sources
     disagree on X — [s1] reports A, while [s2] reports B."
5. If the question cannot be answered from the sources at all, set
   `answerable: false` and explain in `unanswerable_reason`.
6. Citations format: bracketed source IDs separated by commas.

Return ONLY this JSON object:
{
  "answerable": true | false,
  "unanswerable_reason": "<if answerable=false: why; else empty>",
  "answer": "<the synthesized answer with [s1] [s2, s3] inline citations>",
  "conflicts": [
    {"about": "<short description of the disputed fact>",
     "values": [{"source_id": "s1", "claim": "<short>"}, {"source_id": "s2", "claim": "<short>"}],
     "resolution": "report" | "favor_majority" | "uncertain"}
  ],
  "confidence": "high" | "medium" | "low",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Confidence rule:
- "high"   — multiple sources agree on key facts; no conflicts.
- "medium" — sources are complementary OR one minor conflict.
- "low"    — major conflict on a key fact, OR few sources, OR
              sources are weak / partial on the question.
```

## Example

**Input:**

```text
question: "When did Voyager 1 cross the heliopause and enter interstellar space?"
sources: [
  {"id": "s1", "uri": "nasa.gov/voyager-mission", "content": "Voyager 1 entered interstellar space on August 25, 2012."},
  {"id": "s2", "uri": "wikipedia.org/Voyager_1", "content": "Voyager 1 crossed the heliopause on August 25, 2012."},
  {"id": "s3", "uri": "old-blog-post.com/2014", "content": "Voyager 1 left the solar system in 2013, scientists confirmed."}
]
```

**Expected output:**

```json
{
  "answerable": true,
  "unanswerable_reason": "",
  "answer": "Voyager 1 crossed the heliopause and entered interstellar space on August 25, 2012 [s1, s2]. One older source [s3] mentions 2013, but this likely reflects the year the crossing was confirmed by NASA rather than the actual crossing date.",
  "conflicts": [
    {
      "about": "Date of heliopause crossing",
      "values": [
        {"source_id": "s1", "claim": "August 25, 2012"},
        {"source_id": "s2", "claim": "August 25, 2012"},
        {"source_id": "s3", "claim": "2013"}
      ],
      "resolution": "favor_majority"
    }
  ],
  "confidence": "high",
  "decision_basis": "Two authoritative sources agree on Aug 25, 2012; one weak source has 2013, likely confirmation date."
}
```

## Failure Modes

- **Silent conflict resolution** — model picks one source's value
  without surfacing the disagreement. Detect by sampling outputs
  with single-citation key facts; cross-check sources for the same
  fact and verify no conflict was hidden.
- **Citation hallucination** — answer cites [s4] when only s1-s3
  exist. Validate every citation references an actual source ID.
- **Over-citing in agreement** — every sentence cites all 5 sources
  for everything, making the answer unreadable. Cite the smallest
  sufficient set of sources per claim.
- **Conflict over-trigger** — model marks as conflict things that
  are actually different aspects (s1 says revenue, s2 says profit
  — those aren't conflicts). Audit conflicts list; each entry should
  be the same fact at different values.
- **Confidence inflation** — "high" on outputs with major unresolved
  conflicts. Verify via the rule logic at parse time.
- **Unanswerable false negative** — model says answerable=false when
  one source actually has the answer. Track unanswerable rate; high
  rates on benchmark queries means the bar is too cautious.

## Tuning Notes

- 模型差异：必须 frontier 模型。中档模型在 conflict detection 上经常
  失败——把同一事实的不同表述当作冲突，或反过来把真冲突当作互补。
- 温度：`0.0`–`0.2`。
- sources 数量：3-10 是甜点。少于 3 用不上 multi-source 优势；多于
  10 attention 分散，长文 source 还会在 prompt 里挤占空间。
- 与 `rag/context-compression` 的关系：context-compression 是先压缩
  passages 再传给 generator；本卡是把多个完整 source 综合成最终答案。
  典型 pipeline：retrieve N passages → compress → 调用本卡综合。
- 与 `rag/citation-faithfulness-scorer` 的关系：本卡产 answer + citations，
  那张卡审计 citations 是否真支持 claim。生产中两者串联：本卡产出 →
  faithfulness scorer 审 → 不合格的 claim 重新综合。
- 高敏场景（医疗、法律）：`resolution: "report"`（明确告诉用户冲突）
  比 `favor_majority` 安全得多。生产配置中建议默认 report，让 majority
  逻辑作为可选。

## Changelog

- `0.1.0` — Initial card.
