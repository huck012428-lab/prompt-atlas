---
id: sft/style-transfer
title: Style Transfer (rewrite text in target style)
version: 0.1.0
status: stable
direction: sft
tags: [generation, data-augmentation, structured-output]
audience: [sft-team, llm-trainer, app-builder]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: source_text
    description: The text to be rewritten in a different style.
    required: true
  - name: target_style
    description: The target style description (e.g. "formal academic", "casual SMS", "Hemingway terse", "1950s noir narrator", "code documentation").
    required: true
  - name: preserve_meaning_strict
    description: One of "true" (semantic content must be preserved exactly) or "false" (light meaning shifts acceptable for naturalness in target style).
    required: true
---

> 🎯 **场景**：把一段文本改写成目标风格——formal ↔ casual、academic ↔ SMS、各种特定 voice。带"是否严格保留语义"开关。SFT 风格化数据建设、A/B 文案生成、跨场景文本适配的通用工具。

## Quick Use

**Use when:** You want to rewrite text into a specific style (formal/casual, terse/elaborate, persona-flavored) while controlling whether semantic meaning must be preserved exactly.
**Fill in:** `{{source_text}}` = the original text; `{{target_style}}` = style description; `{{preserve_meaning_strict}}` = `true` / `false`.
**You'll get:** The rewritten text, a fidelity score for meaning preservation, and a list of any changes that altered meaning. Output is JSON.

## Purpose

Rewrite text into a target style, controllable on whether semantic
content must be preserved exactly or can shift slightly to feel
natural in the target style. Used for SFT data augmentation
(generate variants from one source), A/B test copy generation,
cross-channel adaptation (turn formal docs into chat replies), and
voice training data. Output is structured so meaning preservation
can be audited.

## Prompt

```text
You rewrite a piece of text into a target style.

Source text:
{{source_text}}

Target style:
{{target_style}}

Preserve meaning strictly:
{{preserve_meaning_strict}}

Strictness meanings:
- "true"   : The rewritten text must convey the SAME information as
              the source. No facts dropped, no facts added.
              Connotations may differ; denotation must match.
- "false"  : Some semantic shift is acceptable if it makes the
              target style feel natural (e.g. a casual rewrite of
              a formal text may drop hedges; a noir rewrite of
              technical text may add atmosphere). Flag any meaningful
              shifts.

Rules:
1. Apply the target style consistently throughout the rewrite.
2. Track which dimensions of style you changed (voice, tone,
   sentence length, vocabulary register, sentence structure).
3. If preserve_meaning_strict=true and a target-style application
   would require dropping/adding info, set
   "fidelity_compromise": true and EITHER refuse to drop the info
   (apply style only on what doesn't conflict) OR set rewrite to
   the closest faithful version.
4. If preserve_meaning_strict=false, list any meaningful shifts in
   `meaning_shifts` so the caller can audit.
5. Don't fake style — if the target style is "1950s noir narrator"
   and you can't actually produce that, set
   "stylistic_capability_limited": true.

Return ONLY this JSON object:
{
  "rewritten_text": "<the styled rewrite>",
  "style_dimensions_changed": ["<dimension>", "..."],
  "meaning_fidelity": "high" | "medium" | "low",
  "meaning_shifts": [
    {"shift": "<short description>", "intentional": true | false}
  ],
  "fidelity_compromise": true | false,
  "stylistic_capability_limited": true | false,
  "limitation_note": "<if capability_limited=true: which aspects you couldn't render; else empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
source_text: "The committee has determined that pursuant to Section 4.2(c), the proposal will be remanded to subcommittee for additional review. Final disposition is anticipated within thirty business days."
target_style: "casual SMS to a friend"
preserve_meaning_strict: "true"
```

**Expected output:**

```json
{
  "rewritten_text": "btw the committee bumped your proposal back to the subcommittee under 4.2(c) — they'll have a final answer in ~30 business days",
  "style_dimensions_changed": ["voice (casual)", "register (SMS shorthand)", "sentence length (longer formal sentences merged into one)", "tone (warm informal)"],
  "meaning_fidelity": "high",
  "meaning_shifts": [],
  "fidelity_compromise": false,
  "stylistic_capability_limited": false,
  "limitation_note": "",
  "decision_basis": "Cast the bureaucratic content into SMS-style abbreviation but kept all four facts (committee action, section reference, what happens next, timeline)."
}
```

## Failure Modes

- **Style on style only** — rewrite changes vocabulary but keeps
  the source's structure verbatim. Real style transfer changes
  sentence structure and rhythm too. Track average sentence-length
  delta; if near zero, the transfer is shallow.
- **Information drift on strict mode** — rewrite drops a sentence
  to fit the target style under strict preservation. The
  `fidelity_compromise` flag is the safety net; audit by sampling.
- **Hallucinated info on loose mode** — rewrite adds details (a
  number, a name) not in source. `meaning_shifts` should list
  these; verify each entry doesn't add concrete facts.
- **Style cosplay** — rewrite uses target style's vocabulary
  superficially but reads as parody. For specific voices ("Hemingway",
  "1950s noir"), audit a sample with someone familiar with the
  target voice; if it's parody-level, downgrade meaning_fidelity
  expectations.
- **Capability over-claiming** — model attempts a target style it
  can't actually produce well (e.g. a non-Mandarin model rewriting
  to Mandarin internet slang). The `stylistic_capability_limited`
  flag exists for this; encourage honest reporting.
- **Format leak** — rewrite preserves source's bullet structure when
  target is SMS, or vice versa. Sentence structure and format are
  part of style; rewrite should adapt them.

## Tuning Notes

- 模型差异：本卡对 model 风格写作能力高度依赖。frontier 模型在
  varied target styles 上稳定；中档模型对小众或文化特定风格（古文、
  方言、特定时代风格）完成度低。
- 温度：`0.5`–`0.8`，style 需要写作灵活性。
- target_style 设计：**具体描述** > **简单标签**。"casual" 不如
  "casual SMS to a close friend, abbreviations OK, no emoji";后者
  让模型有更明确的应用对象。
- preserve_meaning_strict 选择经验：
  - **strict**：法律 / 医疗 / 财务文本风格化；事实必须不动。
  - **loose**：营销文案 A/B；强调情感的场景；creative writing。
- 与 `sft/persona-controlled-response` 的关系：persona 是"完整的
  voice + 行为规约"；style 是"单一维度的写作风格"。前者更复杂，
  后者更聚焦。短期任务通常用 style，长期产品用 persona。
- 与 `sft/instruction-variant-expander` 的关系：那张卡同语义同任务
  改写指令；本卡同语义不同风格改写文本。两者可串联——先 style
  改写一批样本，再用 variant-expander 扩成不同 instruction wording。
- 用作 SFT 数据：(source, target_style, rewrite) 三元组可作为风格
  转换任务的训练数据，让模型学会按 prompt 切换风格。
- 不要用本卡做 fact rewriting 或 stance shifting——它是风格层的
  工具，不是观点 / 立场层的工具。

## Changelog

- `0.1.0` — Initial card.
