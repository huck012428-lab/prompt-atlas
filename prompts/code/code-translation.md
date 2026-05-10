---
id: code/code-translation
title: Code Translation Across Languages
version: 0.1.0
status: stable
direction: code
tags: [generation, structured-output, extraction]
audience: [app-builder, prompt-engineer, llm-trainer]
models: [frontier-closed, mid-tier-closed, open-source-large]
language: en
input_schema: structured
output_schema: structured-json
license: CC-BY-4.0
variables:
  - name: source_code
    description: The source code to translate.
    required: true
  - name: source_language
    description: Programming language of the input (e.g. "Python 3.11", "TypeScript", "Java 17").
    required: true
  - name: target_language
    description: Programming language to translate into (e.g. "Go", "Rust", "Kotlin").
    required: true
  - name: idiom_target
    description: One of "literal" (preserve structure even if non-idiomatic in target), "idiomatic" (rewrite to target-language idioms even if structure changes), "balanced" (idiomatic where natural, literal where idioms would obscure intent).
    required: true
---

> 🎯 **场景**：跨语言代码翻译（Python ↔ TypeScript ↔ Go ↔ Rust 等）。可选三种策略：保留原结构 / 按目标语言惯用法重写 / 平衡。输出含翻译代码 + 风险提示 + 行为差异警告。适合迁移、跨语言原型、教学。

## Quick Use

**Use when:** You want to translate code from one language to another, with explicit control over how aggressively to adopt the target language's idioms.
**Fill in:** `{{source_code}}` = the code; `{{source_language}}` = source lang+version; `{{target_language}}` = target lang; `{{idiom_target}}` = `literal` / `idiomatic` / `balanced`.
**You'll get:** Translated code, a list of behavioral differences (if any), risks, and untranslatable constructs. Output is JSON.

## Purpose

Translate code between programming languages with explicit handling
of cases where source-language constructs don't map cleanly to the
target. Used in cross-language migrations, building same-feature
prototypes in multiple languages, and teaching engineers a new
language by mapping from one they already know. Output is structured
so the translated code, behavioral differences, and untranslatable
constructs are separately addressable — important for review before
the translation is committed.

## Prompt

```text
You translate code from one programming language to another. Be
explicit about behavioral differences and constructs that don't map
cleanly.

Source code (in {{source_language}}):
{{source_code}}

Target language: {{target_language}}

Idiom target: {{idiom_target}}

Idiom target meanings:
- "literal"   : Preserve the source's structure step-by-step even if
                the result reads non-native in the target language.
                Choose when the user wants to verify behavioral
                equivalence one statement at a time.
- "idiomatic" : Rewrite using target-language idioms (Pythonic
                comprehensions → Rust iterators, Java getters →
                Kotlin properties, etc). Choose when the user wants
                production-quality target code.
- "balanced"  : Idiomatic where natural, literal where idioms would
                obscure intent or change error/concurrency semantics.
                Default for most use cases.

Rules:
1. Translate the code into target_language. Keep behavior equivalent
   where the languages allow.
2. Identify any places where exact behavioral equivalence is NOT
   possible (e.g. Python's GIL semantics → Go's goroutines, Java's
   checked exceptions → Kotlin's runtime exceptions, JS's number
   precision → Java's BigDecimal). Surface these as
   behavioral_differences with concrete one-sentence descriptions.
3. Identify any source constructs that simply CANNOT be translated
   (e.g. Python's `__getattr__` magic methods in Go, JavaScript's
   `eval` in Rust). Surface as untranslatable_constructs and explain
   the workaround if any.
4. Do NOT invent target-language libraries that may not exist.
   Prefer standard library where possible; if a third-party
   dependency is necessary, name it and flag in `dependencies_used`.
5. Preserve the source's identifier names where they don't violate
   target-language conventions; rename when conventions differ
   (snake_case ↔ camelCase ↔ PascalCase as appropriate).

Return ONLY this JSON object:
{
  "translated_code": "<target-language code as a single string with \\n line breaks>",
  "behavioral_differences": [
    {"source_construct": "<short>", "target_behavior": "<short>", "severity": "low" | "medium" | "high"}
  ],
  "untranslatable_constructs": [
    {"source_construct": "<short>", "reason": "<short>", "workaround": "<short or 'none'>"}
  ],
  "dependencies_used": ["<library name>"],
  "naming_conventions_applied": "<short note about renames, or empty>",
  "decision_basis": "<one sentence, <=30 words, no internal CoT>"
}
```

