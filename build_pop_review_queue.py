#!/usr/bin/env python3
"""Create a compact, just-in-time review queue from reconstructed POP files."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
POP = ROOT / "docs" / "pop"
PROGRAMMES = POP / "programmes"
ELEMENT_FOLDERS = [ROOT / "docs" / folder for folder in ("games", "yarns", "crafts", "activities")]
VISUAL_CUES = re.compile(r"\b(?:picture|pictures|photo|photograph|image|illustration|diagram|map|chart|template|visual|layout|plan|sketch)\b", re.I)


def title(path: Path) -> str:
    match = re.search(r"^#\s+(.+)$", path.read_text(encoding="utf-8", errors="replace"), re.M)
    return match.group(1).strip() if match else path.stem


def main() -> None:
    programmes = sorted(PROGRAMMES.glob("*.md"))
    elements = []
    for folder in ELEMENT_FOLDERS:
        for path in folder.glob("*.md"):
            if path.name == "POP-EXTRACTED-INDEX.md":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "## Source" in text and ("- [Converted source document]" in text or "- [Converted attachment]" in text):
                elements.append(path)
    elements.sort()
    instructions_gaps, visual_gaps, advancement_gaps = [], [], []
    for path in elements:
        text = path.read_text(encoding="utf-8", errors="replace")
        instructions = text.split("## Instructions", 1)[-1].split("## Advancement covered / badge link", 1)[0]
        visual_section = text.split("## Visual aid / image reference", 1)[-1].split("## Tags", 1)[0]
        has_picture = bool(re.search(r"!\[[^\]]*\]\(", instructions + visual_section))
        if any(marker in instructions.casefold() for marker in ("no readable instructions", "title or reference", "title/reference")):
            instructions_gaps.append(path)
        if VISUAL_CUES.search(instructions) and not has_picture:
            visual_gaps.append(path)
        advancement = text.split("## Advancement covered / badge link", 1)[-1].split("## Visual aid / image reference", 1)[0]
        if "No exact wording match" in advancement:
            advancement_gaps.append(path)

    uncertain_pairs = []
    for path in programmes:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "Probable name match" in text or "verify the pairing" in text.casefold():
            uncertain_pairs.append(path)

    lines = [
        "# POP Review Queue", "",
        f"Current first pass: {len(programmes)} programme drafts and {len(elements)} standalone elements, built from all 170 retained source documents.",
        "Use the programme you plan to run as the review unit. Its schedule, full attachment text, source visuals and linked elements are together; open a flagged element only when that programme needs it.",
        "",
        "## Highest priority", "",
        f"- **Source pairing:** {len(uncertain_pairs)} programme pairing(s) need confirmation.",
    ]
    for path in uncertain_pairs:
        lines.append(f"  - [{title(path)}](programmes/{path.name})")
    lines.extend([
        f"- **Instructions:** {len(instructions_gaps)} elements have a title/reference or incomplete source instructions. Review before using one.",
        f"- **Visuals:** {len(visual_gaps)} elements mention a picture, diagram, map, template or layout without an inline image in the extracted instructions. The programme and source links retain the original visual for comparison.",
        f"- **Advancement:** {len(advancement_gaps)} elements include source task wording without a close Silver/Gold sheet wording match. Each keeps the historical task and says the mapping needs Scouter review.",
        "",
        "## Flagged items", "",
        "The lists below are available when a flagged item is relevant to a planned programme. The element indexes remain the searchable catalogues.",
        "",
        "<details><summary>Instruction details needing review</summary>", "",
    ])
    for path in instructions_gaps:
        folder = path.parent.name
        lines.append(f"- [{title(path)}](../{folder}/{path.name})")
    lines.extend(["", "</details>", "", "<details><summary>Unmatched visual references</summary>", ""])
    for path in visual_gaps:
        folder = path.parent.name
        lines.append(f"- [{title(path)}](../{folder}/{path.name})")
    lines.extend(["", "</details>", "", "<details><summary>Advancement wording to review if used</summary>", ""])
    for path in advancement_gaps:
        folder = path.parent.name
        lines.append(f"- [{title(path)}](../{folder}/{path.name})")
    lines.extend(["", "</details>", "", "## Catalogue indexes", ""])
    for folder in ELEMENT_FOLDERS:
        index = folder / "POP-EXTRACTED-INDEX.md"
        if index.is_file():
            lines.append(f"- [{folder.name.title()}](../{folder.name}/{index.name})")
    lines.extend(["", "- [All programme drafts](PROGRAMME-DRAFT-INDEX.md)", ""])
    (POP / "POP-REVIEW-QUEUE.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote docs/pop/POP-REVIEW-QUEUE.md ({len(programmes)} programmes; {len(elements)} elements; {len(instructions_gaps)} instruction, {len(visual_gaps)} visual, {len(advancement_gaps)} advancement flags).")


if __name__ == "__main__":
    main()
