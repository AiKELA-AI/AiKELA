#!/usr/bin/env python3
"""Build the source-neutral catalogue for all game entries."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GAMES = ROOT / "docs" / "games"
INDEX = GAMES / "GAMES-INDEX.md"
POP_INDEX = GAMES / "POP-EXTRACTED-INDEX.md"


def main() -> None:
    entries = []
    pop_entries = []
    for path in GAMES.glob("*.md"):
        if path.name in {INDEX.name, "POP-EXTRACTED-INDEX.md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        heading = re.search(r"^#\s+(.+)$", text, re.M)
        if not heading:
            continue
        tags = re.search(r"^## Tags\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        tag_text = tags.group(1).strip() if tags else ""
        entries.append((heading.group(1).strip(), path.name, tag_text))
        if re.search(r"\.\./pop/(?:source-conversions|src)/", text):
            pop_entries.append((heading.group(1).strip(), path.name, tag_text))

    entries.sort(key=lambda item: (item[0].casefold(), item[1].casefold()))
    lines = [
        "# Games Index",
        "",
        f"{len(entries)} games from POP, Pack resources and other sources.",
        "Use tags to find games that fit a programme; check each entry's source and safety notes before use.",
        "",
    ]
    for title, filename, tags in entries:
        line = f"- [{title}]({filename})"
        if tags:
            line += f" — {tags}"
        lines.append(line)
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {INDEX.relative_to(ROOT)} ({len(entries)} games).")

    pop_entries.sort(key=lambda item: (item[0].casefold(), item[1].casefold()))
    pop_lines = [
        "# POP Extracted Games Index",
        "",
        f"{len(pop_entries)} source-based game files. Review the linked source and safety before reuse.",
        "",
    ]
    for title, filename, tags in pop_entries:
        line = f"- [{title}]({filename})"
        if tags:
            line += f" — {tags}"
        pop_lines.append(line)
    POP_INDEX.write_text("\n".join(pop_lines) + "\n", encoding="utf-8")
    print(f"Wrote {POP_INDEX.relative_to(ROOT)} ({len(pop_entries)} games).")


if __name__ == "__main__":
    main()
