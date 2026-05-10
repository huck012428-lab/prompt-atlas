---
id: eval/rubric-generator
title: Domain-Specific Rubric Generator
version: 0.1.0
status: experimental
direction: eval
tags: [rubric, generation, structured-output]
audience: [eval-team, ai-pm, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: task_description
    description: One paragraph describing the task being evaluated.
    required: true
  - name: success_criteria_hint
    description: One or two sentences from the task owner about what "good" looks like (vibe is fine — this card formalizes it). Pass empty string if you only have the task description.
    required: false
  - name: n_dimensions
    description: How many scoring dimensions the rubric should have (small integer, typically 3 to 6).
    required: true
---

> 🎯 **场景**：给一个新任务自动生成定制化打分 rubric——每个维度有 1-5 分的具体描述（不是空话）、有明确边界条件、没有重叠。生成后直接喂给 `eval/pointwise-quality-scorer` 等卡当 dimensions 用。给"我要评估 X"省去手写 rubric 的工作。

## Quick Use

**Use when:** You're starting a new evaluation task and want a structured rubric (with concrete level descriptions per dimension) instead of writing it by hand.
**Fill in:** `{{task_description}}` = paragraph describing the task; `{{success_criteria_hint}}` = optional vibe-level hint about "good"; `{{n_dimensions}}` = how many dimensions (3-6).
**You'll get:** A rubric with N dimensions, each with a 1-5 anchor description (what does a 1 vs 3 vs 5 look like) plus dimension boundaries. Output is JSON, ready to feed into a pointwise judge.

## Purpose

Generate a structured evaluation rubric tailored to a specific task,
with concrete descriptions of what each score level looks like
(1, 3, 5 anchors at minimum). Used as the front step of standing up
a new evaluation: instead of an eval-team member writing 5 dimensions
× 5 levels × ~30 words = 750 words of rubric prose by hand, this card
produces a first draft they can edit. Output is structured so the
rubric can be passed directly into `eval/pointwise-quality-scorer`
or `eval/llm-judge-rubric-open-ended` (if reduced to 4 fixed
dimensions) or used as a checklist by human evaluators.

## Prompt

```text
You generate a domain-specific evaluation rubric. The rubric will be
used to score outputs of a specific task. Quality bar: each dimension
must be distinct from the others, and each level (1, 3, 5) must have
a concrete description that a human evaluator could apply to a
real output.

Task description:
{{task_description}}

Success criteria hint (may be empty):
{{success_criteria_hint}}

Number of dimensions:
{{n_dimensions}}

Rules:
1. Each dimension must capture a distinct quality of the output. If
   two dimensions could often score together (e.g. "factuality"
   and "accuracy"), merge them or split into different facets.
2. For each dimension, provide concrete descriptions for level 1, 3,
   and 5. Levels 2 and 4 are interpolations of adjacent anchors and
   don't need explicit anchors.
3. Each level description should reference the task's specific
   content where possible. Generic "5 = excellent, 1 = poor" is
   not acceptable.
4. Identify any dimensions that are NOT applicable to this task and
   warn (e.g. "factuality" doesn't apply to a poetry-writing task).
5. If a useful evaluation cannot be constructed for this task in
   {{n_dimensions}} dimensions, set "feasible: false" and explain.

Return ONLY this JSON object:
{
  "feasible": true | false,
  "infeasibility_reason": "<if feasible=false: why; else empty>",
  "dimensions": [
    {
      "name": "<short_name in snake_case>",
      "description": "<one-sentence description of what this dimension measures>",
      "level_anchors": {
        "1": "<concrete description of a level-1 output>",
        "3": "<concrete description of a level-3 output>",
        "5": "<concrete description of a level-5 output>"
      },
      "boundary_with_others": "<one short note about how this dimension is distinct from the others — empty for single-dimension rubrics>"
    }
    /* exactly n_dimensions entries */
  ],
  "weighting_recommendation": {
    "<dim_name>": <weight float, default 1.0>
    /* one entry per dimension; floats summing roughly to n_dimensions */
  },
  "calibration_advice": "<one or two sentences: what to spot-check on a small sample before relying on this rubric>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
task_description: "Customer support agents respond to user complaint emails about delayed orders. Responses must acknowledge the issue, provide a status update, and offer either a refund or a replacement."
success_criteria_hint: "Friendly but not over-apologetic; doesn't fabricate timelines; ends with a clear next step."
n_dimensions: 4
```

**Expected output:**

```json
{
  "feasible": true,
  "infeasibility_reason": "",
  "dimensions": [
    {
      "name": "issue_acknowledgment",
      "description": "Does the response specifically acknowledge the customer's order delay (not just generic 'we're sorry')?",
      "level_anchors": {
        "1": "Generic apology with no reference to the order or delay; or no apology at all.",
        "3": "Acknowledges the delay generically ('we know your order is late') but does not name the order or quote specifics.",
        "5": "Names the order or quotes a specific from the customer's email ('your March 14 order #4421') and states the actual delay length."
      },
      "boundary_with_others": "Distinct from completeness: this is about whether the issue is named, not whether all required info is present."
    },
    {
      "name": "completeness",
      "description": "Does the response contain all three required elements: status update, resolution option (refund or replacement), and next step?",
      "level_anchors": {
        "1": "Missing two or more of the three required elements.",
        "3": "All three present but at least one is vague (e.g. 'we're working on it' as the status update).",
        "5": "All three present with concrete content: a real status, a clear refund/replacement choice, and a specific next step."
      },
      "boundary_with_others": "Completeness is structural (are the three elements there); accuracy is about correctness of those elements."
    },
    {
      "name": "factual_safety",
      "description": "Does the response avoid fabricated specifics (delivery dates, refund timelines, carrier names) the agent doesn't actually know?",
      "level_anchors": {
        "1": "Contains specific claims the agent cannot verify (invented delivery dates, fake tracking numbers).",
        "3": "Mostly safe but uses qualified guesses without flagging uncertainty ('it should arrive Tuesday').",
        "5": "Specific where verifiable (real timelines, real refund SLAs); explicitly acknowledges uncertainty where it exists."
      },
      "boundary_with_others": "Factual_safety is about hallucination; tone is about how the message reads. A response can be safe but cold."
    },
    {
      "name": "tone",
      "description": "Is the tone friendly, customer-respecting, and proportionate to the issue (not over-apologetic, not dismissive)?",
      "level_anchors": {
        "1": "Cold, dismissive, or accusatory; OR effusively apologetic to the point of seeming insincere.",
        "3": "Neutral and professional, neither warm nor cold.",
        "5": "Warm and respectful without over-apologizing; treats the customer as a competent adult."
      },
      "boundary_with_others": "Tone is independent of factual_safety and completeness — a tone-perfect response can still hallucinate or miss elements."
    }
  ],
  "weighting_recommendation": {
    "issue_acknowledgment": 0.8,
    "completeness": 1.2,
    "factual_safety": 1.5,
    "tone": 0.5
  },
  "calibration_advice": "Run on 30 known-good and 30 known-bad past responses; check that level-5 outputs cluster on known-good and that the four dimensions don't strongly correlate (Pearson < 0.6 between any pair).",
  "decision_basis": "Four distinct customer-support dimensions with concrete anchors; factual_safety weighted highest because hallucinations cause real customer harm."
}
```

## Failure Modes

- **Generic anchors** — level descriptions like "5 = excellent, 1 =
  bad" with no task-specific content. Reject any anchor under ~10
  words or that doesn't reference the task. The rubric is for
  evaluators, not a coloring book.
- **Overlapping dimensions** — `factuality` and `accuracy` defined
  separately such that they always score together. Audit by sampling
  outputs and checking inter-dimension correlation; >0.8 pairwise is
  redundancy. The `boundary_with_others` field exists to surface this.
- **Missing the actual hard part** — task is "explain something
  technical to a layperson" and the rubric covers factuality but not
  accessibility. The success_criteria_hint exists to nudge specifics;
  if hint is empty, expect generic results.
- **Unactionable weighting** — recommended weights all 1.0 with no
  rationale. Mitigation: track whether weights vary; if weights are
  uniform across diverse benchmarks, the model isn't engaging with
  the task's actual priorities.
- **Forced n_dimensions** — model produces 6 dimensions when 3 would
  suffice, splitting one concept into 3 closely-related variants.
  Track inter-dimension correlation; if 2 split dimensions correlate
  >0.85, the split was forced.
- **Calibration_advice vagueness** — "test it on some examples".
  Reject; advice must name a concrete check (sample size, criterion).

## Tuning Notes

- 模型差异：必须 frontier 模型。生成 task-specific concrete anchors
  需要 deep task understanding；中档模型容易回到 generic 维度名
  （factuality / coherence / completeness 通用四件套）。
- 温度：`0.3`–`0.6`。rubric 设计需要一些"如何把任务拆解"的创造性。
- n_dimensions 选择：3 维度适合简单任务、benchmark eval；5-6 维度
  适合多面任务（chat helpfulness、复杂代码生成等）。超过 6 通常意味
  着应该改用 multi-rubric（多个独立 3-4 维 rubric）。
- 与 `eval/pointwise-quality-scorer` 的关系：本卡产 rubric，那张卡用
  rubric 打分。生成-使用闭环。`scoring_dimensions` 字段直接用本卡
  输出的 dimensions[].name 即可。
- 与 `eval/llm-judge-rubric-open-ended` 的关系：那张卡有**固定** 4
  维度（factuality/instruction-following/coherence/completeness）
  适合开放式输出；本卡是 task-specific 自定义维度，适合特定业务。
  两者不冲突——简单 case 用前者，定制 case 用后者。
- 上线流程：本卡产 rubric → 人工 review 编辑 → calibration_advice
  里建议的 spot check → 上 dashboard。**不建议**直接把生成的 rubric
  推到生产打分，先人工编辑。
- 用作训练数据：(task, rubric) 对可作为 SFT 数据，让模型学会"看到
  任务就给出合理 rubric"，对自动化 eval 流水线建设有用。
- 不要省略 calibration：task-specific rubric 上线前必须用人工 gold
  样本 calibrate。`calibration_advice` 字段是模型给的建议，不是
  替代。

## Changelog

- `0.1.0` — Initial card.
