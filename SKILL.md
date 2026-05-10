---
name: prompt-atlas
description: A curated, versioned, searchable library of production-grade prompts for LLM trainers, AI product managers, and evaluation teams. 83 cards across 8 directions — RAG, Agent, RLHF, SFT, Multimodal, Chain-of-Thought, Evaluation, Code. Triggers when the user asks for a prompt for retrieval scoring, multi-hop QA, query rewriting, HyDE, citation auditing, hallucination detection, chunk summarization, context compression, agent planning / tool-call schema, agent reflection, tool-call repair, plan-and-execute, trajectory memory compression, multi-agent sub-task delegation, pairwise preference labeling, pointwise reward scoring, constitutional critique-and-revise, best-of-N selection, red-team prompt generation, instruction augmentation, self-instruct, SFT data filtering, SFT response generation, multi-turn conversation generation, few-shot example selection, structured image captioning, visual question answering, VLM caption verification, OCR structured extraction, chart and table extraction, structured reasoning, least-to-most decomposition, self-consistency aggregation, verify-then-finalize, tree-of-thoughts, LLM-as-judge rubrics, reference-based judging, per-claim factuality, pointwise quality scoring, safety output classification, position-bias-aware pairwise judging, multi-turn dialogue judging, code review, test case generation, code explanation, code evaluation, or refactor suggestion. Use to locate and adapt a Prompt Card rather than writing prompts from scratch.
---

# prompt-atlas

A curated library of 38 reusable Prompt Cards organized by technical
direction. Each card carries metadata, variables, examples, failure
modes, and tuning notes — they are work assets, not snippets, and each
explicitly states when to use a sibling card instead.

## When to invoke this skill

Trigger when the user describes a **prompt-engineering task** in any of
the covered directions, or asks for "a prompt for X" where X falls
under:

- **RAG**: retrieval scoring, multi-hop eval synthesis, query
  rewriting, HyDE-style hypothetical answers, citation faithfulness,
  answer hallucination detection, chunk summarization for retrieval.
- **Agent**: ReAct planning, plan-and-execute, tool-call repair,
  trajectory reflection, long-context memory compression, multi-agent
  sub-task delegation.
- **RLHF**: pairwise preference labeling, pointwise reward scoring,
  constitutional critique-and-revise, best-of-N selection, defensive
  red-team prompt generation.
- **SFT**: instruction-set augmentation, self-instruct generation,
  (instruction, response) quality filtering, SFT response generation.
- **Multimodal**: structured image captioning, VLM caption
  verification, visual question answering with grounding, OCR
  structured extraction, chart and table extraction.
- **Chain-of-Thought**: structured reasoning with rationale summary,
  least-to-most decomposition, self-consistency aggregation, verify-
  then-finalize, tree-of-thoughts.
- **Evaluation**: LLM-as-judge rubrics, reference-based judging,
  per-claim factuality, pointwise quality scoring, safety output
  classification, position-bias-aware pairwise judging.
- **Code**: structured code review, test case generation, audience-
  calibrated code explanation, code evaluation judging, refactor
  suggestions.

Do **not** invoke for: jailbreaks, safety-bypass prompts, or attempts
to extract proprietary internal reasoning traces. See
`docs/SAFETY.md`.

## Routing decision tree

Map the user's described task to the closest direction, then to the
closest card. When in doubt between two cards, read both and pick the
one whose **Purpose** section best matches; the **Tuning Notes** of
each card also explicitly compare it to its siblings.

### RAG

```
User describes...                                                                  → Card
─────────────────────────────────────────────────────────────────────────────────────────
"score whether a retrieved passage is relevant to a query"                         → rag/retrieval-relevance-evaluator
"build a multi-hop QA eval question from two passages"                             → rag/multihop-eval-synthesizer
"decompose / rewrite a user query into focused sub-queries before retrieval"       → rag/query-rewriting-decomposition
"generate a hypothetical answer to embed as a search query (HyDE)"                 → rag/hyde-hypothetical-answer-generator
"audit whether a cited span actually supports the claim it was attached to"        → rag/citation-faithfulness-scorer
"detect hallucinations in a RAG answer (per-claim grounding against context)"      → rag/answer-grounding-checker
"summarize a long document chunk for retrieval indexing"                           → rag/chunk-summarizer-for-retrieval
"compress retrieved passages into a smaller question-tailored context"             → rag/context-compression
"resolve a chat follow-up ('what about that?') into a standalone retrieval query"  → rag/conversational-query-resolver
"synthesize an answer from multiple sources, surfacing conflicts and citations"    → rag/multi-source-aggregator
"build a structured output (table / list / record) from RAG sources with citations" → rag/structured-rag-output-builder
```

