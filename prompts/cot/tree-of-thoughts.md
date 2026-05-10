---
id: cot/tree-of-thoughts
title: Tree-of-Thoughts (branch + evaluate + prune)
version: 0.1.0
status: experimental
direction: cot
tags: [decomposition-cot, self-check, structured-reasoning, structured-output]
audience: [prompt-engineer, llm-trainer, ai-pm]
models: [frontier-closed, reasoning-model]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: question
    description: A reasoning task that benefits from exploring multiple approaches in parallel.
    required: true
  - name: branch_factor
    description: How many distinct approaches to explore at the root (small integer, typically 2 to 4).
    required: true
  - name: max_depth
    description: How many reasoning steps deep to expand each branch (small integer, typically 2 to 4).
    required: true
---

> 🎯 **场景**：Tree-of-Thoughts——并行探索多个**结构上不同**的解法分支，给每个分支打 promise 分，剪掉不靠谱的，从最有希望的叶子产出答案。适合有多种 plausible attack vector 的难题。

## Quick Use

**Use when:** A problem has multiple plausible reasoning paths and a single linear chain might miss the right one — combinatorial planning, search, design problems with trade-offs.
**Fill in:** `{{question}}` = the reasoning task; `{{branch_factor}}` = how many starting approaches to try (2-4); `{{max_depth}}` = how many steps to expand each branch (2-4).
**You'll get:** A structured tree of reasoning branches each scored on promise, the pruned dead-ends, and the final answer drawn from the most promising leaf. Output is JSON.

## Purpose

Solve a reasoning task by exploring multiple distinct approaches as
branches, evaluating each branch's promise, pruning the unpromising
ones, and committing to the most promising leaf — the Tree-of-Thoughts
technique. Used on tasks where a single linear chain risks committing
to a bad first step (combinatorial puzzles, design problems with
trade-offs, math problems with multiple plausible attack vectors).
Output is structured so each branch and its evaluation is independently
inspectable and a future implementation could replay or compose
trees.

This card collapses ToT's classical multi-call exploration into a
single prompt for cost reasons. For high-stakes use, consider
expanding into a true multi-call search loop where each branch is
generated and evaluated in its own call.

## Prompt

```text
You solve a reasoning task by exploring multiple distinct approaches
in parallel, then converging on the best one.

Question:
{{question}}

Branch factor (how many distinct starting approaches to try): {{branch_factor}}
Max depth (how many reasoning steps to expand each branch): {{max_depth}}

Steps:
1. Propose {{branch_factor}} GENUINELY DISTINCT starting approaches.
   Distinctness is the point — different framings, different
   decompositions, different solution methods. Do NOT propose
   superficial variations of the same approach.
2. For each branch, expand up to {{max_depth}} reasoning steps. At
   each step, briefly state what you concluded.
3. After expanding, evaluate each branch's "promise" on a 1-5 scale:
   - 5 = clearly leads to a correct, verifiable answer
   - 3 = plausible but uncertain or partial
   - 1 = dead end, contradicts the problem, or stuck
4. Prune branches with promise <= 2; mark them as dead ends with a
   reason.
5. From the surviving branch with highest promise, commit to a
   final_answer.
6. If no branch reaches promise >= 4, set "decision: insufficient"
   and recommend a different approach (more depth, more branches,
   or human input).

Return ONLY this JSON object:
{
  "branches": [
    {
      "id": "b1",
      "approach_summary": "<short description of the approach>",
      "steps": [
        {"step": 1, "conclusion": "<concrete conclusion at step 1>"},
        {"step": 2, "conclusion": "<concrete conclusion at step 2>"}
        /* up to max_depth */
      ],
      "promise": 1-5,
      "status": "active" | "pruned",
      "prune_reason": "<if pruned: short reason; else empty>"
    }
    /* one entry per branch */
  ],
  "best_branch_id": "<id of the chosen branch, or empty if insufficient>",
  "decision": "committed" | "insufficient",
  "final_answer": "<the answer chosen from the best branch, or empty if insufficient>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
question: "I have 9 coins, one of which is heavier than the other 8. Using a balance scale, what is the minimum number of weighings to identify the heavier coin?"
branch_factor: 3
max_depth: 3
```

**Expected output:**

