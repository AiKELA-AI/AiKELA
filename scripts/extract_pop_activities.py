#!/usr/bin/env python3
"""Build searchable activity libraries from structured POP Markdown.

The source programmes are retained verbatim. Programme-level advancement
claims stay labelled as programme context and are not automatically attributed
to every activity in that programme.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POP = ROOT / "docs" / "pop"
DOCS = ROOT / "docs"
SOURCE_PAGE = "https://scoutwiki.scouts.org.za/wiki/Programmes_on_a_Plate"
WOLF_SHEETS = {
    "Silver Wolf": "../Silver-Wolf-Challenge-Badge-Requirements.md",
    "Gold Wolf": "../Gold-Wolf-Challenge-Badge-Requirements.md",
}
PDF_SECTIONS = {
    "games": ("game",),
    "sense training": ("sense_training",),
    "yarn": ("yarn",),
    "craft/activity": ("activity",),
    "handcraft/activity": ("activity",),
    "singing/play acting": ("activity",),
    "singing/playacting": ("activity",),
}
GAME_WORDS = re.compile(r"\b(game|games|relay|race)\b", re.IGNORECASE)
VISUAL_WORDS = re.compile(
    r"\b(?:picture|pictures|photo|photograph|image|illustration|diagram|map|chart|template|visual|attachment)\b",
    re.IGNORECASE,
)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def normalize_requirement(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def official_page_text(level: str, page: int) -> str:
    path = ROOT / "docs" / f"{level.replace(' ', '-')}-Challenge-Badge-Requirements.md"
    if not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(
        rf"^## Source page {page}\s*$([\s\S]*?)(?=^## Source page \d+\s*$|\Z)",
        content,
        re.MULTILINE,
    )
    return normalize_requirement(match.group(1)) if match else ""


def exact_requirement_matches(level: str, text: str) -> list[dict[str, str]]:
    """Find programme claim phrases that appear in the corresponding SSA sheet."""
    matches: list[dict[str, str]] = []
    paragraphs = re.split(r"\n\s*\n", text)
    for raw_paragraph in paragraphs:
        candidate = clean(raw_paragraph)
        if not candidate:
            continue
        if ":" in candidate:
            candidate = candidate.rsplit(":", 1)[1].strip()
        candidate = re.sub(r"\([^)]*\)", "", candidate).strip()
        candidates = re.split(r"\s+[–—-]\s+", candidate)
        for phrase in candidates:
            phrase = phrase.strip(" .;,:-–—")
            normalized = normalize_requirement(phrase)
            if len(normalized) < 25 or len(normalized.split()) < 5:
                continue
            for page in range(1, 5):
                source = official_page_text(level, page)
                if normalized and normalized in source:
                    item = {
                        "matched_phrase": phrase,
                        "page": str(page),
                        "reference": f"{WOLF_SHEETS[level]}#source-page-{page}",
                        "match_basis": "programme phrase appears in the official sheet after whitespace and punctuation normalization",
                    }
                    if item not in matches:
                        matches.append(item)
    return matches


def table_cells(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in value:
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    cells.append("".join(current).strip())
    return [cell.replace(r"\|", "|").replace("<br>", " ") for cell in cells]


def metadata(path: Path, text: str) -> tuple[str, str]:
    title_match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    original_match = re.search(r"^- Original file: \[?`([^`]+)`", text, re.MULTILINE)
    return (
        title_match.group(1).strip() if title_match else path.stem.replace("_", " "),
        original_match.group(1) if original_match else "",
    )


def classify(label: str, text: str, base: tuple[str, ...] = ()) -> list[str]:
    label_value = label.casefold()
    value = f"{label} {text}".casefold()
    tags = list(base)
    if "steam release" in label_value:
        tags.append("steam_release")
    if "yarn" in label_value:
        tags.append("yarn")
    if "handcraft" in label_value or re.search(r"\bcraft\b", label_value):
        tags.append("craft")
    if GAME_WORDS.search(label_value) or "kim’s game" in label_value or "kim's game" in label_value:
        tags.append("game")
    elif "steam release" in label_value and GAME_WORDS.search(text):
        tags.append("game")
    elif "yarn" not in base and not any(word in label_value for word in ("yarn", "craft", "handcraft", "sing", "playacting", "play acting", "sense training")) and GAME_WORDS.search(text):
        tags.append("game")
    if "sense training" in label_value:
        tags.append("sense_training")
    if any(word in label_value for word in ("work session", "knotting", "instruction", "practice")):
        tags.append("skill_practice")
    if any(word in label_value for word in ("singing", "sing song", "campfire song", "song")):
        tags.append("singing")
    if "playacting" in label_value or "play acting" in label_value:
        tags.append("playacting")
    if any(word in value for word in ("grand howl", "inspection", "notices/badges", "closing parade", "clean up")):
        tags.append("ceremony_or_pack_routine")
    if not tags:
        tags.append("other_activity")
    return list(dict.fromkeys(tags))


def advancement_claims(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    heading = next((i for i, line in enumerate(lines) if re.match(r"^Advancements? covered:\s*$", line.strip(), re.I)), None)
    if heading is None:
        return []
    claims = []
    matches: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines[heading + 1 :], heading + 1):
        match = re.match(r"^\s*(Silver Wolf|Gold Wolf):\s*(.*)$", line, re.I)
        if not match:
            continue
        level = "Silver Wolf" if match.group(1).casefold() == "silver wolf" else "Gold Wolf"
        matches.append((i, level, match.group(2).strip(), line))

    for match_index, (i, level, inline, unused_line) in enumerate(matches):
        gathered = []
        if inline:
            gathered.append(inline)
        end = matches[match_index + 1][0] if match_index + 1 < len(matches) else len(lines)
        for item in lines[i + 1 : end]:
            if re.match(r"^\s*##\s+Page\s+\d+", item, re.I):
                continue
            if re.fullmatch(r"\s*\d+\s*", item):
                continue
            gathered.append(item.strip())
        body = "\n".join(gathered).strip()
        body = re.sub(r"\n{3,}", "\n\n", body)
        if body:
            claims.append({
                "level": level,
                "source_text": body,
                "scope": "programme-level statement; source does not necessarily assign every listed item to a particular activity",
                "advancement_sheet": WOLF_SHEETS[level],
                "official_requirement_matches": exact_requirement_matches(level, body),
            })
    if not claims:
        gathered = []
        for item in lines[heading + 1 :]:
            if re.match(r"^\s*##\s+Page\s+\d+", item, re.I) or re.fullmatch(r"\s*\d+\s*", item):
                continue
            gathered.append(item.strip())
        body = re.sub(r"\n{3,}", "\n\n", "\n".join(gathered).strip())
        if body:
            claims.append({
                "level": "Programme note",
                "source_text": body,
                "scope": "programme-level advancement or badge note; not individually attributed to a particular activity",
                "advancement_sheet": "",
                "official_requirement_matches": [],
            })
    return claims


def activity_advancement_claims(text: str) -> list[dict[str, str]]:
    claims = []
    pattern = re.compile(
        r"\b(Silver|Gold)\s+Wolf\s+requirements?\s*(?:[-:–])\s*([^.;]+)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        level = "Silver Wolf" if match.group(1).casefold() == "silver" else "Gold Wolf"
        claims.append({
            "level": level,
            "source_text": clean(match.group(2)),
            "scope": "activity text explicitly mentions this requirement; verify the match against the official sheet",
            "advancement_sheet": WOLF_SHEETS[level],
            "official_requirement_matches": exact_requirement_matches(level, match.group(2)),
        })
    return claims


def visual_reference_notes(*texts: str) -> list[str]:
    """Return short source excerpts that signal a required visual or attachment."""
    found: list[str] = []
    for text in texts:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
            sentence = clean(sentence.strip(" |-*"))
            if sentence and VISUAL_WORDS.search(sentence) and sentence not in found:
                found.append(sentence[:500])
    return found


def advancement_link_status(
    activity_claims: list[dict[str, str]],
    programme_claims: list[dict[str, str]],
) -> dict[str, Any]:
    """Expose the best available link without assigning programme claims to an activity."""
    if activity_claims:
        return {
            "status": "activity-specific source wording; verify against SSA sheet",
            "claims": activity_claims,
            "programme_context_only": [],
        }
    return {
        "status": "no activity-specific requirement link established",
        "claims": [],
        "programme_context_only": programme_claims,
    }


def new_record(
    *, program: str, original: str, markdown: str, line: int, label: str,
    activity_text: str, minutes: str = "", equipment: str = "", scouter: str = "",
    context: list[str] | None = None, base_categories: tuple[str, ...] = (),
    name: str = "", detail_status: str = "source text available",
    claims: list[dict[str, str]] | None = None, page_url: str = SOURCE_PAGE,
) -> dict[str, Any]:
    activity_claims = activity_advancement_claims(activity_text)
    visual_notes = visual_reference_notes(activity_text, *(context or []), equipment)
    return {
        "id": "",
        "name": name,
        "programme": program,
        "source_activity_label": label,
        "categories": classify(label, activity_text, base_categories),
        "minutes": minutes,
        "activity_text": activity_text,
        "detail_status": detail_status,
        "equipment": equipment,
        "scouter_note": scouter,
        "programme_notes_before_activity": context or [],
        "programme_advancement_claims": claims or [],
        "activity_specific_advancement_claims": activity_claims,
        "advancement_badge_link": advancement_link_status(activity_claims, claims or []),
        "visual_reference_notes": visual_notes,
        "visual_reference_status": "visual or attachment mentioned in extracted text" if visual_notes else "no visual explicitly mentioned in extracted activity text; inspect original source if visuals may be embedded",
        "advancement_mapping_scope": "programme-level context unless the POP source explicitly connects this activity to a named requirement",
        "source_markdown": markdown,
        "source_original": original,
        "source_markdown_line": line,
        "source_page": page_url,
    }


def extract_table_activities(path: Path, text: str, program: str, original: str, claims: list[dict[str, str]]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    in_table = False
    pending_notes: list[str] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.lstrip().startswith("|"):
            if in_table and not line.strip():
                continue
            if in_table:
                in_table = False
            continue
        cells = table_cells(line)
        if len(cells) >= 3 and cells[0].casefold() == "time" and cells[1].casefold() == "min" and cells[2].casefold() == "activity":
            in_table = True
            pending_notes = []
            continue
        if not in_table or len(cells) < 3:
            continue
        if all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
            continue
        if cells[0].casefold() == "time" and cells[1].casefold() == "min":
            continue  # repeated heading at a page break
        activity = cells[2].strip()
        if not activity:
            continue
        if activity.startswith("**Programme note:**"):
            pending_notes.append(re.sub(r"^\*\*Programme note:\*\*\s*", "", activity).strip())
            continue
        label_match = re.match(r"^([^:]{2,60}):\s*", activity)
        label = label_match.group(1).strip() if label_match else ""
        detail_status = "activity row extracted; name and instructions remain combined as in source"
        if "yarn" in label.casefold() and len(activity) < 110:
            detail_status = "yarn title/reference only; narrative is not present in this programme row"
        found.append(new_record(
            program=program,
            original=original,
            markdown=path.name,
            line=line_no,
            label=label,
            activity_text=activity,
            minutes=cells[1].strip(),
            equipment=cells[3].strip() if len(cells) > 3 else "",
            scouter=cells[4].strip() if len(cells) > 4 else "",
            context=pending_notes,
            claims=claims,
            detail_status=detail_status,
        ))
        pending_notes = []
    return found


def extract_fixed_width_activities(path: Path, text: str, program: str, original: str, claims: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Read legacy PDF activity tables laid out with fixed-width columns."""
    lines = text.splitlines()
    found: list[dict[str, Any]] = []
    header: tuple[int, int, int, int, int] | None = None
    current: dict[str, Any] | None = None
    pending_context: list[str] = []
    context_paragraph: list[str] = []

    def flush_context() -> None:
        nonlocal context_paragraph
        if context_paragraph:
            value = clean(" ".join(context_paragraph))
            if value:
                pending_context.append(value)
        context_paragraph = []

    def flush_record() -> None:
        nonlocal current, pending_context
        if current is None:
            return
        activity = clean(" ".join(current["activity"]))
        if activity:
            label_match = re.match(r"^([A-Z][A-Z’' /-]{1,45}):\s*", activity)
            label = label_match.group(1).strip() if label_match else ""
            detail_status = "legacy PDF table row extracted; column alignment preserved from layout text"
            if "yarn" in label.casefold() and len(activity) < 110:
                detail_status = "yarn title/reference only; narrative is not present in this programme row"
            found.append(new_record(
                program=program,
                original=original,
                markdown=path.name,
                line=current["line"],
                label=label,
                activity_text=activity,
                minutes=current["minutes"],
                equipment=clean(" ".join(current["equipment"])),
                scouter=clean(" ".join(current["scouter"])),
                context=pending_context,
                claims=claims,
                detail_status=detail_status,
            ))
        current = None
        pending_context = []

    for line_no, line in enumerate(lines, 1):
        if "Time" in line and "Min" in line and "Activity" in line and "Equipment" in line and "Scouter" in line and not line.lstrip().startswith("|"):
            flush_context()
            header = tuple(line.find(name) for name in ("Time", "Min", "Activity", "Equipment", "Scouter"))  # type: ignore[assignment]
            continue
        if header is None:
            continue
        if line.startswith("## Page "):
            flush_context()
            continue
        time_start, min_start, activity_start, equipment_start, scouter_start = header
        padded = line + " " * max(0, scouter_start + 1 - len(line))
        min_cell = padded[min_start:activity_start].strip()
        activity_cell = padded[activity_start:equipment_start].strip()
        equipment_cell = padded[equipment_start:scouter_start].strip()
        scouter_cell = padded[scouter_start:].strip()

        if re.fullmatch(r"\d{1,2}", min_cell):
            flush_context()
            flush_record()
            current = {
                "line": line_no,
                "minutes": min_cell,
                "activity": [activity_cell] if activity_cell else [],
                "equipment": [equipment_cell] if equipment_cell else [],
                "scouter": [scouter_cell] if scouter_cell else [],
            }
            continue
        if current is not None and line.strip() and not line[0].isspace():
            flush_record()
            context_paragraph.append(line.strip())
            continue
        if current is not None and (activity_cell or equipment_cell or scouter_cell):
            if activity_cell:
                current["activity"].append(activity_cell)
            if equipment_cell:
                current["equipment"].append(equipment_cell)
            if scouter_cell:
                current["scouter"].append(scouter_cell)
            continue
        if line.strip() and not line[0].isspace():
            context_paragraph.append(line.strip())
        elif not line.strip():
            flush_context()

    flush_context()
    flush_record()
    return found


