<!--
Thanks for the PR. Please fill in the sections below. Delete sections that
do not apply.
-->

## What does this PR do?

<!-- One or two sentences. -->

## Type of change

- [ ] New Prompt Card
- [ ] Update to an existing Prompt Card (bump `version` in frontmatter and add a Changelog entry)
- [ ] Vocabulary change (tag / audience / model / direction)
- [ ] Validation / index script change
- [ ] Documentation
- [ ] Other

## For Prompt Card changes

- [ ] `python scripts/validate.py` returns OK locally
- [ ] `python scripts/build_index.py` ran and `INDEX.md` is included in this PR
- [ ] Frontmatter `id` matches the file path
- [ ] All six body sections are present in order
- [ ] Example uses synthetic input/output (no real PII / credentials / proprietary content)
- [ ] I have read [`docs/SAFETY.md`](../docs/SAFETY.md) and this card does not violate it

## For vocabulary changes

- [ ] Updated `docs/SCHEMA.md`
- [ ] Updated matching constant in `scripts/validate.py`
- [ ] Justification below: which existing label did I consider, and why didn't it fit?

## Notes for reviewers

<!-- Anything specific you want reviewers to focus on. -->