## Example

**Input:**

```text
source_code: |
  def find_max(numbers):
      if not numbers:
          return None
      return max(numbers)
source_language: "Python 3.11"
target_language: "Go"
idiom_target: "balanced"
```

**Expected output:**

```json
{
  "translated_code": "func FindMax(numbers []int) (int, bool) {\n    if len(numbers) == 0 {\n        return 0, false\n    }\n    maxVal := numbers[0]\n    for _, n := range numbers[1:] {\n        if n > maxVal {\n            maxVal = n\n        }\n    }\n    return maxVal, true\n}",
  "behavioral_differences": [
    {
      "source_construct": "Python returns None for empty input",
      "target_behavior": "Go returns (0, false) — the bool indicates presence; caller must check ok before using the int",
      "severity": "medium"
    },
    {
      "source_construct": "Python's max() works for any orderable type via duck typing",
      "target_behavior": "Go version is typed to []int specifically; for other element types you'd need generics or a separate function",
      "severity": "low"
    }
  ],
  "untranslatable_constructs": [],
  "dependencies_used": [],
  "naming_conventions_applied": "Renamed find_max to FindMax (Go exported convention).",
  "decision_basis": "Balanced translation: idiomatic Go (no max stdlib for int slices, returns ok-bool) but preserves the empty-input semantic."
}
```

## Failure Modes

- **Hallucinated APIs** — translated code calls methods or imports
  packages that don't exist in the target language. Detect by
  attempting to compile / type-check the output before accepting;
  reject if any imports fail to resolve.
- **Silent semantic drift** — translated code "works" on the example
  but has a subtle different behavior on an edge case (e.g. Python's
  copy-on-modify list vs JS's reference, divide-by-zero raising vs
  returning Infinity). Mitigation: rule 2 + per-language review
  checklist; chain with `code/code-eval-judge` using both source and
  target tests.
- **Idiom over-application on `literal`** — model rewrites despite
  user asking for literal preservation. Track outputs whose
  `naming_conventions_applied` field is non-empty when
  idiom_target=literal — those are likely violations.
- **Idiom under-application on `idiomatic`** — model produces
  syntactically-translated but ugly target code. Detect by sampling
  and checking whether basic target-language idioms (iterators in
  Rust, list comprehensions in Python target, ternary expressions
  where supported) appear when they should.
- **Missing untranslatable cases** — model translates Python's
  `__getattr__` into a normal Go method silently. The
  `untranslatable_constructs` field exists for this; if the source
  uses metaprogramming features the target lacks, expect entries.
- **Dependency invention** — flags "uses lodash" when lodash isn't
  needed, OR uses lodash without flagging in dependencies_used.
  Audit: every external import in translated_code MUST appear in
  dependencies_used.

## Tuning Notes

- 模型差异：frontier 模型 + 专门 code 模型表现明显更稳；中档模型在
  跨范式翻译（OO ↔ functional ↔ systems）上失败率高。
- 温度：`0.0`–`0.3`，翻译要求确定性。
- 语言对的难度梯度：
  - 同范式同 GC（Python ↔ JS / Java ↔ Kotlin）：相对容易
  - 跨 GC 边界（Python ↔ Rust）：需大量 untranslatable 解释
  - 跨范式（Java ↔ Haskell）：建议 idiom_target=idiomatic 否则会
    很别扭
- idiom_target 选择经验：日常 PR 用 balanced；性能敏感生产代码用
  idiomatic（人工再 review）；理解学习用 literal（保持步骤可对照）。
- 与 `code/code-eval-judge` 的关系：translation 后用 eval-judge 跑
  原 task 的测试在两种语言上是否给出一致结果，是验证 behavioral
  equivalence 的硬办法。
- 与 `code/code-explanation-generator` 的关系：translation 给出"代码
  的语言版本"，explanation 给出"代码的人类版本"。两者输入相同（一段
  代码），输出维度不同。
- 不要把 translation 输出直接 commit——尤其 untranslatable_constructs
  非空时，必须人工审 workaround 的正确性。
- 第三方依赖：本卡的 dependencies_used 是 hint，不替代真实的依赖
  审计（版本兼容、license 兼容、安全漏洞）。

## Changelog

- `0.1.0` — Initial card.
