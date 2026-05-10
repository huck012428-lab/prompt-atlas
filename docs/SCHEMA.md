# Prompt Card Schema

Every file under `prompts/**/*.md` is a **Prompt Card**. Cards have YAML
frontmatter followed by a markdown body with a fixed set of sections.
`scripts/validate.py` enforces this schema; CI rejects PRs that fail validation.

## Frontmatter fields

| Field           | Type            | Required | Notes |
|-----------------|-----------------|----------|-------|
| `id`            | string          | yes      | `<direction>/<slug>`. Must match file path (`prompts/<direction>/<slug>.md`). Lowercase, kebab-case. |
| `title`         | string          | yes      | Human-readable name. |
| `version`       | string          | yes      | Semver, e.g. `0.1.0`. Bumped per card, not per repo. |
| `status`        | enum            | yes      | `stable` \| `experimental` \| `deprecated`. |
| `direction`     | enum            | yes      | One of: `rag`, `agent`, `rlhf`, `sft`, `multimodal`, `cot`, `eval`. Must match parent folder. |
| `tags`          | list of strings | yes      | At least one. All values must come from the controlled vocabulary below. |
| `audience`      | list of strings | yes      | At least one. From the controlled vocabulary. |
| `models`        | list of strings | yes      | At least one. From the controlled vocabulary. |
| `language`      | enum            | yes      | `en` (v0.1 only allows English prompt text). |
| `input_schema`  | enum            | yes      | `text` \| `structured` \| `multimodal`. |
| `output_schema` | enum            | yes      | `text` \| `structured-json` \| `numeric-score` \| `label`. |
| `license`       | enum            | yes      | `CC-BY-4.0` (only allowed value in v0.1). |
| `variables`     | list of objects | yes      | Each item: `name` (kebab-case), `description`, `required` (bool). May be empty list `[]` if the prompt has no variables. |

## Required body sections

The body must open with a one-line Chinese 场景 blockquote
(`> 🎯 **场景**：...`) so non-English readers can identify the card's
purpose at a glance. Then the body must contain these seven level-2
headings, in this order:

1. `## Quick Use`
2. `## Purpose`
3. `## Prompt`
4. `## Example`
5. `## Failure Modes`
6. `## Tuning Notes`
7. `## Changelog`

`> 🎯 **场景**：...` (Chinese) is the at-a-glance summary for non-English
readers — one or two sentences naming the workflow scenario this card is
for. Visible without scrolling.

`## Quick Use` is the beginner-facing English summary — a one-sentence
"use when", a plain-English description of what to fill into each
variable, and a plain-English description of what the card returns.
Aimed at users who only need the gist; the deeper sections below it are
where the engineering experience lives.

Variables in the prompt text use double-curly placeholders: `{{variable_name}}`.

**Placeholder ↔ variables consistency** (enforced by `validate.py`):

- Every `{{name}}` placeholder appearing in the body MUST be declared in the
  frontmatter `variables` list.
- Every variable declared in `variables` MUST be referenced at least once
  as `{{name}}` somewhere in the body. Declaring an unused variable is an
  error — either reference it or remove it.

Variable names are `snake_case` (lowercase letters, digits, underscores;
must start with a letter).

## Controlled vocabulary

The canonical source for all enum-valued fields is
[`scripts/vocab.yml`](../scripts/vocab.yml). `validate.py` reads it directly;
the prose listing below is a human-readable mirror. **Keep them in sync** when
adding values.

### Directions
`rag`, `agent`, `rlhf`, `sft`, `multimodal`, `cot`, `eval`, `code`

### Status
`stable`, `experimental`, `deprecated`

### Tags

General-purpose:
`scoring`, `classification`, `extraction`, `generation`, `eval-set`, `safety`,
`structured-output`, `data-augmentation`

RAG:
`retrieval`, `ranking`, `citation`, `query-rewriting`, `grounding`,
`multi-hop`, `synthesis`

Agent:
`planning`, `tool-use`, `react`, `reflection`, `memory`, `decomposition`

RLHF:
`preference-labeling`, `reward-modeling`, `pairwise`, `harmlessness`,
`helpfulness`, `honesty`

SFT:
`instruction-tuning`, `seed-expansion`

Multimodal:
`vision`, `image-description`, `ocr`, `vlm-eval`

CoT:
`structured-reasoning`, `rationale-summary`, `self-check`, `decomposition-cot`

Eval:
`llm-judge`, `rubric`, `comparative`, `holistic`, `factuality`, `coherence`

Code:
`code-review`, `test-generation`, `documentation`

### Audience
`llm-trainer`, `ai-pm`, `prompt-engineer`, `eval-team`, `rlhf-team`, `sft-team`,
`app-builder`

### Models
Tier labels, not specific model names (so cards age well):
`generic`, `frontier-closed`, `mid-tier-closed`, `open-source-large`,
`open-source-small`, `vision-language`, `reasoning-model`

### Input / output schemas
- `input_schema`: `text` | `structured` | `multimodal`
- `output_schema`: `text` | `structured-json` | `numeric-score` | `label`

### License
`CC-BY-4.0` (v0.1)

## Updating the vocabulary

Adding a new tag/audience/model label is a deliberate change. Open a PR that:

1. Adds the value to [`scripts/vocab.yml`](../scripts/vocab.yml).
2. Adds the same value to the prose listing in this file.
3. Justifies the addition in the PR description (which existing tag did not fit?).

`vocab.yml` is the source of truth. Drift between it and this file is a docs
bug; drift between either and an actual card is caught by CI (validation fails
on unknown values).
