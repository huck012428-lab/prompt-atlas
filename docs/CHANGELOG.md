# Changelog

All notable changes to prompt-atlas are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/) at
the **repository** level. Individual Prompt Cards carry their own
`version` field and changelog inside the card frontmatter / body.

## [Unreleased]

Post-v0.1.0 polish + expansion. Will become v0.1.1 (or v0.2.0 if breaking
schema changes accumulate).

### Added

#### Beginner-friendly experience
- `docs/QUICKSTART.md` — 5-minute walkthrough for non-technical users
  (covers what `{{variable}}` means, what JSON output means, where to
  find the right card). Bilingual.
- README "I want to..." section — 38 user-facing goals mapped to
  exact card paths, grouped by intent.
- `## Quick Use` section is now a required body section on every
  card. Three lines (`Use when` / `Fill in` / `You'll get`) in plain
  English. Required-section list grew from 6 to 7; `validate.py`
  enforces it.
- `INDEX.md` "Use when" column auto-extracted from each card's
  Quick Use line.

#### New Prompt Cards (6)
- `rag/chunk-summarizer-for-retrieval` — produce search-friendly
  summaries of long document chunks for retrieval indexing.
- `agent/sub-task-delegator` — multi-agent foundation: split a
  complex task across specialized workers with explicit input/output
  contracts and dependency edges.
- `rlhf/red-team-prompt-generator` — defensive safety probe
  generator (refuses sexual_minors category outright; embeds
  expected refusal posture in each probe).
- `multimodal/chart-table-extractor` — extract structured data from
  chart, plot, and table images with per-data-point confidence.
- `cot/tree-of-thoughts` — explore multiple distinct reasoning
  branches, evaluate, prune.
- `eval/pairwise-judge-with-position-bias-probe` — pairwise judge
  with explicit two-call position-bias detection protocol.
- `sft/conversation-sft-pair-generator` — multi-turn conversation
  SFT data generator with explicit multi-turn-behavior coverage.
- `sft/few-shot-example-selector` — pick best K demonstrations from
  a candidate pool for a target query, ordered for primacy effect.
- `eval/multi-turn-dialogue-judge` — judge multi-turn dialogues
  with per-turn and conversation-level scoring.
- `rag/context-compression` — compress retrieved passages into a
  smaller question-tailored context with verbatim spans and source
  citations.

#### New `code` direction (5 cards)
- `code/code-review-checklist` — structured per-dimension code review
  (correctness / readability / performance / security / testability /
  idiomaticity) with severity-tagged findings and approve / request-
  changes / comment-only verdict.
- `code/test-case-generator` — generate test specs for a function with
  explicit happy-path / edge-case / error-handling / boundary /
  regression coverage and per-test priority.
- `code/code-explanation-generator` — audience-calibrated code
  explanation (junior / senior / non-technical / domain-expert) with
  key concepts and likely confusion points.
- `code/code-eval-judge` — judge candidate code against a task
  description, optional reference, and optional test cases. Strict
  security gate: security<=2 cannot pass.
- `code/refactor-suggestion` — concrete refactor suggestions oriented
  toward a single goal (readability / performance / testability /
  modularity / type_safety) with behavior-change-risk and
  test-breakage-risk estimates.

Vocabulary additions: `code` direction; tags `code-review`,
`test-generation`, `documentation`.

#### Round-balance expansion (6 cards across 6 directions)
- `code/code-translation` — translate code between languages with
  literal / idiomatic / balanced strategies; flags behavioral
  differences and untranslatable constructs.
- `agent/clarification-asker` — front-door of agent loops: decide
  proceed / clarify / out_of_scope on ambiguous goals; ask exactly
  one high-value clarifying question.
- `cot/step-back-prompting` — abstract a question into a principle
  question, answer the principle, then apply back to the original.
- `eval/rubric-generator` — generate a domain-specific scoring rubric
  with concrete level-1/3/5 anchors and weighting recommendation.
- `multimodal/document-layout-analyzer` — identify regions on a
  document page (title / body / table / figure / caption / footer
  etc.) with reading order and hierarchy.
- `rlhf/refusal-calibration-probe` — diagnose whether a response is
  appropriately calibrated to prompt safety: catches over_refusal
  on benign prompts AND under_refusal on unsafe prompts.

Per-direction now: rag 8, eval 8, agent 7, sft 6, code 6, cot 6,
multimodal 6, rlhf 6. Total 53. All directions ≥6.

#### Bilingual at-a-glance (`场景` blockquote)
- Every card now opens with a single-line Chinese `> 🎯 **场景**：...`
  blockquote summarizing the use case. Aimed at non-English readers
  who need to identify "is this card for me?" in one glance.
  Retrofitted to all 47 cards, added to the template, documented in
  SCHEMA / CLAUDE / CONTRIBUTING.

#### Repository organization
- Root directory tidied: `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`
  moved to `.github/` (GitHub auto-detects from there);
  `CHANGELOG.md` and `ROADMAP.md` moved to `docs/`. Root went from
  11 markdown files to 5.

### Changed

- `SKILL.md` routing tree expanded from 28 to 38 entries.
- `templates/prompt-card.md` updated with `## Quick Use` template.
- `CLAUDE.md` and `.github/CONTRIBUTING.md` updated to describe the
  Quick Use quality bar.
- `scripts/build_index.py` "Use when" extraction now reads the
  `**Use when:**` line from `## Quick Use` (cleaner than parsing
  Purpose).

