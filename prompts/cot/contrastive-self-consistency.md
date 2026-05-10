---
id: cot/contrastive-self-consistency
title: Contrastive Self-Consistency (compare against intentionally-wrong)
version: 0.1.0
status: experimental
direction: cot
tags: [self-check, structured-reasoning, scoring, structured-output]
audience: [prompt-engineer, llm-trainer]
models: [frontier-closed, reasoning-model]
language: en
input_schema: text
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The question to reason about.
    required: true
---

> 🎯 **场景**：让模型不仅给答案，还**主动构造一个错误推理**作对照——通过对比"为什么答案是 A 而不是 B"来强化最终答案的稳定性。比 self-consistency aggregation 在小 N 上更高效。适合多歧义、易错题。

## Quick Use

**Use when:** A question has plausible wrong reasoning paths (common confusions, popular misconceptions) and you want the model to actively contrast its answer against the wrong one for stronger commitment.
**Fill in:** `{{question}}` = the question.
**You'll get:** The correct answer, an articulated wrong-path reasoning the model considered and rejected, and the deciding contrast. Output is JSON.

## Purpose

Force the model to articulate a plausible-looking wrong path and
contrast it with the correct one. The act of building the wrong
path explicitly often surfaces hidden assumptions and prevents
silent confusion. Used on questions with known-common
misconceptions (physics intuition traps, statistics counterintuitive
results, legal "common-sense-but-wrong" applications). Distinct
from `cot/self-consistency-aggregator` which samples multiple paths
externally; this card builds one correct + one wrong path internally
in a single call.

## Prompt

```text
You answer a question by articulating BOTH a plausible wrong path
AND the correct path, then explaining what makes the correct one
correct.

Question:
{{question}}

Steps:
1. Identify the surface intuition many people would use first. State
   it as the "tempting wrong answer" or, if no obvious wrong answer
   exists, set "contrastive_useful": false.

2. Build the wrong reasoning path: "If you reasoned [tempting way],
   you'd conclude [wrong answer]." Articulate it in 2-3 sentences,
   making it sound plausible (not strawman).

3. Build the correct reasoning path. The correct path should be
   structurally different from the wrong one — different framing,
   different governing principle, different decomposition.

4. State the deciding contrast: what specifically makes the correct
   path correct and the wrong path wrong. This should NOT be "the
   correct path uses correct logic" — it should name the specific
   misconception or principle that distinguishes them.

5. Final answer drawn from the correct path.

If the question is straightforward (no plausible wrong path exists,
e.g. "What is 7 * 8?"), set "contrastive_useful": false and answer
directly in `final_answer`.

Return ONLY this JSON object:
{
  "contrastive_useful": true | false,
  "wrong_path": {
    "tempting_intuition": "<short>",
    "reasoning": "<2-3 sentence wrong-but-plausible reasoning>",
    "wrong_answer": "<short>"
  },
  "correct_path": {
    "framing": "<short>",
    "reasoning": "<2-3 sentence correct reasoning>",
    "final_answer": "<short>"
  },
  "deciding_contrast": "<the specific principle or fact that distinguishes correct from wrong>",
  "final_answer": "<the committed final answer>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
question: "If you flip a fair coin and get 5 heads in a row, what's the probability the 6th flip is also heads?"
```

**Expected output:**

```json
{
  "contrastive_useful": true,
  "wrong_path": {
    "tempting_intuition": "Gambler's fallacy: tails is 'due' after a streak of heads",
    "reasoning": "After 5 heads in a row, the 'natural balance' suggests tails is more likely on the next flip — the streak of heads should be balanced out by some tails. So probability of heads on the 6th flip is less than 50%.",
    "wrong_answer": "Less than 50%"
  },
  "correct_path": {
    "framing": "Each flip is an independent event",
    "reasoning": "A fair coin's flips are independent — the coin has no memory of past outcomes. The probability of heads on any single flip is 50%, regardless of what came before. The streak of 5 heads is unusual but does not affect future flips.",
    "final_answer": "50%"
  },
  "deciding_contrast": "Independence of events: 'fair coin' means each flip is independent, so no event in the past can influence the probability of a future flip. The wrong path conflates 'long-run frequency converging to 50%' (true) with 'short-run flips compensating for past results' (false — gambler's fallacy).",
  "final_answer": "50% (one-half)",
  "decision_basis": "Each flip is independent regardless of prior outcomes; gambler's-fallacy intuition is the canonical wrong path that needs explicit refutation here."
}
```

## Failure Modes

- **Strawman wrong path** — model builds an obviously-wrong path
  that no one would actually believe. Real value is in
  plausibly-wrong paths (common misconceptions). Sample wrong paths
  and check they pass the "would a smart person briefly fall for
  this?" test.
- **Both paths same** — model articulates two paths that arrive at
  the same answer with different words. The two paths must lead to
  DIFFERENT answers; verify wrong_answer != final_answer.
- **Forced contrastive on direct questions** — model invents a
  wrong path for "What's the boiling point of water?". The
  `contrastive_useful: false` exit exists; verify it triggers on
  direct lookups.
- **Wrong "wrong"** — model labels the actually-correct path as
  wrong and vice versa. Sample low-stakes outputs against ground
  truth.
- **Generic deciding_contrast** — "the correct path uses correct
  logic". Reject any deciding_contrast that doesn't name a specific
  principle / misconception.

## Tuning Notes

- 模型差异：必须 frontier 模型或 reasoning-model. 中档模型在
  articulating plausible wrong path 上经常 strawman.
- 温度：`0.3`–`0.5`。两条路径需要 distinct framing，略高温度有助。
- 与 `cot/self-consistency-aggregator` 的关系：那张卡是 N 路径
  external 投票；本卡是 internal 一对路径 contrast。前者更稳但贵
  N 倍；后者更便宜但单次。混合策略：先本卡 contrastive 拿 first
  cut，再 self-consistency 投票确认。
- 与 `cot/step-back-prompting` 的关系：step-back 抽象到原理；本卡
  对照错误路径。两者都用于 "surface vs deep" 类问题，但工具不同。
- 与 `cot/verify-then-finalize` 的对比：verify-then-finalize check
  自己的答案；本卡构造错误对照来强化答案。前者后验，后者反向。
- contrastive_useful 阈值：典型 30-50% 问题受益（含 misconception
  trap 的）；50%+ 问题是直接 lookup，不应该用本卡。
- 用作 SFT 数据：(question, wrong_path, correct_path, contrast)
  四元组训练模型 anti-misconception 能力。比纯 (question, answer)
  对训出"知道为什么不是别的"的模型。

## Changelog

- `0.1.0` — Initial card.
