---
id: cot/uncertainty-quantification
title: Reasoning with Explicit Uncertainty Quantification
version: 0.1.0
status: experimental
direction: cot
tags: [structured-reasoning, self-check, scoring, structured-output]
audience: [prompt-engineer, llm-trainer, ai-pm]
models: [frontier-closed, reasoning-model]
language: en
input_schema: text
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: The question or task that requires reasoning, where uncertainty about steps should be made explicit.
    required: true
---

> 🎯 **场景**：让模型推理时**明确每一步的不确定度**——不是黑盒输出 + 一个总分，而是 sub-step 级粒度的 "this I'm sure of / this I'm guessing"。最终输出含 confidence interval。适合高敏决策、科学问答、多假设推理。

## Quick Use

**Use when:** You need not just an answer but a calibrated sense of which parts of the reasoning are solid vs guessed — for high-stakes decisions, scientific Q&A, or claims with downstream consequences.
**Fill in:** `{{question}}` = the question.
**You'll get:** Sub-steps each with its own confidence level + evidence type, a final answer with a confidence range, and a "biggest_unknown" identifier. Output is JSON.

## Purpose

Force the model to surface per-step uncertainty rather than collapse
all uncertainty into one final confidence number. Each reasoning
step gets labeled with confidence (high / medium / low) AND evidence
type (definitional, common knowledge, inferential, speculative). The
final answer carries a confidence range derived from the weakest
step. Used in scientific Q&A, legal reasoning, medical triage,
investment analysis — anywhere "I don't know what I don't know"
is itself the failure mode.

## Prompt

```text
You answer a question with EXPLICIT per-step uncertainty. Each
sub-step gets a confidence level AND an evidence type, so the
caller can see which parts of the reasoning are solid vs guessed.

Question:
{{question}}

Steps:
1. Decompose the reasoning into 2-6 sub-steps. Each sub-step must
   produce a concrete artifact (a fact, a number, an inference).

2. For EACH sub-step, label:
   - confidence: "high" | "medium" | "low"
     - high   = you know this with the same certainty you'd state
                a definition or arithmetic
     - medium = you're inferring from common-knowledge premises;
                small chance of being wrong
     - low    = you're guessing or interpolating; significant chance
                of being wrong
   - evidence_type:
     - "definitional"     = true by definition (e.g. "a triangle has
                            three sides")
     - "common_knowledge" = widely-known fact you can recall
     - "inferential"      = derived from prior steps or premises
     - "speculative"      = your best guess; you do not actually know

3. Compute the final answer's confidence range:
   - The range is BOUNDED BY the lowest-confidence sub-step that
     the final answer depends on.
   - If any depended-on step is "low", final confidence is "low to
     medium".
   - If any depended-on step is "medium", final confidence is
     "medium to high".
   - All depended-on steps "high" → final "high".

4. Identify "biggest_unknown" — the single sub-step whose
   uncertainty most affects the final answer. This is what a user
   should verify if they want to act on the answer.

Return ONLY this JSON object:
{
  "sub_steps": [
    {
      "id": "s1",
      "name": "<short label>",
      "result": "<concrete artifact>",
      "confidence": "high" | "medium" | "low",
      "evidence_type": "definitional" | "common_knowledge" | "inferential" | "speculative"
    }
  ],
  "final_answer": "<the answer>",
  "final_confidence": "high" | "medium-to-high" | "low-to-medium" | "low",
  "biggest_unknown": {
    "step_id": "<id of the most uncertainty-impactful step>",
    "what_to_verify": "<one sentence explaining what a user should verify>"
  },
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
question: "If I invest $10,000 in an S&P 500 index fund and historical average returns hold, what would it be worth in 30 years?"
```

**Expected output:**

