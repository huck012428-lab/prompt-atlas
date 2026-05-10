# Roadmap

A living document. Items here are *intentions*, not commitments — open
issues and PRs are the authoritative state of work in flight.

## v0.1 (released 2026-05-10)

Shipped. See [`CHANGELOG.md`](CHANGELOG.md). 32 cards across 7
directions, schema + validator + CI, bilingual README, safety policy,
dual license.

## v0.2 — broaden coverage and tighten boundaries

Goal: get every direction past the "minimum representative" line and
into "covers the common production tasks". Roughly +10–15 cards
across the seven directions.

Likely additions per direction:

- **RAG**: chunk summarization for retrieval, relevance feedback /
  iterative retrieval, context compression.
- **Agent**: multi-agent supervisor, sub-task delegation, tool catalog
  generator from API specs.
- **RLHF**: red-team prompt generator (defensive), iterative DPO data
  generator, refusal calibration probe.
- **SFT**: persona controller, style-controlled response variants,
  conversation-format SFT pair generator.
- **Multimodal**: chart / table extraction, image + text joint
  classifier, video frame description aggregator (audio direction
  reserved for a later release).
- **CoT**: tree-of-thoughts variant, plan critique + rewrite,
  step-by-step rationale with citations.
- **Eval**: pairwise judge with position-bias probe, calibration test
  harness, multi-turn dialogue judge.

Vocabulary additions in v0.2 will follow the standard process: each
new tag/audience/model entry must be justified in the PR that
introduces the first card using it.

## v0.3 — discovery and integration

Goal: make the library easier to find the right card in.

- README catalog table generated from `INDEX.md` so the front page
  doubles as the category index.
- `scripts/build_index.py` extension: secondary index slices by
  audience and by model class.
- Skill-side improvements: tag-search hints in `SKILL.md` so Claude
  Code can route on intent phrases that don't directly map to a
  direction.
- A short "tour" doc that walks through 3–4 representative end-to-end
  workflows (a RAG eval pipeline, an SFT data construction pipeline,
  an agent loop) using the cards in sequence.

## Beyond v0.3 — open questions

These are not commitments; they are open design questions where the
right answer depends on contributor traffic and use signals.

- **Versioned card retrieval**. As cards evolve (`version: 0.2.0`
  etc.), is there value in keeping previous revisions accessible
  rather than overwriting? Likely yes for cards that change
  semantically; not worth it for cosmetic edits.
- **Sibling-card cross-references as machine-readable links**. Today
  the "see also" pointers live in prose inside Tuning Notes. A
  structured `related_cards` frontmatter field would let tooling
  surface cluster diagrams, but adds maintenance cost.
- **Per-card eval harness**. Some cards have a known "if calibrated,
  agreement with gold should be >X%". Stamping cards with a
  reproducible eval would make quality auditable, but it's a real
  engineering project.
- **Localization beyond bilingual README**. Card prompt bodies are
  English-first by policy (most production prompts use English to
  maximize model performance). If demand emerges for native-language
  prompt variants, that would need a per-card `language: zh` variant
  alongside the English original — schema-supported but currently
  unused.
- **Plugin / package distribution**. Today, installation is `git
  clone`. A `pip install prompt-atlas` or similar is doable but only
  worth it if the cards are consumed programmatically, not just read.

## Non-goals

Intentionally out of scope for the foreseeable future:

- A SaaS layer or hosted UI. The repo + skill model is the product.
- Generation prompts whose primary purpose is harm enabling, jailbreak
  research, or proprietary-prompt redistribution. See `docs/SAFETY.md`.
- Becoming a generic "prompt store" by including every prompt anyone
  contributes. The PromptOps quality bar (Failure Modes, Tuning Notes,
  sibling-card relationships) is the entry criterion.

## How to influence the roadmap

- Open an issue with the `new-prompt-card` template proposing a card
  you'd use.
- Open an issue describing an integration / discovery / quality gap
  with concrete examples.
- A PR with the card or fix is the strongest form of influence.