### Agent

```
User describes...                                                                  → Card
─────────────────────────────────────────────────────────────────────────────────────────
"agent loop, ReAct-style, every step emits a JSON tool call"                       → agent/react-planner-with-tool-schema
"produce a complete plan upfront for a goal whose structure is predictable"        → agent/plan-and-execute-planner
"fix a malformed tool call given the validation error message"                     → agent/tool-call-repair
"step back and reflect on whether the trajectory is on track"                      → agent/self-critique-reflection
"compress a long agent trajectory into structured memory before context overflow"  → agent/long-context-memory-summarizer
"split a complex task across specialized workers / agents (multi-agent)"           → agent/sub-task-delegator
"decide whether a goal is too ambiguous to act on; ask one good clarifying question" → agent/clarification-asker
"convert an OpenAPI / Swagger / JSON Schema spec into an agent tool catalog"       → agent/api-spec-to-tool-catalog
"decide retry / abort / escalate when an agent operation fails"                    → agent/error-recovery-strategy
"plan agent execution within a token / dollar budget"                              → agent/budget-aware-planner
"compress a tool's verbose output before adding to agent context"                  → agent/tool-output-summarizer
```

### RLHF

```
User describes...                                                                  → Card
─────────────────────────────────────────────────────────────────────────────────────────
"label A vs B preference (HHH dimensions) for reward model data"                   → rlhf/pairwise-preference-labeler
"produce a single-response scalar reward signal (no pair available)"               → rlhf/pointwise-reward-scorer
"critique a response against a constitution and produce a revised version (CAI)"   → rlhf/constitutional-critique-revise
"pick the best of N candidate responses (rank + select)"                           → rlhf/best-of-n-selector
"generate adversarial probe prompts for safety evaluation (defensive only)"        → rlhf/red-team-prompt-generator
"diagnose model refusal calibration (over-refusal vs under-refusal vs correct)"    → rlhf/refusal-calibration-probe
"generate iterative DPO (chosen, rejected) pairs targeting one principle"          → rlhf/iterative-dpo-pair-generator
"score whether a response matches a defined persona / brand voice"                 → rlhf/persona-consistency-judge
"score helpfulness vs harmlessness independently to detect over-cautious failures" → rlhf/helpfulness-vs-harmlessness-tradeoff
"label pairwise preference for long-form (long input + long output) responses"     → rlhf/long-context-preference-labeler
```

### SFT

```
User describes...                                                                  → Card
─────────────────────────────────────────────────────────────────────────────────────────
"rewrite ONE instruction into N diverse variants (same task)"                      → sft/instruction-variant-expander
"generate NEW instructions in the same task family as seed examples"               → sft/self-instruct-from-seed
"filter (instruction, response) SFT pairs by quality before training"              → sft/data-quality-filter
"generate the response half of an SFT pair given an instruction"                   → sft/response-generator
"generate multi-turn conversation SFT data (chat training)"                        → sft/conversation-sft-pair-generator
"select best K few-shot demonstrations from a candidate pool for a query"          → sft/few-shot-example-selector
"generate a response in a defined persona / brand voice (with strictness)"         → sft/persona-controlled-response
"rewrite text in a target style (formal / casual / specific voice)"                → sft/style-transfer
"analyze SFT dataset coverage by topic / skill, find gaps and over-representation" → sft/data-coverage-analyzer
"classify an instruction's difficulty for a target model class"                    → sft/instruction-difficulty-classifier
```

### Multimodal