def section_key(line: str) -> str | None:
    key = clean(line).casefold().rstrip(": ")
    return key if key in PDF_SECTIONS or key in {"advancement covered", "advancements covered"} else None


def section_blocks(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    blocks = []
    i = 0
    while i < len(lines):
        key = section_key(lines[i])
        if key not in PDF_SECTIONS:
            i += 1
            continue
        start = i
        body = []
        i += 1
        while i < len(lines) and section_key(lines[i]) is None:
            body.append(lines[i])
            i += 1
        blocks.append((key, start + 1, body))
    return blocks


def nonempty_paragraphs(lines: list[str]) -> list[str]:
    paragraphs = []
    current: list[str] = []
    for line in lines:
        if re.match(r"^\s*##\s+Page\s+\d+", line, re.I) or re.fullmatch(r"\s*\d+\s*", line):
            continue
        value = line.strip()
        if value:
            current.append(value)
        elif current:
            paragraphs.append(clean(" ".join(current)))
            current = []
    if current:
        paragraphs.append(clean(" ".join(current)))
    return [p for p in paragraphs if p]


def numbered_entries(lines: list[str]) -> list[tuple[int, str, str, str]]:
    entries: list[tuple[int, str, str, str]] = []
    current_line = 0
    current_head = ""
    current_tail: list[str] = []
    for index, line in enumerate(lines, 1):
        if re.match(r"^\s*##\s+Page\s+\d+", line, re.I) or re.fullmatch(r"\s*\d+\s*", line):
            continue
        match = re.match(r"^\s*\d+[.)]\s+([^\n]+?:\s*.+?)\s*$", line)
        if match:
            if current_head:
                entries.append((current_line, current_head, " ".join(current_tail), ""))
            current_line = index
            current_head = clean(match.group(1))
            current_tail = []
        elif current_head:
            if line.strip():
                current_tail.append(line.strip())
    if current_head:
        entries.append((current_line, current_head, " ".join(current_tail), ""))
    return entries


def extract_pdf_sections(path: Path, text: str, program: str, original: str, claims: list[dict[str, str]]) -> list[dict[str, Any]]:
    lines = text.splitlines()
    found: list[dict[str, Any]] = []
    for key, section_line, body in section_blocks(lines):
        base = PDF_SECTIONS[key]
        if key == "yarn":
            paragraphs = nonempty_paragraphs(body)
            story = "\n\n".join(paragraphs)
            if not story:
                continue
            is_reference = len(story) < 100 or bool(re.search(r"\b(?:yarn|story)\s+module\s*:\s*page\s*\d+", story, re.I))
            first = paragraphs[0] if paragraphs else ""
            # Keep a likely story heading separate only as a title; preserve the full text below.
            name = first.strip(" :") if first and len(first) < 100 else ""
            found.append(new_record(
                program=program, original=original, markdown=path.name,
                line=section_line, label="YARN section", activity_text=story,
                base_categories=base,
                detail_status="title_or_module_reference_only" if is_reference else "story_text_extracted",
                claims=claims,
            ))
            continue

        items = numbered_entries(body)
        if not items:
            paragraphs = nonempty_paragraphs(body)
            for paragraph in paragraphs:
                if len(paragraph) < 15:
                    continue
                found.append(new_record(
                    program=program, original=original, markdown=path.name,
                    line=section_line, label=key.title(), activity_text=paragraph,
                    base_categories=base, claims=claims,
                ))
            continue

        # Numbered-entry line indexes are local to the section body.
        for offset, head, detail, unused in items:
            kind_match = re.match(r"^([^:]{1,45}):\s*(.*)$", head)
            if kind_match:
                label = kind_match.group(1).strip()
                name = kind_match.group(2).strip()
            else:
                label = key.title()
                name = head
            activity_text = detail.strip() or head
            status = "full_activity_text_extracted" if detail else "title_or_reference_only"
            found.append(new_record(
                program=program, original=original, markdown=path.name,
                line=section_line + offset, label=label, activity_text=activity_text,
                name=name, base_categories=base, detail_status=status, claims=claims,
            ))
    return found


def extract_all() -> list[dict[str, Any]]:
    all_records: list[dict[str, Any]] = []
    for path in sorted(POP.glob("*.md")):
        if path.name == "conversion-errors.json":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        program, original = metadata(path, text)
        claims = advancement_claims(text)
        table_records = extract_table_activities(path, text, program, original, claims)
        fixed_width_records = extract_fixed_width_activities(path, text, program, original, claims)
        pdf_records = extract_pdf_sections(path, text, program, original, claims)
        all_records.extend(table_records)
        all_records.extend(fixed_width_records)
        all_records.extend(pdf_records)
    for index, record in enumerate(all_records, 1):
        record["id"] = f"POP-ACT-{index:04d}"
    return all_records


def source_links(record: dict[str, Any]) -> str:
    links = [f"[POP Markdown](../pop/{record['source_markdown']})"]
    if record["source_original"]:
        links.append(f"[original source: {record['source_original']}]({SOURCE_PAGE})")
    return ", ".join(links)


def render_record(record: dict[str, Any]) -> list[str]:
    lines = [
        f"### {record['id']} — {record['programme']} ({', '.join(record['categories'])})",
        "",
        f"- **Source activity label:** {record['source_activity_label'] or 'Not labelled in source'}",
        f"- **Time:** {record['minutes'] + ' min' if record['minutes'].isdigit() else 'Not stated'}",
        f"- **Equipment:** {record['equipment'] or 'Not stated in source'}",
        f"- **Source:** {source_links(record)}",
        f"- **Source line:** {record['source_markdown_line']}",
        f"- **Detail status:** {record['detail_status']}",
        f"- **Advancement / badge link:** {record['advancement_badge_link']['status']}",
    ]
    link = record["advancement_badge_link"]
    if link["claims"]:
        for claim in link["claims"]:
            lines.append(f"  - **{claim['level']}:** {claim['source_text'].replace(chr(10), ' ')} ([advancement sheet]({claim['advancement_sheet']}))")
            if claim["official_requirement_matches"]:
                for match in claim["official_requirement_matches"]:
                    lines.append(f"    - Matching wording: “{match['matched_phrase']}” ([sheet page {match['page']}]({match['reference']})); check the complete requirement.")
            else:
                lines.append("    - No matching wording was located automatically; Scouter review is needed.")
    elif link["programme_context_only"]:
        lines.append("  - POP gives advancement/badge context for the programme, but does not attribute it to this activity:")
        for claim in link["programme_context_only"]:
            ref = f" ([advancement sheet]({claim['advancement_sheet']}))" if claim["advancement_sheet"] else ""
            lines.append(f"    - **{claim['level']}:** {claim['source_text'].replace(chr(10), ' ')}{ref}")
    else:
        lines.append("  - No requirement is stated or verified for this activity. Review the relevant SSA sheet before assigning one.")
    if record["programme_advancement_claims"]:
        lines.extend([
            "- **POP programme advancement / badge information (copied to this activity; not yet narrowed to this item):**",
        ])
        for claim in record["programme_advancement_claims"]:
            reference = f" ([advancement sheet]({claim['advancement_sheet']}))" if claim["advancement_sheet"] else ""
            lines.append(f"  - **{claim['level']}:** {claim['source_text'].replace(chr(10), ' ')}{reference}")
            for match in claim["official_requirement_matches"]:
                lines.append(f"    - Matching wording: “{match['matched_phrase']}” ([sheet page {match['page']}]({match['reference']})); check the complete requirement.")
    else:
        lines.append("- **POP programme advancement / badge information:** None stated in the source programme.")
    lines.append(f"- **Visual aid / image reference:** {record['visual_reference_status']}.")
    if record["visual_reference_notes"]:
        for note in record["visual_reference_notes"]:
            lines.append(f"  - Source note: {note}")
    lines.append(f"  - Check [POP Markdown](../pop/{record['source_markdown']}) and the original source ({record['source_original']}; [find it on ScoutWiki]({SOURCE_PAGE})) for embedded visuals or linked attachments." if record["source_original"] else f"  - Check [POP Markdown](../pop/{record['source_markdown']}) for any visual aids.")
    if record["programme_notes_before_activity"]:
        lines.append("- **Preceding programme notes:** " + " / ".join(record["programme_notes_before_activity"]))
    lines.append("")
    if record["name"]:
        lines.extend([f"**Name in source:** {record['name']}", ""])
    lines.extend(["**POP activity text:**", "", record["activity_text"], ""])
    lines.append("")
    return lines


def write_library(path: Path, title: str, records: list[dict[str, Any]], preface: list[str]) -> None:
    lines = [f"# {title}", "", *preface, ""]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["source_markdown"]].append(record)
    for source, group in grouped.items():
        lines.extend([f"## {group[0]['programme']}", "", f"Source programme: [open POP Markdown](../pop/{source})", ""])
        for record in group:
            lines.extend(render_record(record))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def programme_coverage_index(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    programmes: dict[str, dict[str, Any]] = {}
    for record in records:
        if not record["programme_advancement_claims"]:
            continue
        programmes.setdefault(record["source_markdown"], {
            "programme": record["programme"],
            "source_markdown": record["source_markdown"],
            "source_original": record["source_original"],
            "source_page": record["source_page"],
            "claims": record["programme_advancement_claims"],
        })
    return [programmes[key] for key in sorted(programmes)]


def write_programme_coverage(path: Path, programmes: list[dict[str, Any]]) -> None:
    write_jsonl(path.with_suffix(".jsonl"), programmes)
    lines = [
        "# POP Programme-Level Advancement and Badge Notes",
        "",
        f"Statements extracted from {len(programmes)} POP programme sources.",
        "These are programme-level statements, not proof that every activity in that programme meets every listed requirement.",
        "A phrase match points to wording in a supplied SSA advancement sheet; check the full sheet requirement and the original POP context.",
        "",
    ]
    for programme in programmes:
        lines.extend([
            f"## {programme['programme']}",
            "",
            f"Source: [POP Markdown](../pop/{programme['source_markdown']})" + (f", original source: [`{programme['source_original']}`]({SOURCE_PAGE})" if programme['source_original'] else ""),
            "",
        ])
        for claim in programme["claims"]:
            suffix = f" ([advancement sheet]({claim['advancement_sheet']}))" if claim["advancement_sheet"] else ""
            lines.append(f"- **{claim['level']}:** {claim['source_text'].replace(chr(10), ' ')}{suffix}")
            for match in claim["official_requirement_matches"]:
                lines.append(f"  - Matching wording: “{match['matched_phrase']}” ([sheet page {match['page']}]({match['reference']})); check the full requirement on that page.")
        lines.append("")
    path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not POP.is_dir():
        raise SystemExit(f"POP Markdown folder not found: {POP}")
    records = extract_all()
    activities_dir = DOCS / "activities"
    write_jsonl(activities_dir / "POP-activity-catalog.jsonl", records)
    coverage = programme_coverage_index(records)
    write_programme_coverage(activities_dir / "POP-programme-advancement", coverage)
    write_library(
        activities_dir / "POP-activity-catalog.md",
        "POP Activity Catalog",
        records,
        [
            f"First-pass catalog of {len(records)} activity records extracted from structured POP programmes.",
            "Categories preserve source labels and flag broad activity types; they do not establish that an activity satisfies a badge requirement.",
            "Programme-level advancement statements are kept as programme context. Only a source that explicitly connects an activity and requirement supports activity-level attribution.",
        ],
    )

    category_specs = {
        "game": ("games", "POP Game Library", "Game, relay, race and named game entries extracted from POP programme activities."),
        "yarn": ("yarns", "POP Yarn Library", "Yarn entries and story text extracted from POP. Title-only and module-reference entries are labelled as such; no missing story is invented."),
        "craft": ("crafts", "POP Craft Library", "Handcraft and craft/activity entries extracted from POP."),
        "skill_practice": ("activities", "POP Skills and Practice Activities", "Work sessions, knotting, instruction and practice activities extracted from POP."),
        "sense_training": ("activities", "POP Sense-Training Activities", "Sense-training entries extracted from POP."),
        "singing": ("activities", "POP Singing Activities", "Singing and song entries extracted from POP."),
        "playacting": ("activities", "POP Playacting Activities", "Playacting entries extracted from POP."),
    }
    for category, (folder, title, description) in category_specs.items():
        selected = [record for record in records if category in record["categories"]]
        if folder == "activities":
            stem = category.replace("_", "-")
            write_jsonl(DOCS / "activities" / f"POP-{stem}.jsonl", selected)
            write_library(DOCS / "activities" / f"POP-{stem}.md", title, selected, [description])
        elif folder == "games":
            write_jsonl(DOCS / "games" / "POP-game-library.jsonl", selected)
            write_library(DOCS / "games" / "POP-game-library.md", title, selected, [description])
        elif folder == "yarns":
            write_jsonl(DOCS / "yarns" / "POP-yarn-library.jsonl", selected)
            write_library(DOCS / "yarns" / "POP-yarn-library.md", title, selected, [description])
        elif folder == "crafts":
            write_jsonl(DOCS / "crafts" / "POP-craft-library.jsonl", selected)
            write_library(DOCS / "crafts" / "POP-craft-library.md", title, selected, [description])

    counts: dict[str, int] = defaultdict(int)
    for record in records:
        for category in record["categories"]:
            counts[category] += 1
    print(f"Extracted {len(records)} activity records from {len({r['source_markdown'] for r in records})} POP programmes.")
    print("Category records (multi-category activities counted in each category):")
    for category, count in sorted(counts.items()):
        print(f"  {category}: {count}")
    print(f"Libraries written under {DOCS}")


if __name__ == "__main__":
    main()