```json
{
  "branches": [
    {
      "id": "b1",
      "approach_summary": "Pairwise comparison of all coins.",
      "steps": [
        {"step": 1, "conclusion": "Compare coins one-by-one needs up to 8 weighings — clearly not minimum."},
        {"step": 2, "conclusion": "Pruning at first step: this approach cannot beat divide-and-conquer."}
      ],
      "promise": 1,
      "status": "pruned",
      "prune_reason": "Linear comparison has worst-case 8 weighings; not minimum."
    },
    {
      "id": "b2",
      "approach_summary": "Halve the coins each weighing (4 vs 4, set aside 1).",
      "steps": [
        {"step": 1, "conclusion": "Weighing 1: 4 vs 4. If balanced, the leftover is heavy (1 weighing total)."},
        {"step": 2, "conclusion": "If unbalanced, take heavier 4. Weighing 2: 2 vs 2. If balanced doesn't apply (we know one is heavier among 4)."},
        {"step": 3, "conclusion": "Weighing 3: 1 vs 1 from heavy 2. So worst case 3 weighings."}
      ],
      "promise": 4,
      "status": "active",
      "prune_reason": ""
    },
    {
      "id": "b3",
      "approach_summary": "Split into thirds (3 vs 3, set aside 3).",
      "steps": [
        {"step": 1, "conclusion": "Weighing 1: 3 vs 3. If balanced, heavy is in the 3 set aside."},
        {"step": 2, "conclusion": "Now we have a known group of 3 containing the heavy coin."},
        {"step": 3, "conclusion": "Weighing 2: 1 vs 1 from those 3. If balanced, third is heavy. Total: 2 weighings worst case."}
      ],
      "promise": 5,
      "status": "active",
      "prune_reason": ""
    }
  ],
  "best_branch_id": "b3",
  "decision": "committed",
  "final_answer": "2 weighings",
  "decision_basis": "Ternary-split branch achieves 2 weighings worst-case, beating halving (3) and linear (8)."
}
```

## Failure Modes

- **Pseudo-distinct branches** — model produces N branches that are
  actually the same approach with cosmetic variation. Detect by
  comparing `approach_summary` across branches; if they paraphrase
  each other, the branching budget was wasted.
- **Premature pruning of correct branches** — model prunes the right
  approach at step 1 because it doesn't see ahead. Mitigation:
  enforce a minimum 2-step expansion before pruning is allowed; in
  practice, this is harder to enforce in a single prompt — for
  high-stakes use, switch to multi-call ToT.
- **Promise inflation** — every branch gets promise 4-5, defeating
  pruning. Track distribution of promise values; if std dev is low
  across diverse benchmark, the rubric is collapsing.
- **Hallucinated step conclusions** — model writes confident-sounding
  step conclusions that are actually wrong (especially in math /
  combinatorics). Mitigation: chain with `cot/verify-then-finalize`
  on the chosen branch's final_answer.
- **`decision: insufficient` over-trigger** — model gives up rather
  than commit. Track the rate; if >10% on benchmark, the rubric is
  over-cautious.
- **Branching cost explosion** — branch_factor=4, max_depth=4 is 16
  step conclusions in a single prompt — long outputs degrade
  attention. Cap product (branch_factor * max_depth) at ~12 to keep
  quality; for larger trees use multi-call.

## Tuning Notes

- 模型差异：必须 frontier 模型或 reasoning-model（o-系列、Claude
  extended-thinking）。中档模型在 distinct-branching 上几乎必然
  退化为 cosmetic 变体。
- 温度：`0.5`–`0.8` 用于 branch 多样性；evaluation 阶段建议另起一次
  低温调用（multi-call ToT）以避免高温采样污染评估。
- branch_factor / max_depth 选择：从 (3, 2) 起步；逐步加大。乘积
  超过 12 单 prompt 的效果会快速下降。
- 与 `cot/least-to-most-decomposition` 的关系：least-to-most 是
  linear chain（每步严格依赖前步）；本卡是 tree（多 branch 并行）。
  problem 是 compositional 但 path 唯一时用 least-to-most；problem
  有多个 plausible attack vector 时用本卡。
- 与 `cot/self-consistency-aggregator` 的关系：self-consistency
  在同一 chain 上多采样投票；本卡在多个**结构上不同**的 chain 间
  选择。对真正困难的问题，可以叠加：每个 branch 内部跑 self-
  consistency，再在 branches 之间用本卡的 promise 评估选 best。
- 与 `agent/plan-and-execute-planner` 的对比：plan-and-execute 是
  agent 工具层（每步对应 tool call）；本卡是纯推理层（每步是思考
  conclusion，不调工具）。形态相似但 domain 不同。
- 用作训练数据：本卡产出（包括 pruned branches）可以作为 reasoning
  preference data — 让模型学会哪些初始分支更值得展开。

## Changelog

- `0.1.0` — Initial card.
