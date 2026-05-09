#!/usr/bin/env python3
"""Validate prompt-atlas card files against the schema in docs/SCHEMA.md.

Run from repo root:

    python scripts/validate.py

Exits 0 if every card under prompts/ is valid, 1 otherwise. Prints one error
line per violation. CI runs this on every pull request.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"

DIRECTIONS = {"rag", "agent", "rlhf", "sft", "multimodal", "cot", "eval"}
STATUS = {"stable", "experimental", "deprecated"}
LANGUAGES = {"en"}
INPUT_SCHEMAS = {"text", "structured", "multimodal"}
OUTPUT_SCHEMAS = {"text", "structured-json", "numeric-score", "label"}
LICENSES = {"CC-BY-4.0"}

TAGS = {
    # general
    "scoring", "classification", "extraction", "generation", "eval-set",
    "safety", "structured-output", "data-augmentation",
    # rag
    "retrieval", "ranking", "citation", "query-rewriting", "grounding",
    "multi-hop", "synthesis",
    # agent
    "planning", "tool-use", "react", "reflection", "memory", "decomposition",
    # rlhf
    "preference-labeling", "reward-modeling", "pairwise", "harmlessness",
    "helpfulness", "honesty",
    # sft
    "instruction-tuning", "seed-expansion", "persona", "style-control",
    # multimodal
    "vision", "image-description", "ocr", "video", "vlm-eval", "audio",
    # cot
    "structured-reasoning", "rationale-summary", "self-check",
    "decomposition-cot",
    # eval
    "llm-judge", "rubric", "comparative", "holistic", "factuality",
    "coherence",
}

AUDIENCES = {
    "llm-trainer", "ai-pm", "prompt-engineer", "eval-team",
    "rlhf-team", "sft-team", "app-builder",
}

MODELS = {
    "generic", "frontier-closed", "mid-tier-closed",
    "open-source-large", "open-source-small",
    "vision-language", "reasoning-model",
}

REQUIRED_FRONTMATTER = [
    "id", "title", "version", "status", "direction",
    "tags", "audience", "models", "language",
    "input_schema", "output_schema", "license", "variables",
]

REQUIRED_SECTIONS = [
    "## Purpose",
    "## Prompt",
    "## Example",
    "## Failure Modes",
    "## Tuning Notes",
    "## Changelog",
]

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ID_RE = re.compile(r"^[a-z]+/[a-z0-9]+(?:-[a-z0-9]+)*$")
VAR_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PLACEHOLDER_RE = re.compile(r"\{\{([a-z_][a-z0-9_]*)\}\}")


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("file does not start with '---' frontmatter delimiter")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        raise ValueError("missing closing '---' frontmatter delimiter")
    return rest[:end], rest[end + 5:]


def validate_card(
    path: Path,
    errors: list[str],
    ids_seen: dict[str, str],
) -> None:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    try:
        fm_str, body = split_frontmatter(text)
    except ValueError as exc:
        errors.append(f"{rel}: {exc}")
        return

    try:
        fm = yaml.safe_load(fm_str)
    except yaml.YAMLError as exc:
        errors.append(f"{rel}: invalid YAML frontmatter: {exc}")
        return

    if not isinstance(fm, dict):
        errors.append(f"{rel}: frontmatter is not a YAML mapping")
        return

    missing = [k for k in REQUIRED_FRONTMATTER if k not in fm]
    if missing:
        errors.append(f"{rel}: missing required field(s): {', '.join(missing)}")
        return

    expected_dir = path.parent.name
    expected_slug = path.stem
    expected_id = f"{expected_dir}/{expected_slug}"

    fid = str(fm["id"])
    if fid != expected_id:
        errors.append(
            f"{rel}: id '{fid}' does not match file path; expected '{expected_id}'"
        )
    if not ID_RE.match(fid):
        errors.append(f"{rel}: id '{fid}' is not lowercase kebab-case '<dir>/<slug>'")

    if fid in ids_seen:
        errors.append(f"{rel}: duplicate id '{fid}' (also at {ids_seen[fid]})")
    else:
        ids_seen[fid] = rel

    if fm["direction"] != expected_dir:
        errors.append(
            f"{rel}: direction '{fm['direction']}' does not match folder '{expected_dir}'"
        )
    if fm["direction"] not in DIRECTIONS:
        errors.append(f"{rel}: direction '{fm['direction']}' not in vocabulary")

    if not isinstance(fm.get("title"), str) or not fm["title"].strip():
        errors.append(f"{rel}: title must be a non-empty string")

    version = fm.get("version")
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        errors.append(f"{rel}: version '{version}' is not semver (X.Y.Z)")

    for field, vocab in (
        ("status", STATUS),
        ("language", LANGUAGES),
        ("input_schema", INPUT_SCHEMAS),
        ("output_schema", OUTPUT_SCHEMAS),
        ("license", LICENSES),
    ):
        if fm[field] not in vocab:
            errors.append(
                f"{rel}: {field} '{fm[field]}' not in {sorted(vocab)}"
            )

    for field, vocab in (("tags", TAGS), ("audience", AUDIENCES), ("models", MODELS)):
        value = fm.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{rel}: {field} must be a non-empty list")
            continue
        for item in value:
            if not isinstance(item, str) or item not in vocab:
                errors.append(
                    f"{rel}: {field} value '{item}' not in controlled vocabulary"
                )

    variables = fm.get("variables")
    if not isinstance(variables, list):
        errors.append(f"{rel}: variables must be a list (use [] if none)")
    else:
        seen_names: set[str] = set()
        for i, var in enumerate(variables):
            if not isinstance(var, dict):
                errors.append(f"{rel}: variables[{i}] must be a mapping")
                continue
            for vk in ("name", "description", "required"):
                if vk not in var:
                    errors.append(f"{rel}: variables[{i}] missing '{vk}'")
            name = var.get("name")
            if isinstance(name, str):
                if not VAR_NAME_RE.match(name):
                    errors.append(
                        f"{rel}: variables[{i}].name '{name}' is not snake_case"
                    )
                if name in seen_names:
                    errors.append(f"{rel}: duplicate variable name '{name}'")
                seen_names.add(name)
            if "required" in var and not isinstance(var["required"], bool):
                errors.append(
                    f"{rel}: variables[{i}].required must be a boolean"
                )
            if "description" in var:
                desc = var["description"]
                if not isinstance(desc, str) or not desc.strip():
                    errors.append(
                        f"{rel}: variables[{i}].description must be a non-empty string"
                    )

    declared_vars: set[str] = set()
    if isinstance(variables, list):
        for var in variables:
            if isinstance(var, dict) and isinstance(var.get("name"), str):
                declared_vars.add(var["name"])
    referenced_vars = set(PLACEHOLDER_RE.findall(body))
    for orphan in sorted(referenced_vars - declared_vars):
        errors.append(
            f"{rel}: prompt body references {{{{ {orphan} }}}} but it is not "
            f"declared in 'variables'"
        )
    for unused in sorted(declared_vars - referenced_vars):
        errors.append(
            f"{rel}: variable '{unused}' is declared but never referenced "
            f"as {{{{ {unused} }}}} in the body"
        )

    last_idx = -1
    last_section = None
    for sec in REQUIRED_SECTIONS:
        needle_mid = f"\n{sec}\n"
        idx = body.find(needle_mid)
        if idx == -1 and body.startswith(f"{sec}\n"):
            idx = 0
        if idx == -1:
            errors.append(f"{rel}: missing required section '{sec}'")
            continue
        if idx <= last_idx:
            errors.append(
                f"{rel}: section '{sec}' must appear after '{last_section}'"
            )
        last_idx = idx
        last_section = sec


def main() -> int:
    if not PROMPTS_DIR.exists():
        print(f"ERROR: {PROMPTS_DIR} not found", file=sys.stderr)
        return 1

    cards = sorted(PROMPTS_DIR.glob("*/*.md"))
    if not cards:
        print(f"ERROR: no prompt cards found under {PROMPTS_DIR}", file=sys.stderr)
        return 1

    errors: list[str] = []
    ids_seen: dict[str, str] = {}
    for card in cards:
        validate_card(card, errors, ids_seen)

    if errors:
        print(f"FAIL: {len(errors)} error(s) across {len(cards)} card(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK: {len(cards)} card(s) validated against schema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
