---
id: sft/instruction-deduplicator
title: SFT Instruction Deduplicator
version: 0.1.0
status: stable
direction: sft
tags: [classification, instruction-tuning, structured-output]
audience: [sft-team, llm-trainer]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: instructions
    description: A JSON array of instruction strings (or {id, text} objects). Typical batch 50-300.
    required: true
---

> 🎯 **场景**：找出 SFT 数据集里**语义相似**的指令对——不只是字面去重（lev distance），是 paraphrase / synonymous task / minor variation 级。clusters 标注后让训练数据 dedup 决策可控（保 N 个不保 1 个）。

## Quick Use

**Use when:** You have an SFT instruction dataset and want to find near-duplicates at the SEMANTIC level (paraphrases, synonymous tasks) — not just exact-string duplicates.
**Fill in:** `{{instructions}}` = JSON array of instruction strings or {id, text} objects.
**You'll get:** Clusters of near-duplicate instructions with similarity reasoning, and a recommended representative per cluster. Output is JSON.

## Purpose

Detect semantic near-duplicates in an SFT instruction set. Goes
beyond string-level dedup (which catches exact / minor-typo dupes)
to find "Summarize this article" vs "Give me a summary of the
following article" vs "TL;DR this:" — same task, different
wording. Used in dataset cleanup before training. Output is
structured so per-cluster keep / drop decisions can be programmatic.

## Prompt

```text
You find semantic near-duplicates in an instruction set.

Instructions:
{{instructions}}

Steps:
1. Walk through all instructions and group near-duplicates into
   clusters. Two instructions are near-duplicates if they:
   - Express the same TASK (same input shape, same expected
     output shape)
   - Differ only in wording / register / phrasing
   - Would produce the same kind of training signal

2. For each cluster, pick a "representative" — the clearest /
   most natural phrasing. Briefly note why it's the best
   representative.

3. Singletons (no near-duplicates) get their own one-instruction
   "cluster" with cluster_size=1.

4. Capture cluster_size and total_clusters_found.

Return ONLY this JSON object:
{
  "clusters": [
    {
      "cluster_id": "c1",
      "members": [{"id": "<instruction id or index>", "text": "<instruction>"}],
      "cluster_size": <integer>,
      "representative_id": "<id>",
      "representative_reason": "<short>",
      "task_signature": "<one short phrase describing the shared task>"
    }
  ],
  "total_clusters_found": <integer>,
  "duplicate_clusters": <integer; clusters with size >= 2>,
  "deduplication_potential": <float; fraction of instructions that could be removed: (total_instructions - total_clusters) / total_instructions>,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
instructions: [
  {"id": "i1", "text": "Summarize the article in 3 bullet points."},
  {"id": "i2", "text": "Give me a 3-bullet summary of this article."},
  {"id": "i3", "text": "TL;DR the article in 3 bullets."},
  {"id": "i4", "text": "Translate the article into French."},
  {"id": "i5", "text": "Render the article in French."}
]
```

**Expected output:**

```json
{
  "clusters": [
    {
      "cluster_id": "c1",
      "members": [{"id": "i1", "text": "Summarize the article in 3 bullet points."}, {"id": "i2", "text": "Give me a 3-bullet summary of this article."}, {"id": "i3", "text": "TL;DR the article in 3 bullets."}],
      "cluster_size": 3,
      "representative_id": "i1",
      "representative_reason": "Most explicit and standard wording — 'summarize in 3 bullet points' has minimal ambiguity.",
      "task_signature": "Article → 3-bullet summary"
    },
    {
      "cluster_id": "c2",
      "members": [{"id": "i4", "text": "Translate the article into French."}, {"id": "i5", "text": "Render the article in French."}],
      "cluster_size": 2,
      "representative_id": "i4",
      "representative_reason": "'Translate' is the canonical verb; 'render' is uncommon usage that may confuse.",
      "task_signature": "Article → French translation"
    }
  ],
  "total_clusters_found": 2,
  "duplicate_clusters": 2,
  "deduplication_potential": 0.6,
  "decision_basis": "5 instructions cluster into 2 distinct tasks; 60% can be deduplicated by keeping one rep per cluster."
}
```

## Failure Modes

- **Over-clustering** — clusters two instructions that are similar
  but actually different tasks. "Summarize the article" vs "Critique
  the article" both involve the article but require different
  outputs. Audit task_signature: should describe BOTH input AND
  output shape.
- **Under-clustering** — misses paraphrases. "What's the population
  of X?" vs "How many people live in X?" should cluster. Track
  cluster size distribution; if most clusters are singletons on
  data known to have paraphrases, the bar is too tight.
- **Bad representative pick** — picks a typo'd or awkward variant
  as representative. The representative_reason exists to surface
  this; verify on samples.
- **Cluster size mismatch** — total_clusters_found / sum of
  cluster_sizes don't equal input length. Validate at parse time.

## Tuning Notes

- 模型差异：frontier 模型在跨 paraphrase 识别上更稳；中档模型常对
  "synonymous task with different wording" 漏认。
- 温度：`0.0`，clustering 必须可重现。
- 数据规模：50-300 instructions 一次。> 300 prompt 太长可能丢失。大
  数据集分批跑后用 representative 间再做一轮 cross-batch dedup。
- 与 embedding-based dedup 的关系：本卡是 LLM-based semantic dedup,
  embedding-based 是 vector-similarity dedup. 后者更便宜更快, 适合
  粗筛 (cosine > 0.95); 前者更精, 适合 borderline pairs (0.85-0.95)
  的语义判断. 生产中可以叠加: embedding 先粗筛 → 本卡精细判断.
- 与 `sft/data-coverage-analyzer` 的关系：那张卡分析数据集的覆盖
  分布; 本卡找数据集中的冗余. 互补——一个解决"缺什么", 一个解决
  "多什么". 都是 SFT data hygiene 步骤.
- deduplication_potential 解读: >50% 通常说明数据集有严重重复（来自
  scraping 或 self-instruct 没去重）. 健康数据集 <20%.
- 不要盲目 dedup: 同一任务的多种 phrasing 对 instruction-following
  泛化是有价值的. 建议 cluster size 大的 keep 2-3 个 vs keep 1 个,
  按数据集规模调.

## Changelog

- `0.1.0` — Initial card.
