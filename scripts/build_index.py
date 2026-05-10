#!/usr/bin/env python3
"""Generate INDEX.md from all prompt cards under prompts/.

Run from repo root:

    python scripts/build_index.py

Reads frontmatter from every prompts/*/*.md file and emits a catalog grouped
by direction and a tag matrix. Run validate.py first; this script trusts
that frontmatter is well-formed.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
INDEX_PATH = REPO_ROOT / "INDEX.md"

DIRECTION_ORDER = ["rag", "agent", "rlhf", "sft", "multimodal", "cot", "eval", "code"]
DIRECTION_LABEL = {
    "rag": "RAG",
    "agent": "Agent",
    "rlhf": "RLHF",
    "sft": "SFT",
    "multimodal": "Multimodal",
    "cot": "Chain-of-Thought",
    "eval": "Evaluation",
    "code": "Code",
}


def parse_card(path: Path) -> tuple[dict, str]:
    """Return (frontmatter, body) for a card file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing frontmatter")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        raise ValueError(f"{path}: unterminated frontmatter")
    fm = yaml.safe_load(rest[:end])
    if not isinstance(fm, dict):
        raise ValueError(f"{path}: frontmatter is not a mapping")
    body = rest[end + 5:]
    return fm, body


def extract_use_when(body: str) -> str:
    """Extract a one-line 'use when' summary from the card body.

    Preferred source: the `**Use when:**` line in `## Quick Use`. That is
    the beginner-facing one-liner authored deliberately for this purpose.
    Fallback: first sentence of `## Purpose` (for legacy cards that may
    pre-date the Quick Use convention).
    """
    # Try Quick Use first
    qu_marker = "\n## Quick Use\n"
    qu_idx = body.find(qu_marker)
    if qu_idx == -1 and body.startswith("## Quick Use\n"):
        qu_idx = 0
        qu_start = len("## Quick Use\n")
    elif qu_idx != -1:
        qu_start = qu_idx + len(qu_marker)
    else:
        qu_start = -1
    if qu_start >= 0:
        next_section = body.find("\n## ", qu_start)
        quick_block = body[qu_start:next_section if next_section != -1 else None]
        for line in quick_block.splitlines():
            line = line.strip()
            if line.lower().startswith("**use when:**"):
                value = line[len("**use when:**"):].strip().rstrip(".")
                if value:
                    if len(value) > 180:
                        value = value[:177].rstrip() + "..."
                    return value

    # Fallback: first sentence of Purpose
    marker = "\n## Purpose\n"
    idx = body.find(marker)
    if idx == -1 and body.startswith("## Purpose\n"):
        idx = 0
        section_start = idx + len("## Purpose\n")
    elif idx != -1:
        section_start = idx + len(marker)
    else:
        return ""
    next_section = body.find("\n## ", section_start)
    purpose = body[section_start:next_section if next_section != -1 else None].strip()
    # Take the first sentence: up to the first period followed by space, or first newline-newline.
    para_end = purpose.find("\n\n")
    if para_end != -1:
        purpose = purpose[:para_end]
    purpose = purpose.replace("\n", " ").strip()
    # Walk forward looking for a real sentence boundary, skipping common
    # abbreviations like "i.e.", "e.g.", "etc.", "vs.", "Mr.", "Dr." that
    # contain "." but should not split a sentence.
    abbrev_blocklist = ("i.e.", "e.g.", "etc.", "vs.", "mr.", "dr.", "mrs.", "ms.")
    pos = 0
    chosen = -1
    while True:
        idx = purpose.find(". ", pos)
        if idx == -1:
            break
        # Look at the 5 chars ending at idx+1 (the period). If they form a
        # known abbreviation, skip past and keep searching.
        prefix = purpose[max(0, idx - 4):idx + 1].lower()
        if any(prefix.endswith(ab) for ab in abbrev_blocklist):
            pos = idx + 2
            continue
        chosen = idx
        break
    if 0 < chosen < 200:
        purpose = purpose[:chosen + 1]
    # Hard cap to keep table cells reasonable.
    if len(purpose) > 180:
        purpose = purpose[:177].rstrip() + "..."
    return purpose


def main() -> int:
    cards = sorted(PROMPTS_DIR.glob("*/*.md"))
    if not cards:
        print(f"ERROR: no prompt cards found under {PROMPTS_DIR}", file=sys.stderr)
        return 1

    by_dir: dict[str, list[tuple[dict, str, str]]] = defaultdict(list)
    by_tag: dict[str, list[tuple[dict, str]]] = defaultdict(list)

    for path in cards:
        fm, body = parse_card(path)
        rel = path.relative_to(REPO_ROOT).as_posix()
        use_when = extract_use_when(body)
        by_dir[fm["direction"]].append((fm, rel, use_when))
        for tag in fm.get("tags", []):
            by_tag[tag].append((fm, rel))

    lines: list[str] = []
    lines.append("# prompt-atlas Index")
    lines.append("")
    lines.append("> Auto-generated by `scripts/build_index.py`. Do not edit by hand.")
    lines.append("")
    lines.append(f"**Total cards:** {len(cards)}")
    lines.append("")
    lines.append("## Cards by direction")
    lines.append("")

    for direction in DIRECTION_ORDER:
        items = by_dir.get(direction)
        if not items:
            continue
        lines.append(f"### {DIRECTION_LABEL[direction]} (`{direction}`)")
        lines.append("")
        lines.append("| Card | Use when | Status | Tags |")
        lines.append("|------|----------|--------|------|")
        for fm, rel, use_when in sorted(items, key=lambda triple: triple[0]["id"]):
            link = f"[{fm['title']}]({rel})"
            tags = ", ".join(f"`{t}`" for t in fm["tags"])
            # Escape pipe characters in use_when for table safety
            cell = use_when.replace("|", "\\|") if use_when else ""
            lines.append(
                f"| {link} | {cell} | `{fm['status']}` | {tags} |"
            )
        lines.append("")

    lines.append("## Cards by tag")
    lines.append("")
    for tag in sorted(by_tag):
        items = sorted(by_tag[tag], key=lambda pair: pair[0]["id"])
        items_str = ", ".join(f"[{fm['title']}]({rel})" for fm, rel in items)
        lines.append(f"- **`{tag}`** — {items_str}")
    lines.append("")

    INDEX_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK: wrote {INDEX_PATH.relative_to(REPO_ROOT).as_posix()} with {len(cards)} card(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
