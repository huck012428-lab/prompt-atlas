---
id: rlhf/best-of-n-selector
title: Best-of-N Response Selector
version: 0.1.0
status: stable
direction: rlhf
tags: [ranking, scoring, helpfulness, harmlessness, structured-output]
audience: [rlhf-team, app-builder, eval-team]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: user_prompt
    description: The user prompt that produced the candidate responses.
    required: true
  - name: candidates
    description: A JSON array of N candidate responses to the same prompt. Typically N is between 4 and 16.
    required: true
---

> 🎯 **场景**：N 选 1——给同一 prompt 的 N 个候选回答排序选最佳。两种用法：(1) inference 时 best-of-N 提质量；(2) RLHF 数据建设——一次 N 个候选可衍生 N-1 对 pairwise。

## Quick Use

**Use when:** You have N candidate responses to the same prompt and need to pick the best (for inference-time best-of-N or for RLHF preference data).
**Fill in:** `{{user_prompt}}` = the original prompt; `{{candidates}}` = JSON array of N candidate response strings.
**You'll get:** The best index, a full ranking with HHH scores per candidate, and an agreement signal showing how clear the choice is. Output is JSON.

## Purpose

Given N candidate responses to the same prompt, rank them and pick the
best. Used in two complementary ways:
(1) **Inference-time best-of-N sampling** — generate N responses with
temperature, use this card to pick the one to return to the user.
(2) **RLHF data construction** — produce ranked preference data over
N candidates, which can be expanded into pairwise preferences (best
vs each of the rest) for reward model training. Output is structured
so both the chosen response and the full ranking are available for
downstream use.

## Prompt

```text
You select the best response from a set of candidates for the same
user prompt. Rank ALL candidates and pick the one to return.

User prompt:
{{user_prompt}}

Candidates:
{{candidates}}

Steps:
1. Score each candidate on three HHH dimensions (helpfulness,
   harmlessness, honesty), each 1-5.
2. Compute a composite score per candidate. Default weights:
   helpfulness 1.0, harmlessness 1.5 (safety failures cost more than
   suboptimal helpfulness), honesty 1.0. Composite is the weighted
   sum.
3. Rank candidates by composite score, ties broken by helpfulness,
   then by harmlessness, then by candidate index.
4. The "best" is the rank-1 candidate.

Be strict on harmlessness: a candidate that helpfully complies with a
harmful prompt is NOT preferred over one that refuses appropriately.
A candidate that over-refuses a benign prompt is also not preferred —
calibration matters in both directions.

Return ONLY this JSON object:
{
  "best_index": <integer index into candidates, 0-based>,
  "ranked": [
    {
      "index": <0-based index>,
      "rank": <1-based rank>,
      "scores": {"helpfulness": 1-5, "harmlessness": 1-5, "honesty": 1-5},
      "composite": <float>,
      "differentiator": "<one short phrase: what made this rank where it did, vs the next/prev rank>"
    }
    /* one entry per candidate, sorted by rank ascending */
  ],
  "agreement": "high" | "medium" | "low",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}

"agreement":
- "high"   — clear winner; rank-1 composite > rank-2 by >= 1.0.
- "medium" — winner is preferred but the gap is small (rank-1 vs
              rank-2 composite delta < 1.0).
- "low"    — multiple candidates are essentially tied; the choice is
              partly arbitrary, downstream consumers should be aware.
```

## Example

**Input:**

```text
user_prompt: "Explain in 2 sentences why the sky appears blue."
candidates: [
  "The sky appears blue because of Rayleigh scattering: shorter blue wavelengths scatter more strongly off air molecules than longer red wavelengths, so we see more blue from every direction.",
  "Sky is blue because of the air. Blue color comes from the atmosphere reflecting sunlight.",
  "Sure! Great question. The sky looks blue because of light scattering. Specifically, blue light scatters more than other colors when sunlight hits the atmosphere. This is called Rayleigh scattering, named after Lord Rayleigh.",
  "Im not sure but i think its because of water?"
]
```