## [0.1.0] — 2026-05-10

First public release. The initial schema, tooling, and a curated set
of 32 Prompt Cards covering all seven directions.

### Added

#### Repository structure and tooling
- Hybrid form: GitHub repository **and** Claude Code skill (one
  `SKILL.md` at the repo root makes the same content installable to
  `~/.claude/skills/prompt-atlas`).
- Dual-license policy: `LICENSE` documents MIT for code (`scripts/`,
  CI) and CC-BY-4.0 for prompt content (`prompts/`, `templates/`,
  `docs/`).
- Schema definition in `docs/SCHEMA.md`: required frontmatter fields,
  required body sections, controlled vocabulary, and the
  placeholder-↔-variables consistency rule.
- Canonical controlled vocabulary in `scripts/vocab.yml`. `validate.py`
  reads it directly so vocabulary changes only require touching one
  source plus its prose mirror in `docs/SCHEMA.md`.
- `scripts/validate.py`: enforces frontmatter shape, ID/path/direction
  consistency, controlled-vocabulary membership, body section
  ordering, and `{{placeholder}}` ↔ variable declaration consistency.
- `scripts/build_index.py`: regenerates `INDEX.md` (catalog by
  direction + tag matrix) from card frontmatter.
- CI workflow at `.github/workflows/validate.yml`: runs validation on
  every push and PR; fails the build if `INDEX.md` is stale.
- Standard OSS hygiene files: `README.md` (English/Chinese bilingual),
  `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.gitignore`,
  `.editorconfig`, `.github/PULL_REQUEST_TEMPLATE.md`, structured
  issue templates for new prompt cards and bug reports.
- Safety policy in `docs/SAFETY.md`: explicit prohibition on
  jailbreaks, hidden-CoT extraction, harm-enabling content, and
  proprietary leaks; explicit endorsement of defensive and evaluation
  prompts.

#### Prompt Cards (32)

**RAG (6):**
- `retrieval-relevance-evaluator` — score passage relevance to a query.
- `multihop-eval-synthesizer` — synthesize multi-hop QA eval questions.
- `query-rewriting-decomposition` — split a query into focused sub-queries.
- `hyde-hypothetical-answer-generator` — HyDE technique for retrieval.
- `citation-faithfulness-scorer` — audit per-claim citations.
- `answer-grounding-checker` — per-answer hallucination detection.

**Agent (5):**
- `react-planner-with-tool-schema` — ReAct loop with strict JSON tool calls.
- `plan-and-execute-planner` — upfront linear plan for predictable goals.
- `tool-call-repair` — schema-driven repair of malformed tool calls.
- `self-critique-reflection` — meta-level continue/switch/escalate.
- `long-context-memory-summarizer` — compress trajectories into structured memory.

**RLHF (4):**
- `pairwise-preference-labeler` — HHH dimensions, pairwise.
- `pointwise-reward-scorer` — single-response scalar reward.
- `constitutional-critique-revise` — Constitutional AI critique-then-revise.
- `best-of-n-selector` — rank N candidates, supports both inference and data construction.

**SFT (4):**
- `instruction-variant-expander` — rewrite ONE seed into N variants.
- `self-instruct-from-seed` — generate NEW instructions in the same task family.
- `data-quality-filter` — keep / review / drop SFT pairs by quality.
- `response-generator` — produce the response half of an SFT pair.

**Multimodal (4):**
- `vlm-image-description-verifier` — audit caption against image (per-claim).
- `structured-caption-generator` — captions as discrete schema fields.
- `vqa-with-confidence` — visual QA with grounding region and confidence.
- `ocr-structured-extraction` — schema-driven OCR + extraction for documents.

**CoT (4):**
- `structured-reasoning-with-rationale-summary` — single-path reasoning with rationale_summary.
- `least-to-most-decomposition` — decompose into strictly easier sub-problems.
- `self-consistency-aggregator` — majority vote across N pre-sampled paths.
- `verify-then-finalize` — draft + verify + finalize in one prompt.

**Eval (5):**
- `llm-judge-rubric-open-ended` — fixed 4-dimension rubric for open-ended outputs.
- `reference-based-judge` — score against a gold reference.
- `per-claim-factuality-judge` — atomic claim decomposition + factuality labels.
- `pointwise-quality-scorer` — custom dimensions + self-reported confidence.
- `safety-output-classifier` — defensive harm-taxonomy classifier.

### Design decisions documented

- Cards are **work assets**, not snippets. Every card includes
  `## Failure Modes` (how it breaks, how to detect) and
  `## Tuning Notes` (model differences, temperature, sibling cards).
- Tuning Notes explicitly compare each card to its siblings so readers
  know when to switch (e.g. open-ended vs reference-based judges,
  pairwise vs pointwise reward, ReAct vs plan-and-execute).
- "Hidden chain-of-thought extraction" is a banned use case; cards use
  `reasoning_summary` / `rationale_summary` / `decision_basis` field
  names by convention. Normal step-by-step reasoning in visible
  output is fine.
- `INDEX.md` is auto-generated, never hand-edited. CI rejects PRs that
  ship a stale `INDEX.md`.

### Removed

The following tags were proposed in early drafts but never used by any
card and were removed from the controlled vocabulary in this release:
`audio`, `persona`, `style-control`, `video`. They can be re-added in
the future via the standard vocabulary change process when an actual
card needs them.
