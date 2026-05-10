# Contributing to prompt-atlas

Thanks for contributing. This document covers how to add a Prompt Card,
how validation works, and what we will not accept.

## Quickstart

```bash
git clone https://github.com/huck012428-lab/prompt-atlas
cd prompt-atlas
pip install -r scripts/requirements.txt

# Create your card from the template:
cp templates/prompt-card.md prompts/<direction>/<your-slug>.md
$EDITOR prompts/<direction>/<your-slug>.md

# Validate:
python scripts/validate.py

# Refresh the auto-generated index:
python scripts/build_index.py
```

Open a PR using the **New Prompt Card** issue template (or skip the issue
and open a PR directly). CI runs the same validation; PRs that fail
validation will not be merged.

## Card requirements

Every file under `prompts/<direction>/<slug>.md` must conform to the schema
in [`docs/SCHEMA.md`](docs/SCHEMA.md). Specifically:

1. **Frontmatter** — all required fields present, all enum values from the
   controlled vocabulary, `id` matches file path, `direction` matches
   parent folder.
2. **Body sections** — six level-2 headings in this exact order:
   `## Purpose`, `## Prompt`, `## Example`, `## Failure Modes`,
   `## Tuning Notes`, `## Changelog`.
3. **Variables** — every `{{placeholder}}` in the prompt body matches a
   `name` in the `variables` frontmatter list.
4. **Concrete examples** — `## Example` must show real input and real
   expected output, not `<...>` placeholders.

## Quality bar

Cards that pass validation but read as unfinished will be asked for
revisions. The bar:

- **Purpose** names the workflow stage, not just "this prompt does X".
  Bad: "scores stuff". Good: "Used during RAG eval-set construction to
  produce per-passage relevance labels for offline retriever metrics."
- **Prompt** uses an explicit role + task + format structure, with
  `{{variable}}` placeholders.
- **Failure Modes** has at least two entries, each describing what goes
  wrong AND how to detect it. Don't list theoretical failures; list ones
  you have actually seen.
- **Tuning Notes** has practical guidance (model differences, temperature,
  few-shot suggestions, adjacent use cases). Chinese is fine here; the
  prompt body must be English in v0.1.

## Vocabulary changes

If your card needs a tag / audience / model label that does not exist:

1. Add it to [`scripts/vocab.yml`](scripts/vocab.yml) (canonical source —
   `validate.py` reads this directly).
2. Add the same value to the prose listing in
   [`docs/SCHEMA.md`](docs/SCHEMA.md) so humans browsing the docs see it.
3. In your PR description, justify the addition: which existing label did
   you consider and why didn't it fit?

Vocabulary changes are scrutinized — drift is the failure mode of
controlled-vocabulary systems. CI catches drift between `vocab.yml` and
actual cards (validation fails on unknown values); drift between
`vocab.yml` and `docs/SCHEMA.md` is a docs bug that reviewers should
catch.

## What we will NOT accept

See [`docs/SAFETY.md`](docs/SAFETY.md) for the full list. Highlights:

- Jailbreaks, safety-bypass prompts, refusal-suppression templates —
  including under "research" framing.
- Prompts whose primary purpose is harm-enabling (phishing, malware,
  surveillance abuse, fraud, harassment).
- Attempts to extract proprietary internal chain-of-thought from
  closed-source models. Use `reasoning_summary`, `rationale_summary`,
  or `decision_basis` instead. (Normal "think step by step" reasoning
  in visible output is fine.)
- Proprietary, leaked, or paid-course prompts — only contribute prompts
  you authored or that are already published under a compatible open
  license.
- Real personal data, API keys, credentials, or customer transcripts in
  examples. Use synthetic examples.

If you are unsure whether your card crosses a line, open a draft PR and
ask. Most ambiguity is around defensive / evaluation prompts (red-team
rubrics, harmfulness judges) — those are explicitly welcome.

## Reporting safety issues post-merge

If you find a card that violates [`docs/SAFETY.md`](docs/SAFETY.md) after
it has been merged, open a GitHub issue using the **Bug Report** template
and add the `safety` label. Maintainers will triage in the next merge
cycle.

## Code of conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Commit & PR conventions

- One card per PR is preferred. Vocabulary changes are their own PR.
- Commit message: `<area>: <imperative>` — for example:
  - `prompts/rag: add citation faithfulness scorer`
  - `scripts: validate variable name format`
  - `docs: clarify CoT safety boundary`
- Do not hand-edit `INDEX.md`. Let `scripts/build_index.py` do it.
- If your PR changes the vocabulary, run validation and the index
  builder in your final commit so reviewers see the synchronized state.

## License acknowledgement

By contributing, you agree your contribution is licensed under the
applicable part of [`LICENSE`](LICENSE):

- Code (`scripts/`, CI): MIT
- Prompt content (`prompts/`, `templates/`, `docs/`): CC-BY-4.0
