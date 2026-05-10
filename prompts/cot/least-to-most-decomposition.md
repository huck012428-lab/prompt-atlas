---
id: cot/least-to-most-decomposition
title: Least-to-Most Decomposition
version: 0.1.0
status: stable
direction: cot
tags: [decomposition-cot, structured-reasoning, structured-output]
audience: [prompt-engineer, llm-trainer, ai-pm]
models: [frontier-closed, mid-tier-closed, open-source-large, reasoning-model]
language: en
input_schema: text
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: complex_question
    description: A complex question that benefits from being broken into easier sub-problems solved in order.
    required: true
  - name: max_subproblems
    description: Cap on how many sub-problems to break the question into (small integer, typically 2 to 5).
    required: true
---

## Quick Use

**Use when:** A complex problem can be solved by breaking it into a chain of strictly easier sub-problems where each can use earlier answers.
**Fill in:** `{{complex_question}}` = the original complex question; `{{max_subproblems}}` = a small number, typically 2 to 5.
**You'll get:** An ordered list of sub-problems each with its answer, why it's easier, and dependency edges, plus the final answer. Output is JSON.

## Purpose

Solve a complex question by first breaking it into a sequence of easier
sub-problems, where each sub-problem is **strictly easier** than the
original and each later sub-problem can use the answers of earlier ones
as known facts — the least-to-most prompting technique. Used on
problems that resist single-pass reasoning: compositional QA, multi-
step word problems, programs whose correctness depends on intermediate
results. Output is structured so each sub-problem and its answer is
independently inspectable, and the final answer is traceable back
through the chain.

## Prompt

```text
You solve a complex question by breaking it into easier sub-problems
and solving them in order. Each sub-problem must be EASIER than the
original question, and each later sub-problem may use earlier
answers as established facts.

Complex question:
{{complex_question}}

Maximum number of sub-problems:
{{max_subproblems}}

Rules:
1. Use 2 to {{max_subproblems}} sub-problems. Fewer is better when
   the question can be split into fewer truly easier pieces.
2. Each sub-problem must be a self-contained question whose answer
   is concrete (a number, a name, a short phrase, a labeled
   classification — not an essay).
3. The first sub-problem must be answerable WITHOUT any of the later
   sub-problems' answers.
4. Each subsequent sub-problem may reference earlier answers using
   the placeholder syntax `[answer of subproblem N]` in its question.
5. The final sub-problem's answer must be the answer to the original
   complex question, OR the synthesis step at the end must explicitly
   combine sub-problem answers into the final answer.
6. Do NOT introduce facts not present in the complex question and not
   derivable from common knowledge. If the question lacks information
   to be answerable, set "decomposable: false" and stop.

Return ONLY this JSON object:
{
  "decomposable": true | false,
  "infeasibility_reason": "<if decomposable=false: what is missing; else empty string>",
  "subproblems": [
    {
      "id": "sp1",
      "question": "<sub-problem question>",
      "depends_on": [],
      "answer": "<concrete answer>",
      "why_easier": "<one short phrase: how this is easier than the main question>"
    },
    {
      "id": "sp2",
      "question": "<sub-problem question, may reference earlier answers via [answer of sp1]>",
      "depends_on": ["sp1"],
      "answer": "<concrete answer>",
      "why_easier": "<...>"
    }
    /* ... */
  ],
  "final_answer": "<the answer to the original complex question>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
complex_question: "A bookstore sold 30% more books in March than in February. February sales were 20% lower than January's 1000 books. How many books did the bookstore sell in March?"
max_subproblems: 3
```

**Expected output:**

```json
{
  "decomposable": true,
  "infeasibility_reason": "",
  "subproblems": [
    {
      "id": "sp1",
      "question": "If January sales were 1000 books and February sales were 20% lower, how many books were sold in February?",
      "depends_on": [],
      "answer": "800",
      "why_easier": "Direct percentage subtraction from a given number; no chained dependency."
    },
    {
      "id": "sp2",
      "question": "If February sales were [answer of sp1] and March sales were 30% higher than February, how many books were sold in March?",
      "depends_on": ["sp1"],
      "answer": "1040",
      "why_easier": "One percentage operation given a known starting value."
    },
    {
      "id": "sp3",
      "question": "What is the answer to the original question, given the March sales computed in sp2?",
      "depends_on": ["sp2"],
      "answer": "1040",
      "why_easier": "Trivial restatement of sp2's result as the final answer."
    }
  ],
  "final_answer": "1040",
  "decision_basis": "Decomposed the chained percentage problem into Feb-from-Jan and Mar-from-Feb steps, each a single percentage operation."
}
```

## Failure Modes

- **Cosmetic decomposition** — model produces sub-problems that are
  not actually easier than the original ("sub-problem 1: solve the
  whole problem"). Mitigation: the `why_easier` field exists to
  surface this; in audits, reject entries where `why_easier` is
  vague or where solving sp1 requires solving the original.
- **Forward-reference cheating** — sub-problem 1 covertly assumes
  the answer to a later sub-problem. Detect by hiding later sub-
  problems and checking sp1 still has enough information. Mitigation:
  rule 3 explicit; in pipelines, run a strict "answer sp1 alone first"
  check.
- **Missing dependency edges** — sub-problem 2 uses sp1's answer in
  its question but `depends_on` is empty. Validate the dependency
  graph against the placeholder references in `question`.
- **Trivial final step inflation** — model adds a final sub-problem
  that just restates the previous answer (as in the example above —
  this is acceptable when the previous answer IS the final answer,
  but should not pad solving 2-step problems into 5 steps).
- **Hallucinated knowledge** — sub-problem assumes a fact not in the
  question (e.g. "if there are 24 hours in a day"). Some common
  knowledge is fine; novel domain facts are not. Mitigation: rule 6;
  audit by sampling and checking that every numeric / factual claim
  in sub-problems traces back to the original question.
- **Uneven difficulty** — first sub-problem is "easier" but the
  second is harder than the original (e.g. it requires combining
  multiple unrelated facts). Decomposition only helps if each piece
  is genuinely easier; track per-sub-problem accuracy on a benchmark
  to detect this.

## Tuning Notes

- 模型差异：本卡对 frontier 模型受益最大，因为分解和逐步求解都需要
  模型能在中间步骤上保持 grounded。中档模型在 cosmetic decomposition
  和 forward-reference cheating 上失败率较高。
- 温度：`0.0`–`0.3`。decomposition 一致性优先。
- 与 `cot/structured-reasoning-with-rationale-summary` 的关系：
  rationale-summary 卡是单一推理路径，按"自然顺序"思考；本卡强制
  least-to-most 拆分，对 compositional 任务更稳。简单题用前者；
  题目明显复合或多跳时用本卡。
- 与 `cot/self-consistency-aggregator` 的关系：互补——self-consistency
  通过多采样降方差，本卡通过结构化分解提升单路径正确率。两者可叠加
  （每条 self-consistency path 内部用 least-to-most），但 latency 翻
  N 倍，实际生产中先单独 A/B 看哪个收益大。
- 与 `agent/plan-and-execute-planner` 的对比：plan-and-execute 是
  agent 工具调用层面的计划（每步对应一个 tool call）；本卡是纯推理
  层面的分解（每步对应一个推理子问题，不调工具）。形态相似但应用
  域不同。
- max_subproblems 选择：4 步以内最稳；>4 步通常说明问题应该被进一步
  分解为子任务而非子问题。
- decomposable=false 的样本：通常说明问题确实信息不足，不要硬把它
  们塞进训练集；可作为"unanswerable from context"类样本的来源。

## Changelog

- `0.1.0` — Initial card.
