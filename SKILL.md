---
name: prompt-atlas
description: A curated, versioned, searchable library of production-grade prompts for LLM trainers, AI product managers, and evaluation teams. Triggers when the user asks for a prompt for RAG, Agent / tool use, RLHF preference labeling, SFT data augmentation, multimodal / VLM evaluation, structured chain-of-thought, or LLM-as-judge evaluation rubrics. Use to locate and adapt a Prompt Card rather than writing prompts from scratch.
---

# prompt-atlas

A curated library of reusable Prompt Cards organized by technical direction.
Each card carries metadata, variables, examples, failure modes, and tuning
notes — they are work assets, not snippets.

## When to invoke this skill

Trigger when the user describes a **prompt-engineering task** in any of the
covered directions, or asks for "a prompt for X" where X falls under:

- Retrieval-augmented generation (RAG): retrieval scoring, multi-hop eval
  synthesis, query rewriting, grounding checks.
- Agents: planning loops, tool-call schemas, ReAct trajectories.
- RLHF: pairwise preference labeling, reward-model data, HHH evaluation.
- SFT: instruction-set augmentation, seed expansion, persona / style control.
- Multimodal: VLM caption verification, image-grounding factuality.
- Structured chain-of-thought: visible reasoning summaries, sub-step
  decomposition (without exposing hidden traces).
- Evaluation: LLM-as-judge rubrics, holistic / per-criterion scoring.

Do **not** invoke for: jailbreaks, safety-bypass prompts, or attempts to
extract proprietary internal reasoning traces. See `docs/SAFETY.md`.

## Routing decision tree

Map the user's described task to the closest direction, then to the closest
card. When in doubt between two cards, read both and pick the one whose
**Purpose** section best matches.

```
User describes...                                        → Direction → Card
─────────────────────────────────────────────────────────────────────────
"score whether a passage is relevant to a query"         → rag       → rag/retrieval-relevance-evaluator
"build a multi-hop QA eval set from passages"            → rag       → rag/multihop-eval-synthesizer
"agent loop with tool calls / strict JSON schema"        → agent     → agent/react-planner-with-tool-schema
"label A vs B preference (HHH)"                          → rlhf      → rlhf/pairwise-preference-labeler
"expand SFT seeds into diverse rewrites"                 → sft       → sft/instruction-variant-expander
"verify a VLM caption against the actual image"          → multimodal → multimodal/vlm-image-description-verifier
"structured reasoning with a rationale summary"          → cot       → cot/structured-reasoning-with-rationale-summary
"LLM-as-judge rubric for open-ended outputs"             → eval      → eval/llm-judge-rubric-open-ended
```

For tasks not covered above:

1. Check `INDEX.md` (auto-generated) for the full card list grouped by
   direction and tag.
2. If still no match, the closest direction's existing card may be adaptable
   — read its **Tuning Notes** section for adjacent use cases.
3. If no card fits, tell the user and suggest opening an issue using
   `.github/ISSUE_TEMPLATE/new-prompt-card.yml` to request the card.

## Tag dictionary (for fuzzier matches)

When the user's words don't directly map to a direction, search by tag
intent:

- "score / rate / judge / evaluate" → `scoring`, `llm-judge`, `rubric`
- "label / annotate" → `preference-labeling`, `classification`
- "synthesize / generate examples" → `generation`, `synthesis`,
  `seed-expansion`, `data-augmentation`
- "multi-step / decompose / plan" → `planning`, `decomposition`,
  `decomposition-cot`, `react`
- "verify / check / ground" → `factuality`, `grounding`, `self-check`
- "multi-hop / cross-passage" → `multi-hop`
- "tool / function call" → `tool-use`, `structured-output`
- "image / picture / visual" → `vision`, `image-description`, `vlm-eval`

The full controlled tag vocabulary is in `docs/SCHEMA.md`.

## How to use a card

1. **Read the entire card.** Frontmatter + all six sections. Skipping
   `Failure Modes` and `Tuning Notes` is the most common cause of
   unsatisfying results — those sections are where the experience lives.
2. **Match the user's variables** to the card's `variables` block. If a
   required variable is missing, ask the user for it.
3. **Substitute** `{{variable}}` placeholders in the card's prompt body.
4. **Match the model class** to the card's `models` field. If the user is
   on a model class the card has not been validated for, mention this and
   adjust per `Tuning Notes`.
5. **Surface the output schema.** If the card's `output_schema` is
   `structured-json`, ensure the calling environment can parse JSON; if
   the user is in a freeform chat, propose using a JSON-mode call.

## Safety

Every card is reviewed against `docs/SAFETY.md`. If a user request would
require violating that policy (jailbreaks, hidden-CoT extraction,
harm-enabling content), do not adapt a card to fit — refuse and explain.

## Repository layout (reference)

```
prompt-atlas/
├── prompts/<direction>/<slug>.md     ← the cards
├── templates/prompt-card.md          ← canonical template
├── docs/SCHEMA.md                    ← frontmatter + tag vocabulary
├── docs/SAFETY.md                    ← policy
├── INDEX.md                          ← auto-generated catalog
└── scripts/{validate,build_index}.py ← maintenance
```
