---
id: sft/code-sft-pair-generator
title: Code SFT Pair Generator
version: 0.1.0
status: stable
direction: sft
tags: [instruction-tuning, generation, data-augmentation, structured-output]
audience: [sft-team, llm-trainer]
models: [frontier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: language
    description: Target programming language (e.g. "Python 3.11", "TypeScript", "Rust").
    required: true
  - name: difficulty_target
    description: One of "easy" (snippet-level), "medium" (function-level with tests), "hard" (multi-function refactoring or design).
    required: true
  - name: topic_seed
    description: A short topic / domain hint (e.g. "string manipulation", "REST API client", "concurrent task queue", "graph traversal"). Pass empty string for general.
    required: false
---

> 🎯 **场景**：生成 code-specific SFT 训练对——instruction 描述任务，response 给可运行代码 + 解释。可控难度、按 topic / language。比通用 response-generator 更适合 code task：保留正确性、include test idea、避免幻觉 API。

## Quick Use

**Use when:** You're building code SFT training data and need (instruction, response) pairs at controlled difficulty in a target language.
**Fill in:** `{{language}}` = target language; `{{difficulty_target}}` = `easy` / `medium` / `hard`; `{{topic_seed}}` = optional topic hint.
**You'll get:** A code SFT pair with instruction, response (code + brief explanation), test sketch, and quality flags. Output is JSON.

## Purpose

Generate code-specific (instruction, response) SFT pairs at
controlled difficulty in a target language. Each response includes
runnable code, a brief explanation, and a test sketch — three
things code SFT data should always have. Used in code-LLM training
data construction. Distinct from general `sft/response-generator`:
this card is code-aware (runnable, language-idiomatic, with tests)
and difficulty-controlled.

## Prompt

```text
You generate a code SFT training pair.

Language: {{language}}

Difficulty target:
{{difficulty_target}}

Topic seed (may be empty):
{{topic_seed}}

Difficulty meanings:
- "easy"   : Snippet-level. Single function or block, ~5-15 lines.
              Tests trivial.
- "medium" : Function-level. Multi-function design, ~15-50 lines.
              Tests cover happy path + 1-2 edge cases.
- "hard"   : Multi-function refactoring, design with constraints,
              ~50-150 lines. Tests cover multiple scenarios.

Rules:
1. Generate an instruction in plain English describing a task.
2. Generate a response that:
   - Is RUNNABLE code in the target language (no pseudocode).
   - Uses idiomatic patterns of the language.
   - Has 1-2 sentences of explanation BEFORE the code (intent +
     approach).
   - Does NOT use third-party libraries unless commonly-available
     and necessary; prefer standard library.
3. Include a test_sketch — pseudocode or test names showing what
   should be tested.
4. Self-flag risks:
   - "uses_external_api" : Code calls an external service.
   - "non_deterministic" : Output may vary (random, time-based).
   - "language_idiom_questionable" : Code works but isn't very
                                       idiomatic.
   - "fabricated_specific" : Code mentions specific things (URLs,
                              IDs) that don't exist.

Return ONLY this JSON object:
{
  "instruction": "<the instruction in plain English>",
  "response": "<explanation\\n\\n```language\\ncode\\n```>",
  "code_only": "<just the code without explanation>",
  "test_sketch": "<pseudocode or test names>",
  "estimated_loc": <integer>,
  "self_flagged_risks": ["<from list>"],
  "training_usable": true | false,
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
language: "Python 3.11"
difficulty_target: "medium"
topic_seed: "string manipulation"
```

**Expected output (abridged code for brevity):**

```json
{
  "instruction": "Write a function `slugify` that converts a string to a URL-safe slug: lowercase, replace whitespace with hyphens, remove non-alphanumeric characters except hyphens, and collapse consecutive hyphens. Handle Unicode characters by transliterating to ASCII where reasonable.",
  "response": "Here's a slugify function. The approach is: NFKD-normalize Unicode (separates diacritics), encode to ASCII (drops non-encodable), lowercase, then regex-clean whitespace and disallowed characters.\\n\\n```python\\nimport re\\nimport unicodedata\\n\\ndef slugify(text: str) -> str:\\n    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')\\n    text = text.lower()\\n    text = re.sub(r'[^a-z0-9\\\\s-]', '', text)\\n    text = re.sub(r'[\\\\s-]+', '-', text)\\n    return text.strip('-')\\n```",
  "code_only": "import re\\nimport unicodedata\\n\\ndef slugify(text: str) -> str:\\n    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')\\n    text = text.lower()\\n    text = re.sub(r'[^a-z0-9\\\\s-]', '', text)\\n    text = re.sub(r'[\\\\s-]+', '-', text)\\n    return text.strip('-')",
  "test_sketch": "test_basic: 'Hello World' → 'hello-world'\\ntest_unicode: 'Café Münchner' → 'cafe-munchner'\\ntest_special_chars: 'Hello, World!' → 'hello-world'\\ntest_consecutive_hyphens: 'a---b' → 'a-b'\\ntest_strip: '-hello-' → 'hello'",
  "estimated_loc": 8,
  "self_flagged_risks": [],
  "training_usable": true,
  "decision_basis": "Idiomatic Python with stdlib only; covers the common edge cases; reasonable medium-difficulty task."
}
```

## Failure Modes

- **Pseudocode disguised as code** — looks like code but won't run.
  Validate by ast.parse / language-specific parser before training.
- **Hallucinated APIs** — uses libraries / functions that don't
  exist. Mitigation: prefer stdlib in rules + post-validation.
- **Mismatched difficulty** — easy task at hard label. Verify
  estimated_loc matches difficulty band.
- **Test sketch drift** — test names that don't actually correspond
  to runnable tests. The sketch is informational; production
  pipeline should still write real tests.
- **Topic_seed ignored** — generates string manipulation when seed
  was "graph traversal". Track topic match.

## Tuning Notes

- 模型差异：frontier 模型 + code-specialized 模型显著优于通用模型。
- 温度：`0.4`–`0.7`. 多样性优先；后续 quality filter 过。
- 与 `sft/response-generator` 的关系：那张卡是通用 response gen；本卡
  是 code-specific gen，要求 runnable + tests + idiom check。
- 与 `code/code-eval-judge` 的关系：本卡产 (instruction, response)
  pair；那张卡 judge 候选代码是否完成任务。pipeline:本卡产 → eval-
  judge 验 → keep 通过的入训练集。
- 与 `sft/data-quality-filter` 的关系：filter 过 (instruction, response)
  pair；本卡产 code-specific pair。两者协同：本卡产 → quality-filter
  过滤 → eval-judge run tests → 入训练集。
- 高敏代码（auth / crypto / payments）：本卡产 SFT 数据建议跳过这些
  topic，或人工审核每条；模型容易产看似对但实际不安全的代码。

## Changelog

- `0.1.0` — Initial card.
