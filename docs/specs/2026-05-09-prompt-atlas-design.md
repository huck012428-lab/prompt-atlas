# prompt-atlas — v0.1 Design Spec

**Date:** 2026-05-09
**Status:** Approved (hybrid form, active routing skill)

## 1. Goal

A curated, versioned, searchable prompt library for LLM trainers, AI product
managers, prompt engineers, RLHF/SFT data teams, evaluation teams, and AI
application builders.

The library treats every prompt as a **reusable work asset** (a *Prompt Card*),
not a snippet. Each card carries metadata, variables, examples, failure modes,
and tuning notes so it can be reused, tuned, and evaluated.

## 2. Form

Hybrid: a public GitHub repository **and** a Claude Code skill installable to
`~/.claude/skills/`. The repo root contains both `README.md` (GitHub entry) and
`SKILL.md` (Claude Code entry).

## 3. Architecture (Approach B — Active Routing)

```
prompt-atlas/
├── README.md                  GitHub entry, English-first + Chinese summary
├── SKILL.md                   Claude Code skill entry, contains routing tree + tag dictionary
├── CLAUDE.md                  Working instructions for agents editing this repo
├── LICENSE                    Dual-license note (MIT for code, CC-BY-4.0 for prompt content)
├── CONTRIBUTING.md            Contribution guide + safety rules
├── CODE_OF_CONDUCT.md         Pointer to Contributor Covenant
├── INDEX.md                   AUTO-GENERATED catalog by direction/tag — do not edit manually
├── .editorconfig
├── .gitignore
├── docs/
│   ├── SCHEMA.md              Frontmatter schema + controlled tag vocabulary
│   ├── SAFETY.md              What is NOT allowed in this repo
│   └── specs/                 Design specs (this file lives here)
├── templates/
│   └── prompt-card.md         Canonical Prompt Card template
├── prompts/
│   ├── rag/
│   ├── agent/
│   ├── rlhf/
│   ├── sft/
│   ├── multimodal/
│   ├── cot/
│   └── eval/
├── scripts/
│   ├── validate.py            Frontmatter + tag vocabulary + ID uniqueness check
│   ├── build_index.py         Generates INDEX.md from all cards
│   └── requirements.txt       PyYAML
└── .github/
    ├── ISSUE_TEMPLATE/
    │   ├── new-prompt-card.yml
    │   └── bug-report.yml
    ├── PULL_REQUEST_TEMPLATE.md
    └── workflows/
        └── validate.yml       CI: pip install + python scripts/validate.py
```

## 4. Prompt Card Schema (frontmatter)

```yaml
id: <direction>/<slug>          # e.g. rag/retrieval-relevance-evaluator
title: <human-readable title>
version: 0.1.0                  # semver per card
status: stable | experimental | deprecated
direction: rag | agent | rlhf | sft | multimodal | cot | eval
tags: [<from controlled vocab>]
audience: [<from controlled vocab>]
models: [<from controlled vocab>]
language: en
input_schema: text | structured | multimodal
output_schema: text | structured-json | numeric-score | label
license: CC-BY-4.0
variables:
  - name: <var-name>
    description: <what this slot is for>
    required: true | false
```

Card body sections (markdown, after frontmatter):

1. **Purpose** — one paragraph, when and why to use
2. **Prompt** — the prompt text in a fenced block, with `{{variable}}` placeholders
3. **Example** — concrete input → expected output
4. **Failure Modes** — bullet list of how this prompt typically goes wrong
5. **Tuning Notes** — knobs to turn for different models/contexts (Chinese OK)
6. **Changelog** — per-version entries

## 5. Controlled tag vocabulary (v0.1)

See `docs/SCHEMA.md` for the canonical list. Validation rejects unknown tags
to prevent vocabulary drift.

## 6. Discovery UX

Two paths:

- **GitHub browsers**: `INDEX.md` is auto-generated and committed; `README.md`
  embeds the same catalog table near the top.
- **Claude Code users**: `SKILL.md` contains a routing decision tree mapping
  user intents (e.g. "evaluate retrieval", "build judge rubric") to specific
  card paths. Tag vocabulary is mirrored inside the skill so the model can
  reason about which card fits.

## 7. v0.1 seed cards (8)

| Direction  | Card                                                |
|------------|-----------------------------------------------------|
| rag        | retrieval-relevance-evaluator                       |
| rag        | multihop-eval-synthesizer                           |
| agent      | react-planner-with-tool-schema                      |
| rlhf       | pairwise-preference-labeler                         |
| sft        | instruction-variant-expander                        |
| multimodal | vlm-image-description-verifier                      |
| cot        | structured-reasoning-with-rationale-summary         |
| eval       | llm-judge-rubric-open-ended                         |

## 8. Safety stance

- No jailbreaks, safety-bypass prompts, or roleplay-as-bypass.
- No prompts for phishing, malware, credential theft, surveillance abuse.
- No private, proprietary, leaked, or paid-course prompts.
- No personal data, API keys, credentials.
- No prompts that try to extract privileged reasoning traces from closed-source
  models. Use `reasoning_summary` / `rationale_summary` instead of asking for
  hidden chain-of-thought.

Normal "think step by step" reasoning IS allowed; the rule targets explicit
attempts to extract proprietary internal traces.

## 9. License

- Code (`scripts/`, CI, validation): MIT
- Prompt content (`prompts/`, `templates/`, `docs/`): CC-BY-4.0

Single `LICENSE` file documents the split; each prompt card frontmatter carries
`license: CC-BY-4.0` for clarity.

## 10. Validation guarantees

`scripts/validate.py` checks:

1. Every `prompts/**/*.md` file has YAML frontmatter
2. All required fields present and non-empty
3. `id` matches the file path
4. `id` is unique across the repo
5. `direction` matches the parent folder
6. All `tags`, `audience`, `models`, `status` values are in the controlled vocabulary
7. Body contains the six required section headers

CI runs validation on every PR.
