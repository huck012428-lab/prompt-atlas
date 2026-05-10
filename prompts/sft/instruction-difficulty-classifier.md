---
id: sft/instruction-difficulty-classifier
title: Instruction Difficulty Classifier
version: 0.1.0
status: stable
direction: sft
tags: [classification, scoring, instruction-tuning, structured-output]
audience: [sft-team, llm-trainer, eval-team]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: instruction
    description: A single instruction to classify by difficulty.
    required: true
  - name: target_model_class
    description: The target model class for which "difficulty" is judged. One of "frontier" (GPT-4 / Claude / Gemini class), "mid-tier" (mid-size proprietary), "open-source-large" (70B class), "open-source-small" (7B class).
    required: true
---

> 🎯 **场景**：把单条指令按"对目标模型的难度"分类。用于 curriculum SFT（先训简单后训难的）、benchmark 难度分层、active learning 候选挑选。"难"是相对的——给 7B 模型来说的难，frontier 模型可能 trivial。

## Quick Use

**Use when:** You're building curriculum training data, stratifying a benchmark, or selecting active-learning candidates and need a per-instruction difficulty label calibrated to a target model class.
**Fill in:** `{{instruction}}` = the instruction; `{{target_model_class}}` = `frontier` / `mid-tier` / `open-source-large` / `open-source-small`.
**You'll get:** A difficulty label, the dimensions that make it hard, and predicted success rate for the target class. Output is JSON.

## Purpose

Classify a single instruction by difficulty, calibrated to a specific
target model class. Difficulty is multi-dimensional (knowledge,
reasoning, formatting, length, ambiguity, multi-step) — different
instructions are hard for different reasons. Used in curriculum
training (start easy, progress hard), benchmark stratification, and
active-learning candidate selection. Output is structured so per-
dimension difficulty can be tracked across a dataset.

## Prompt

```text
You classify an instruction's difficulty for a specific model class.

Instruction:
{{instruction}}

Target model class:
{{target_model_class}}

Steps:
1. Identify difficulty dimensions present in this instruction:
   - "knowledge"     : Requires specific domain or factual knowledge.
   - "reasoning"     : Requires multi-step deduction / inference.
   - "math"          : Requires numerical computation.
   - "formatting"    : Requires specific output format / structure.
   - "length"        : Requires producing a long output (e.g. 1000+
                       words).
   - "ambiguity"     : Instruction has multiple valid interpretations.
   - "multi_step"    : Requires planning / decomposition.
   - "creative"      : Requires originality, not just retrieval.
   - "constraint"    : Has explicit hard constraints (length cap,
                       must include X, must avoid Y).

2. For each dimension present, rate intensity 1-3:
   - 1 = mild (a competent model handles fine)
   - 2 = moderate (some models struggle)
   - 3 = severe (most models fail without scaffolding)

3. Predict success rate for the target_model_class:
   - "high"   : >85% expected success
   - "medium" : 50-85%
   - "low"    : <50%
   - "near_zero" : <10% — likely fails

4. Aggregate: pick "easy" / "medium" / "hard" / "very_hard" overall:
   - "easy"      : success_rate=high AND no dimension at 3
   - "medium"    : success_rate=medium OR one dimension at 3
   - "hard"      : success_rate=low OR two+ dimensions at 3
   - "very_hard" : success_rate=near_zero OR three+ dimensions at 3

Return ONLY this JSON object:
{
  "difficulty": "easy" | "medium" | "hard" | "very_hard",
  "predicted_success_rate": "high" | "medium" | "low" | "near_zero",
  "dimensions": [
    {"name": "<dimension>", "intensity": 1-3, "why": "<short>"}
  ],
  "scaffolding_suggestions": ["<one short suggestion per item>; e.g. 'add a worked example', 'break into sub-questions'"],
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
instruction: "Write a 500-word personal essay reflecting on a time you failed, the lesson learned, and how it shaped your approach to challenges since. Use vivid sensory detail and avoid clichés."
target_model_class: "open-source-small"
```

**Expected output:**

```json
{
  "difficulty": "hard",
  "predicted_success_rate": "low",
  "dimensions": [
    {"name": "creative", "intensity": 3, "why": "Personal essay with vivid sensory detail requires originality + voice; small models often produce generic essays."},
    {"name": "length", "intensity": 2, "why": "500 words requires sustained coherence; small models drift in long generation."},
    {"name": "constraint", "intensity": 2, "why": "Constraints 'avoid clichés' + 'sensory detail' are stylistic; hard to verify and small models default to clichés."},
    {"name": "ambiguity", "intensity": 1, "why": "Mild — 'a time you failed' is open but not deeply ambiguous."}
  ],
  "scaffolding_suggestions": [
    "Provide 1-2 strong example essays as few-shot demonstrations.",
    "Break into a 3-step prompt: outline first, then draft, then revise.",
    "Lower length target to 300 words first to reduce drift."
  ],
  "decision_basis": "Creative + length + constraint dimensions all challenge a 7B model; expected low success without scaffolding."
}
```

## Failure Modes

- **Difficulty inflation** — every instruction marked "hard" or
  "very_hard". Track distribution; on a diverse benchmark expect
  roughly 30/40/25/5 easy/medium/hard/very_hard split.
- **Difficulty deflation** — same instruction marked easy across
  model classes despite obvious model-class effect. Sample outputs
  comparing same instruction at frontier vs open-source-small;
  difficulty should shift up at lower model class.
- **Dimension hallucination** — listing "math" intensity for an
  instruction with no math. Verify each listed dimension actually
  applies.
- **Generic scaffolding suggestions** — "improve the prompt" is not
  actionable. Reject vague suggestions.
- **Length / creative miscategorization** — short creative tasks
  marked hard purely because creative; long creative tasks marked
  easy. Length is independent of creativity; both contribute.

## Tuning Notes

- 模型差异：本卡的 difficulty estimation 对 model class 知识要求高
  (frontier 模型对 7B 模型能干什么的认识比对自己更难)。frontier
  judging mid-tier 和 small 通常稳；judging open-source-large 略漂。
- 温度：`0.0`，分类必须可重现。
- 与 `sft/data-coverage-analyzer` 的关系：那张卡产出含粗粒度
  difficulty_distribution；本卡是单条精分类。整套 SFT 数据建设流程：
  coverage 分析整体 → 找出某 category 缺难度档 → 用本卡精筛已有样本
  哪些是该档 → 用 self-instruct 生成补缺。
- curriculum training 用法：训练数据按 difficulty 排序，先 easy 后
  hard。本卡是给数据打 difficulty label 的工具。研究上 curriculum
  effects 不一定显著，但 active learning 上排序明确有用。
- 与 `eval/llm-judge-rubric-open-ended` 的关系：那张卡判输出质量；
  本卡判输入难度。互补——hard instructions 上低质量输出 expected，
  easy 上低质量是问题。
- scaffolding_suggestions 的下游：可以喂给 prompt-engineering pipeline
  自动构造 few-shot 版本。"add a worked example" 自动触发 example
  selection。

## Changelog

- `0.1.0` — Initial card.