```
User describes...                                                                  → Card
─────────────────────────────────────────────────────────────────────────────────────────
"verify whether a candidate caption matches the image (per-claim audit)"           → multimodal/vlm-image-description-verifier
"generate a structured caption (scene, objects, action, salient text)"             → multimodal/structured-caption-generator
"answer a question about an image with grounding region + confidence"              → multimodal/vqa-with-confidence
"extract typed fields from a document image (receipt / invoice / form / ID)"       → multimodal/ocr-structured-extraction
"extract data from a chart / plot / table image"                                   → multimodal/chart-table-extractor
"analyze a document page's layout (title, body, tables, figures, reading order)"   → multimodal/document-layout-analyzer
"extract graph structure from a diagram / flowchart / architecture image"          → multimodal/diagram-to-structured-data
"convert a UI screenshot into a component spec (component tree + layout)"          → multimodal/screenshot-to-spec
"classify an image into custom user-defined categories with confidence"            → multimodal/image-classification
"transcribe handwritten text with per-word confidence"                             → multimodal/handwriting-transcriber
```

### Chain-of-Thought

```
User describes...                                                                  → Card
─────────────────────────────────────────────────────────────────────────────────────────
"single-pass structured reasoning with sub-steps and a visible rationale"          → cot/structured-reasoning-with-rationale-summary
"decompose a complex compositional problem into easier sub-problems in order"      → cot/least-to-most-decomposition
"aggregate N independently-sampled reasoning paths into a consensus answer"        → cot/self-consistency-aggregator
"draft + verify before committing to a final answer (per-check verdicts)"          → cot/verify-then-finalize
"explore multiple approaches in parallel, evaluate, prune (tree-of-thoughts)"      → cot/tree-of-thoughts
"abstract the question into a principle first, then apply (step-back prompting)"   → cot/step-back-prompting
"critique and revise a candidate reasoning plan before execution"                  → cot/plan-critique-and-revise
"reason with explicit per-step uncertainty and a final confidence range"           → cot/uncertainty-quantification
"reasoning where every claim must cite a provided source"                          → cot/citation-grounded-reasoning
"contrast correct path against an articulated wrong path (anti-misconception)"     → cot/contrastive-self-consistency
```

### Evaluation

```
User describes...                                                                  → Card
─────────────────────────────────────────────────────────────────────────────────────────
"LLM-as-judge rubric for open-ended outputs, fixed 4-dimension rubric"             → eval/llm-judge-rubric-open-ended
"score a model output against a gold reference (closed-form benchmark)"            → eval/reference-based-judge
"decompose an output into atomic claims and label each true/false/unverifiable"    → eval/per-claim-factuality-judge
"score one output on custom dimensions with self-reported confidence"              → eval/pointwise-quality-scorer
"classify a single output along a harm taxonomy (allow / review / block)"          → eval/safety-output-classifier
"pairwise judge with explicit position-bias detection (two-call protocol)"         → eval/pairwise-judge-with-position-bias-probe
"judge a multi-turn dialogue (per-turn + conversation-level scoring)"              → eval/multi-turn-dialogue-judge
"generate a domain-specific rubric with concrete level anchors (1-5)"              → eval/rubric-generator
"compare baseline vs candidate outputs and detect quality regressions"             → eval/regression-detector
"diagnose LLM judge biases (length / position / format / verbosity)"               → eval/judge-bias-probe
"check confidence calibration (predicted confidence vs actual accuracy)"           → eval/calibration-checker
```

### Code

```
User describes...                                                                  → Card
─────────────────────────────────────────────────────────────────────────────────────────
"structured code review with per-dimension findings (correctness/security/etc.)"   → code/code-review-checklist
"generate test cases for a function with happy/edge/error coverage"                → code/test-case-generator
"explain code at a specific audience level (junior dev / PM / domain expert)"      → code/code-explanation-generator
"judge whether candidate code fulfills a task (with optional gold + tests)"        → code/code-eval-judge
"suggest concrete refactors with rationale and impact (single goal per call)"      → code/refactor-suggestion
"translate code from one language to another (literal / idiomatic / balanced)"     → code/code-translation
"focused code security review with CWE-style findings and threat model"            → code/security-review
"summarize a git diff into a structured PR description (changes + risks + tests)"  → code/code-summary-for-pr
"plan a major version migration grounded in actual code (phased + ordered)"        → code/migration-plan-generator
"analyze the impact of changing a function / API signature on a codebase"          → code/dependency-impact-analyzer
```

