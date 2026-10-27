#!/usr/bin/env python3
"""Build the source-neutral catalogue for activity entries."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LIBRARY = ROOT / "docs" / "activities"
INDEX = LIBRARY / "ACTIVITIES-INDEX.md"


def main() -> None:
    entries = []
    for path in LIBRARY.glob("*.md"):
        if path.name in {INDEX.name, "POP-EXTRACTED-INDEX.md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        heading = re.search(r"^#\s+(.+)$", text, re.M)
        if not heading:
            continue
        tags = re.search(r"^## Tags\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        tag_text = tags.group(1).strip() if tags else ""
        entries.append((heading.group(1).strip(), path.name, tag_text))

    entries.sort(key=lambda item: (item[0].casefold(), item[1].casefold()))
    lines = [
        "# Activities Index",
        "",
        f"{len(entries)} activities from POP, Pack resources and other sources.",
        "Use tags to find a suitable activity; check each entry's source and safety notes before reuse.",
        "",
    ]
    for title, filename, tags in entries:
        line = f"- [{title}]({filename})"
        if tags:
            line += f" — {tags}"
        lines.append(line)
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {INDEX.relative_to(ROOT)} ({len(entries)} activities).")


if __name__ == "__main__":
    main()
