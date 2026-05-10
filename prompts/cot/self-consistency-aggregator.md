---
id: cot/self-consistency-aggregator
title: Self-Consistency Aggregator (majority vote over reasoning paths)
version: 0.1.0
status: stable
direction: cot
tags: [structured-reasoning, self-check, rationale-summary, structured-output]
audience: [prompt-engineer, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large, reasoning-model]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The original question that all candidate answers attempted.
    required: true
  - name: candidate_paths
    description: A JSON array of independently-sampled candidate paths, each an object with rationale_summary and final_answer fields.
    required: true
  - name: equivalence_hint
    description: Optional hint for how to consider two answers equivalent (e.g. case-insensitive string match, numerical equivalence within a tolerance, semantic paraphrase). Pass empty string to use exact-match semantics.
    required: false
---

## Quick Use

**Use when:** You've sampled N candidate answers to the same question (with temperature) and want to take a majority vote.
**Fill in:** `{{question}}` = the original question; `{{candidate_paths}}` = JSON array of N (rationale_summary, final_answer) objects; `{{equivalence_hint}}` = optional definition of "equivalent" answers (e.g. numerical tolerance).
**You'll get:** The consensus answer, vote counts per equivalence class, an agreement_rate, and a `trustworthy` flag. Output is JSON.

## Purpose

Aggregate N independently-sampled reasoning paths for the same question
into a single consensus answer plus agreement metrics — the
self-consistency technique. **This card does not sample the paths
itself**; it operates on N pre-sampled (rationale_summary, final_answer)
pairs (typically generated with temperature > 0 by
`cot/structured-reasoning-with-rationale-summary` or similar). Used
when accuracy on hard reasoning tasks matters more than latency:
arithmetic, multi-step QA, code translation. Output is structured so
the agreement rate doubles as a confidence signal.

## Prompt

```text
You are aggregating N candidate reasoning paths for the same question
into a consensus answer using majority vote. Decide which final answers
are equivalent, count the votes, and return the consensus.

Original question:
{{question}}

Candidate paths (each has its own rationale_summary and final_answer):
{{candidate_paths}}

Equivalence hint (may be empty):
{{equivalence_hint}}

Steps:
1. Group the candidate paths' final_answer values into equivalence
   classes. Two answers are in the same class if and only if they
   would be considered "the same answer" by the equivalence_hint
   (or by exact-match if no hint is given). Examples:
   - "42" and "forty-two" are equivalent under numerical equivalence.
   - "Paris" and "Paris, France" are equivalent under "city-level
     match".
2. The consensus answer is the answer of the largest equivalence
   class. If two classes tie, pick the answer whose member paths have
   the most coherent rationale_summary as a tiebreaker.
3. Compute agreement_rate = size of consensus class / N.
4. List the minority answers and how many paths produced each.

Return ONLY this JSON object:
{
  "consensus_answer": "<the canonical form of the majority answer>",
  "vote_counts": [
    {"answer": "<canonical form>", "count": <integer>}
    /* one entry per equivalence class, sorted by count desc */
  ],
  "agreement_rate": <float between 0.0 and 1.0>,
  "trustworthy": true | false,
  "minority_summary": "<one short phrase: are minority answers obviously wrong, or plausible alternatives, or both?>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

Set "trustworthy": true only if agreement_rate >= 0.6 AND the consensus
class contains at least 2 paths. Otherwise trustworthy=false; the
consumer should treat the consensus as a weak signal.
```

## Example

**Input:**

```text
question: "If a train leaves at 9:00am at 80 km/h and a second train leaves at 10:30am at 100 km/h on the same track, when does the second train catch up?"
candidate_paths: [
  {"rationale_summary": "Lead = 80*1.5 = 120 km. Closing speed = 20 km/h. Time = 120/20 = 6h. Catch-up at 4:30pm.", "final_answer": "4:30pm"},
  {"rationale_summary": "Computed lead 120 km, closing 20 km/h, 6 hours after 10:30am gives 4:30pm.", "final_answer": "4:30pm"},
  {"rationale_summary": "Used relative-speed framing; 6h after 10:30am.", "final_answer": "16:30"},
  {"rationale_summary": "Off-by-one: thought lead was 80 km, got 4 hours later = 2:30pm.", "final_answer": "2:30pm"},
  {"rationale_summary": "Same approach as path 1; 4:30pm.", "final_answer": "4:30pm"}
]
equivalence_hint: "Treat 24-hour and 12-hour clock formats as equivalent."
```