For tasks not covered above:

1. Check `INDEX.md` (auto-generated) for the full card list grouped by
   direction and tag.
2. If still no match, the closest direction's existing cards may be
   adaptable — read their **Tuning Notes** sections for adjacent use
   cases.
3. If no card fits, tell the user and suggest opening an issue using
   `.github/ISSUE_TEMPLATE/new-prompt-card.yml` to request the card.

## Tag dictionary (for fuzzier matches)

When the user's words don't directly map to a direction, search by tag
intent:

- "score / rate / judge / evaluate" → `scoring`, `llm-judge`, `rubric`
- "label / annotate / classify" → `preference-labeling`,
  `classification`, `pairwise`
- "synthesize / generate examples / new instructions" → `generation`,
  `synthesis`, `seed-expansion`, `data-augmentation`
- "multi-step / decompose / break down / plan" → `planning`,
  `decomposition`, `decomposition-cot`, `react`
- "verify / check / ground / fact-check" → `factuality`, `grounding`,
  `self-check`, `citation`
- "multi-hop / cross-passage / chain" → `multi-hop`
- "tool / function call / repair / schema" → `tool-use`,
  `structured-output`
- "image / picture / visual / VLM" → `vision`, `image-description`,
  `vlm-eval`
- "reflection / step back / look at trajectory" → `reflection`,
  `self-check`
- "memory / compress / summarize trajectory / resume later" → `memory`,
  `rationale-summary`
- "constitution / critique-revise / harmless rewrite" → `harmlessness`,
  `helpfulness`, `honesty`
- "filter / quality / drop bad data" → `scoring`, `classification`,
  `instruction-tuning`
- "safety / harm / block / red-team / harmlessness" → `safety`,
  `harmlessness`
- "rationale / reasoning / sub-steps / least-to-most / self-consistency"
  → `structured-reasoning`, `rationale-summary`, `decomposition-cot`,
  `self-check`
- "reward model / RM training / preference data" → `reward-modeling`,
  `preference-labeling`, `pairwise`

The full controlled tag vocabulary is in `docs/SCHEMA.md`.

## How to use a card

1. **Read the entire card.** Frontmatter + all six sections. Skipping
   `Failure Modes` and `Tuning Notes` is the most common cause of
   unsatisfying results — those sections are where the experience
   lives.
2. **Match the user's variables** to the card's `variables` block. If a
   required variable is missing, ask the user for it.
3. **Substitute** `{{variable}}` placeholders in the card's prompt
   body.
4. **Match the model class** to the card's `models` field. If the user
   is on a model class the card has not been validated for, mention
   this and adjust per `Tuning Notes`.
5. **Surface the output schema.** If the card's `output_schema` is
   `structured-json`, ensure the calling environment can parse JSON;
   if the user is in a freeform chat, propose using a JSON-mode call.
6. **Check the sibling cards.** Most cards' Tuning Notes name an
   adjacent card and explain when to switch (e.g.
   `eval/reference-based-judge` says use it for closed-form,
   `eval/llm-judge-rubric-open-ended` for open-ended). Verify the
   chosen card is the right sibling for the user's actual task.

## Safety

Every card is reviewed against `docs/SAFETY.md`. If a user request
would require violating that policy (jailbreaks, hidden-CoT extraction,
harm-enabling content), do not adapt a card to fit — refuse and explain.

The `eval/safety-output-classifier` card is itself defensive (it
detects harm to filter or label); do not invert it to generate harmful
content.

## Repository layout (reference)

```
prompt-atlas/
├── prompts/<direction>/<slug>.md     ← the cards (83 total)
├── templates/prompt-card.md          ← canonical template
├── docs/SCHEMA.md                    ← frontmatter + tag vocabulary
├── docs/SAFETY.md                    ← policy
├── INDEX.md                          ← auto-generated catalog
└── scripts/{validate,build_index}.py ← maintenance
```