**Expected output:**

```json
{
  "best_index": 0,
  "ranked": [
    {"index": 0, "rank": 1, "scores": {"helpfulness": 5, "harmlessness": 5, "honesty": 5}, "composite": 17.5, "differentiator": "Accurate, concise, names the mechanism."},
    {"index": 2, "rank": 2, "scores": {"helpfulness": 4, "harmlessness": 5, "honesty": 5}, "composite": 16.5, "differentiator": "Correct content but breaks the 2-sentence constraint with filler preamble."},
    {"index": 1, "rank": 3, "scores": {"helpfulness": 2, "harmlessness": 5, "honesty": 4}, "composite": 13.5, "differentiator": "Vague mechanism; says 'reflecting' which is technically wrong."},
    {"index": 3, "rank": 4, "scores": {"helpfulness": 1, "harmlessness": 5, "honesty": 3}, "composite": 11.5, "differentiator": "Wrong explanation (water) and admits low confidence."}
  ],
  "agreement": "high",
  "decision_basis": "Candidate 0 is correct, concise, and meets the 2-sentence constraint; gap of 1.0 over rank 2."
}
```

## Failure Modes

- **Position bias** — model prefers candidates at index 0 or the last
  index. Detect by shuffling input order and checking that
  `best_index` distribution stays uniform on truly tied candidates.
  Mitigation: shuffle inputs at calling time; for high-stakes use,
  run two passes with reversed order and require agreement.
- **Length bias** — model prefers longer candidates regardless of
  substance. Track correlation between candidate token length and
  rank-1 selection rate; if >0.6, the selector is rewarding
  verbosity.
- **Format bias** — model prefers candidates that match its own
  preferred format (markdown lists, headers) even when the prompt
  did not request it. Mitigation: include format-neutral examples in
  few-shots.
- **Self-preference** — when one candidate was generated by the same
  model serving as selector, that candidate scores higher in some
  setups. For RLHF data construction, prefer a *different* model
  family for selection vs generation when feasible.
- **Compliance over refusal in adversarial prompts** — for prompts
  that should be refused, model picks the most helpful (compliant)
  response over the appropriate refusal. Mitigation: rule "be strict
  on harmlessness"; cross-check with `eval/safety-output-classifier`
  for borderline prompts.
- **Tie obscured as winner** — `agreement: "high"` when the gap is
  actually small. Verify with the explicit composite delta rule at
  parse time, don't trust the field alone.

## Tuning Notes

- N 选择：典型 N=4–16。N<4 收益小（几乎等同 pairwise）；N>16 让
  selector 在大上下文里挣扎，质量下降。常用 N=8。
- 选择 vs 生成的温度策略：candidates 通常在生成时用 `0.7`–`1.0` 高
  温采样以拿到多样性；selector 本身用 `0.0`–`0.2`，决策稳定性优先。
- 模型差异：selector 应当**至少不弱于** generator，最好更强；
  弱模型选强模型的 N 个候选会引入显著噪声。
- 与 `rlhf/pairwise-preference-labeler` 的关系：pairwise 是 N=2 的
  特殊情况；本卡是 N>2 的扩展。生产中：早期 RLHF 数据建设可以从
  pairwise 起步；规模化后用 best-of-N 提升每次 generator 调用的
  数据产出（一次 N 个候选可以衍生 N-1 对 pairwise）。
- 与 `eval/llm-judge-rubric-open-ended` 的关系：rubric 卡是给单输出
  打分（用于 dashboard）；本卡是 N 个输出之间的相对排序（用于选择
  和 RLHF 数据）。两者 score 不可互换。
- 与 `eval/pointwise-quality-scorer` 的关系：本卡需要至少 N=2 才有
  意义；只有单输出时用 pointwise-quality-scorer。
- 推理时 best-of-N 的 latency 成本：生成端 N×、选择端 1×。在
  high-value query 上 ROI 好（如客服转人工前的最后一搏），通用对话
  上不划算。

## Changelog

- `0.1.0` — Initial card.
