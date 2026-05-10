---
id: eval/pairwise-judge-with-position-bias-probe
title: Pairwise Judge with Position-Bias Probe
version: 0.1.0
status: stable
direction: eval
tags: [llm-judge, pairwise, comparative, scoring, structured-output]
audience: [eval-team, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: task_description
    description: One paragraph describing what the task is.
    required: true
  - name: response_a
    description: First candidate response.
    required: true
  - name: response_b
    description: Second candidate response.
    required: true
---

## Quick Use

**Use when:** You're running pairwise LLM-as-judge evaluation and want to detect / control for the well-known position bias (judge prefers whichever response is shown first).
**Fill in:** `{{task_description}}` = what the task was; `{{response_a}}` and `{{response_b}}` = the two responses to compare.
**You'll get:** A first-pass verdict, an instruction to re-run with positions swapped, and an interpretation rule for combining both runs into a robust verdict. Output is JSON.

## Purpose

Run a pairwise comparison while explicitly instrumenting for position
bias — the well-documented failure mode where an LLM judge prefers
whichever response was shown first (or sometimes last) regardless of
actual quality. This card is **half of a two-call protocol**: the
first call produces a verdict on (A, B); the caller then re-invokes
with swapped positions and uses this card's `position_bias_protocol`
to combine the two verdicts into a robust judgment. Output is
structured so per-task position-bias rates can be tracked across a
benchmark.

## Prompt

```text
You are a pairwise judge that is aware of, and instrumented for,
position bias. Score this single (response_a, response_b) ordering;
the caller will run a second pass with positions swapped and combine
the verdicts.

Task description:
{{task_description}}

Response A:
{{response_a}}

Response B:
{{response_b}}

Return ONLY this JSON object:
{
  "verdict": "a" | "b" | "tie",
  "confidence": "high" | "medium" | "low",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>",
  "swapped_call_instruction": "Re-invoke this card with response_a and response_b swapped. Then apply position_bias_protocol below to combine verdicts.",
  "position_bias_protocol": {
    "if_both_pick_same_letter": "Strong consensus on the WINNER. Treat the result as the verdict.",
    "if_picks_swap_with_positions": "Position bias detected — the judge picked first-position both times. Verdict is 'tie' regardless of either single call.",
    "if_one_run_is_tie": "Soft preference. Use the non-tie verdict but mark confidence as <=medium.",
    "if_picks_disagree_orthogonally": "Genuine disagreement: judge unstable on this pair. Mark as 'tie' or escalate to human."
  }
}

Calibration:
- Be willing to call ties when the responses are genuinely close.
  Forced binary decisions inflate position bias.
- Confidence "high" requires that you would expect the same verdict
  on a position-swap. If you suspect position influences your call,
  downgrade to "medium" or "low".
```

## Example

**Input:**

```text
task_description: "Explain in 2 sentences why the sky appears blue."
response_a: "The sky appears blue because of Rayleigh scattering: shorter blue wavelengths scatter more strongly off air molecules than longer red wavelengths, so we see more blue from every direction."
response_b: "Sky is blue because of the air. Blue color comes from the atmosphere reflecting sunlight."
```

**Expected output:**

```json
{
  "verdict": "a",
  "confidence": "high",
  "decision_basis": "A names Rayleigh scattering and the wavelength mechanism; B says 'reflecting' which is technically wrong.",
  "swapped_call_instruction": "Re-invoke this card with response_a and response_b swapped. Then apply position_bias_protocol below to combine verdicts.",
  "position_bias_protocol": {
    "if_both_pick_same_letter": "Strong consensus on the WINNER. Treat the result as the verdict.",
    "if_picks_swap_with_positions": "Position bias detected — the judge picked first-position both times. Verdict is 'tie' regardless of either single call.",
    "if_one_run_is_tie": "Soft preference. Use the non-tie verdict but mark confidence as <=medium.",
    "if_picks_disagree_orthogonally": "Genuine disagreement: judge unstable on this pair. Mark as 'tie' or escalate to human."
  }
}
```

(In the second call, with A and B swapped, the judge would still pick
the *response that names Rayleigh scattering*. Because the picks
"swap with positions" — both calls picked the substantively-correct
response by content rather than by position — that's the
`if_both_pick_same_letter` outcome: strong consensus, robust verdict.)

## Failure Modes

- **Caller skips the second call** — turning a position-bias-aware
  protocol into a regular pairwise judge. Mitigation: make the
  caller's loop unconditionally do both passes; do not let users
  short-circuit when the first call is "high" confidence.
- **Position-bias confusion** — caller misreads "picks swap with
  positions" as the success case. The protocol's wording is precise:
  if call 1 picks first-position AND call 2 picks first-position
  (different letters because positions swapped), THAT'S position
  bias. Verify by tracking pairs where both calls picked the same
  positional slot.
- **Tie inflation** — judge defaults to "tie" to avoid commitment.
  Track tie rate against a benchmark of known-decisive pairs; if
  >30% on clearly-different responses, the rubric is too forgiving.
- **Confidence/verdict mismatch** — high confidence but the second
  call disagrees orthogonally. Should be rare; if frequent, the
  judge is overconfident.
- **Format / length leakage into verdict** — judge prefers the
  longer or more-formatted response regardless of substance. The
  position bias protocol catches POSITION confounds but not
  LENGTH/FORMAT confounds — those need separate length-controlled
  evals.

## Tuning Notes

- 模型差异：strong judges (frontier-closed) 通常 position bias 在
  10-25% 量级；中档 judges 在 30-50%。本卡的双向运行协议把上述误差
  压到 5-10%（由 `if_picks_swap_with_positions` 触发的 tie 兜底）。
- 温度：`0.0`，judging 必须可重现；这是 position bias 测量本身的
  前提。
- 调用经济性：本卡需要 2x 调用次数。在 RLHF 数据建设的关键阶段
  （reward model 训练数据）值得；在快速 dashboard / 排行榜场景上
  可以只跑单向，但应当报告未控制 position bias。
- 与 `rlhf/pairwise-preference-labeler` 的关系：那张卡是 RLHF 数据
  建设的主力（HHH 三维度，单向调用）；本卡是 eval 端的 robust
  pairwise（双向调用 + bias 检测）。两者使用场景互补：rlhf-pairwise
  追求规模，本卡追求每次比较的可信度。
- 与 `rlhf/best-of-n-selector` 的关系：N>2 时用 best-of-N；N=2 且
  关心可信度时用本卡；N=2 且重视速度时用 rlhf-pairwise。
- 实施细节：caller loop 应该是确定性的（先 A/B 跑、再 B/A 跑），
  并对调用结果按 protocol 表合并，不让 LLM 自己决定怎么合并。
- 高敏 benchmark 上线前：跑 100-200 个人工 gold 样本测 raw position
  bias 率（单向调用与人工不一致率），用本卡测控后的不一致率。差值
  就是本卡的实际收益。

## Changelog

- `0.1.0` — Initial card.
