# CLAUDE.md — instructions for agents working on this repo

You are working on **prompt-atlas**, a curated Prompt Card library for LLM
trainers, AI product managers, and evaluation teams. This file tells you
how to work in this repo. The user-facing entry points are `README.md`
(GitHub) and `SKILL.md` (Claude Code).

## Project shape

- Hybrid: GitHub repository + installable Claude Code skill.
- Every prompt is a **Prompt Card**: one markdown file under
  `prompts/<direction>/<slug>.md` with YAML frontmatter and six required
  body sections.
- `docs/SCHEMA.md` is the canonical schema and controlled vocabulary.
  `scripts/validate.py` enforces it. CI rejects PRs that fail validation.

## When you change anything under `prompts/`

You MUST run, in order, before claiming work is done:

```bash
python scripts/validate.py     # exits 0 only if every card is valid
python scripts/build_index.py  # regenerates INDEX.md from frontmatter
```

`INDEX.md` is auto-generated. **Never edit it by hand.** If your diff includes
manual `INDEX.md` edits, that is a bug — discard them and re-run the build.

## When you add a new tag, audience, or model label

The vocabulary lives in two places that must stay in sync:

1. `docs/SCHEMA.md` — the prose listing for humans
2. `scripts/validate.py` — the constants used by validation

Drift between them means CI either fails on valid cards or accepts invalid
ones. When you touch one, touch the other in the same commit, and justify
the addition in the PR description (which existing label did not fit?).

## When you add a new direction

A new direction (currently: `rag`, `agent`, `rlhf`, `sft`, `multimodal`,
`cot`, `eval`) is a structural change. You must update:

1. The directory `prompts/<new-direction>/` (create with at least one card).
2. The `DIRECTIONS` set in `scripts/validate.py`.
3. The `DIRECTION_ORDER` and `DIRECTION_LABEL` map in
   `scripts/build_index.py`.
4. The list in `docs/SCHEMA.md`.
5. The routing tree in `SKILL.md`.

Then re-run validate and build_index.

## When you write a new card

Start from `templates/prompt-card.md`. Required body sections, in order:

1. `## Purpose`
2. `## Prompt`
3. `## Example`
4. `## Failure Modes`
5. `## Tuning Notes`
6. `## Changelog`

Quality bar:

- Purpose names the workflow stage (not just "this prompt does X").
- Prompt body uses `{{variable}}` placeholders that match the
  `variables` frontmatter block.
- Example contains a concrete input and a concrete expected output —
  not "..." placeholders.
- Failure Modes is at least two bullets, each with a description of what
  goes wrong AND how to detect it.
- Tuning Notes covers model differences, temperature, and adjacent use
  cases. Chinese OK in this section; English-only required in the prompt
  body.

## Safety boundaries

`docs/SAFETY.md` lists what is NOT allowed. Notable items:

- No jailbreak / safety-bypass prompts, even framed as "research".
- No prompts whose primary purpose is harm-enabling.
- No attempts to extract privileged internal chain-of-thought from
  closed-source models. Use `reasoning_summary` / `rationale_summary` /
  `decision_basis` field names instead. (Normal "think step by step"
  reasoning IS fine.)
- No real personal data, API keys, customer data in examples.

If a user request requires violating these boundaries, refuse and explain.

## Git etiquette

- Commit message format: `<area>: <short imperative>` (e.g.
  `prompts/rag: add citation faithfulness scorer`).
- One card per PR is preferred. Vocabulary changes are their own PR.
- Do not commit auto-generated `INDEX.md` changes alongside unrelated
  edits — the diff should be obvious.

## What this repo is NOT

- Not a paste-bin of "awesome prompts".
- Not a place for jailbreaks, even pedagogical ones.
- Not a leak archive for closed-product system prompts.
- Not a snippet directory — every entry must be a full Prompt Card.