```json
{
  "sub_steps": [
    {"id": "s1", "name": "S&P 500 historical average return", "result": "Approximately 10% per year nominal, ~7% real (inflation-adjusted), based on 100+ year history.", "confidence": "high", "evidence_type": "common_knowledge"},
    {"id": "s2", "name": "Compound growth formula", "result": "Future value = principal × (1 + r)^n", "confidence": "high", "evidence_type": "definitional"},
    {"id": "s3", "name": "Apply 10% nominal rate over 30 years", "result": "$10,000 × (1.10)^30 = $10,000 × 17.45 = ~$174,500 nominal", "confidence": "high", "evidence_type": "inferential"},
    {"id": "s4", "name": "Whether 'historical average return' will hold", "result": "Future returns may differ — past performance does not guarantee future returns. Range of plausible 30-year outcomes: $50K to $300K (real, inflation-adjusted).", "confidence": "low", "evidence_type": "speculative"}
  ],
  "final_answer": "Roughly $174,500 nominal under the historical 10% assumption, but the realistic range is wide ($50K-$300K real-dollar terms) given that historical averages are not predictions.",
  "final_confidence": "low-to-medium",
  "biggest_unknown": {
    "step_id": "s4",
    "what_to_verify": "Whether the historical 10% nominal / 7% real return is a reasonable expectation for the next 30 years; this is a forecasting question with structurally high uncertainty."
  },
  "decision_basis": "Math (s1-s3) is high-confidence; the forecast assumption (s4) is genuinely speculative, so final confidence is bounded by it."
}
```

## Failure Modes

- **Confidence inflation** — model marks every step "high" when it
  shouldn't. Track distribution; if low/medium rate <20% across a
  diverse benchmark, calibration is broken.
- **Confidence deflation** — model marks every step "low" to be
  cautious. Should be rare; if frequent, the rubric needs sharpening.
- **Evidence type confusion** — speculative steps marked
  "common_knowledge" or vice versa. Sample outputs and verify
  evidence_type matches the actual reasoning style.
- **Final confidence inconsistency** — final_confidence claims
  "high" while biggest_unknown is "low". Validate the rule logic
  at parse time.
- **Cosmetic biggest_unknown** — model picks a low-impact step as
  biggest_unknown. Should be the step whose uncertainty most
  changes the answer; sample and verify.
- **Hidden inference chains** — final answer depends on a step model
  didn't list. Audit by checking final_answer doesn't reference
  facts not in any sub_step.
- **Forecasting → high confidence** — model treats "what will
  happen" questions as having calculable answers. Step 4 in the
  example is the canonical case — forecast steps must be at most
  "medium" unless there's a concrete model.

## Tuning Notes

- 模型差异：本卡对 calibration 要求高——这是 LLM 的弱项。frontier
  模型 + reasoning-model（o-series, Claude extended-thinking）显著
  优于普通模型。中档模型常出现 confidence inflation。
- 温度：`0.0`，calibration 必须可重现。
- 评估方法：calibration plot——从 high/medium/low 标签和真实正确率
  画图。high-confidence 应当 >80% 准确，medium ~50-80%，low <50%。
  偏离即是 calibration 问题。
- 与 `cot/structured-reasoning-with-rationale-summary` 的关系：那张
  卡是一般性结构推理；本卡是带 calibration 的专版。简单题用前者
  够了；高敏决策 / forecasting / 跨知识领域问题用本卡。
- 与 `cot/verify-then-finalize` 的关系：verify-then-finalize 检查
  answer 是否过得了具体 check（算术 / 边界 / 矛盾）；本卡明示
  step-level uncertainty。互补——前者技术正确性，后者认知不确定性。
- 与 `eval/pointwise-quality-scorer` 的 confidence 字段的关系：
  那个是 judge 的自报置信度；本卡是被判模型的 step-level 置信度。
  judge calibration 和 model calibration 是两个独立问题，都需要。
- 高敏场景必备：医疗 / 法律 / 财务建议必须用 calibration-aware
  reasoning，不能给单个 yes/no 答案。本卡的 final_confidence +
  biggest_unknown 是给用户的"如何验证我的答案"的明确指引。
- 用作训练数据：human-labeled (question, answer, true_uncertainty)
  三元组可作 calibration 训练 SFT 数据；本卡产出可作 model
  self-calibration 训练的起点（再用人工或外部 knowledge 校准）。

## Changelog

- `0.1.0` — Initial card.