**Expected output:**

```json
{
  "consensus_answer": "4:30pm",
  "vote_counts": [
    {"answer": "4:30pm", "count": 4},
    {"answer": "2:30pm", "count": 1}
  ],
  "agreement_rate": 0.8,
  "trustworthy": true,
  "minority_summary": "One path made an arithmetic error on the lead distance; the dissent is clearly wrong, not a plausible alternative.",
  "decision_basis": "Four of five paths agree on 4:30pm under 24h-equivalence; the dissent is an obvious computation error."
}
```

## Failure Modes

- **Equivalence over-merging** — model decides "4:30pm" and "5:30pm"
  are equivalent under a vague hint, inflating agreement. Detect by
  spot-checking equivalence classes that combine numerically distinct
  values; tighten `equivalence_hint`.
- **Equivalence under-merging** — model treats "42" and "forty-two"
  as different answers because the hint is missing. Always pass an
  explicit `equivalence_hint` for non-string outputs.
- **Tie-handling bias** — when two classes tie, model defaults to
  the first-listed path; ordering of `candidate_paths` then
  influences the result. Mitigation: shuffle `candidate_paths`
  before passing in; or implement a deterministic tiebreaker upstream.
- **Format normalization drift** — `consensus_answer` is in a
  different format than any candidate (e.g. all candidates said
  "4:30pm" but consensus says "16:30 PM"). Mitigation: rule says
  pick the canonical form FROM the consensus class, not invent a
  new format.
- **Trustworthy inflation** — for N=3 with split 2-1, model marks
  trustworthy=true even though 2 paths is a weak basis. The rule
  "consensus class contains at least 2 paths AND agreement >= 0.6"
  helps; on small N (<5) treat trustworthy as a noisy hint.
- **Non-categorical answer collapse** — for free-text answers (e.g.
  long-form explanations), majority vote is meaningless. This card
  is for answers that have a small number of canonical forms;
  free-text generation needs a different aggregator (e.g. LLM-judge
  on pairwise of paths).

## Tuning Notes

- N 选择：典型 N=5–10。N<3 不显著降低方差；N>20 边际收益小。算式
  类问题 N=5 通常足够，open-domain 多步推理 N=10 更稳。
- 采样温度：上游采样建议 `0.5`–`0.8`，给路径多样性。本卡 aggregator
  本身用 `0.0`，确保聚合可重现。
- 模型差异：aggregator 不需要强模型——它做的是 string equivalence
  和 vote counting，中档模型够用。**采样阶段**才需要强模型，否则
  N 个 path 可能集体一致地犯同一种错。
- 与 `cot/structured-reasoning-with-rationale-summary` 的关系：
  那张卡产出单个 (rationale_summary, final_answer)；本卡聚合多个。
  典型工作流：上游把 structured-reasoning 卡跑 N 遍 → 把 N 个 outputs
  作为 candidate_paths 喂本卡。
- 与 `cot/least-to-most-decomposition` 的关系：least-to-most 把单个
  问题拆成易子问题，是单条路径的优化；self-consistency 是多条路径
  的方差缩减。两者正交，可叠加：每条 self-consistency path 内部用
  least-to-most 推理。
- agreement_rate 的解读：可作为答案的"软置信度"，但**不要**直接当
  概率使用（self-consistency 的 calibration 在不同任务上偏差大）。
  在校准集上回归一遍再使用。
- trustworthy=false 的样本：不要丢弃；它们是模型的 disagreement
  zone，是后续 active learning 或人工 review 的高价值候选。

## Changelog

- `0.1.0` — Initial card.
