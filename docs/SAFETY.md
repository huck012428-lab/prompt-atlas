# Safety Policy

prompt-atlas is a working tool for LLM trainers, AI product managers, and
evaluation teams. It is **not** a place to collect adversarial techniques,
proprietary leaks, or harm-enabling content.

## What is NOT allowed

Prompts that fall into any of the categories below will be rejected (or
removed if discovered after merge):

1. **Safety-bypass prompts** — jailbreaks, "DAN"-style roleplays, system-prompt
   leakers, refusal-suppression templates. This includes prompts framed as
   "for research" whose actual function is to elicit policy-violating output.

2. **Harm-enabling content** — prompts whose primary purpose is to produce
   phishing, malware, credential theft, surveillance abuse, fraud, harassment,
   targeting of individuals, or instructions for illegal activity.

3. **Hidden-reasoning extraction** — prompts that try to force closed-source
   models to reveal proprietary internal chain-of-thought traces.
   Use `reasoning_summary`, `rationale_summary`, or `decision_basis` fields
   instead. Asking a model to reason step by step in its visible output is
   fine; trying to exfiltrate hidden traces is not.

4. **Proprietary or leaked prompts** — system prompts copied from closed
   products, paid courses, or leaked sources. Only contribute prompts you
   authored or that are already published under a compatible open license.

5. **Sensitive data in examples** — real personal data, real API keys,
   credentials, internal company names, customer transcripts. Use synthetic
   examples.

## What IS encouraged

- Prompts for **evaluating** safety / harmlessness (e.g. preference labelers
  for harm dimensions). These exist to make models safer and are welcome.
- Prompts that document **failure modes** clearly — knowing how a prompt
  breaks is part of the asset.
- Defensive use cases: red-team rubrics, bias evaluation templates, factuality
  judges. Frame them as evaluation tools, not as exploit recipes.

## Reporting

Found a card that violates this policy after merge? Open an issue with the
template `bug-report` and label it `safety`. Maintainers will triage within
the next merge cycle.

## A note on dual-use

Some legitimate evaluation work looks adversarial on the surface (e.g. a
red-team rubric describing what a harmful response looks like). The test is
**purpose**: is the card built to make models safer / better evaluated, or to
make harm easier? Cards in the first bucket belong here; cards in the second
do not.
