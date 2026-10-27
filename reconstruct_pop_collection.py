#!/usr/bin/env python3
"""Build first-pass POP programme drafts and standalone elements.

Input is the preserved source-conversion archive. The script keeps source
wording, combines clear programme/attachment pairs, and labels inferred links
for Scouter review. It never edits docs/pop/src or overwrites a hand-edited
element with the same name.
"""

from __future__ import annotations

import re
from functools import lru_cache
from difflib import SequenceMatcher
from pathlib import Path

from extract_pop_activities import (activity_advancement_claims, advancement_claims,
                                    extract_fixed_width_activities, extract_table_activities)


ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "docs" / "pop" / "source-conversions"
PROGRAMMES = ROOT / "docs" / "pop" / "programmes"
FOLDERS = {"game": ROOT / "docs" / "games", "yarn": ROOT / "docs" / "yarns",
           "craft": ROOT / "docs" / "crafts", "activity": ROOT / "docs" / "activities"}
ALLOCATED_TARGETS: set[str] = set()
ATTACHMENT_RE = re.compile(r"attachment", re.I)
LABEL_RE = re.compile(r"^\|\s*([^|]{1,50}?)\s*:\s*\|\s*([^|]*?)\s*\|\s*$", re.I)
VALID_TYPES = {
    "yarn": "yarn", "story": "yarn", "singing": "activity", "sing song": "activity",
    "playacting": "activity", "activity": "activity", "handcraft": "craft",
    "craft": "craft", "steam release": "game", "games": "game", "game": "game",
    "team game": "game", "relay game": "game", "quiet game": "game",
    "circle game": "game", "revision game": "game", "sense training": "activity",
    "inspection": "activity", "work session": "activity", "trail": "activity",
    "trail signs": "activity", "first aid": "activity", "tie two knots": "activity",
    "candle lighting": "activity", "requirements": "activity", "alternate game": "game",
}
LEVELS = {"caracal", "cheetah", "leopard", "lion", "silver wolf", "gold wolf"}
KEYWORDS = {
    "birds": ("bird", "eagle", "owl", "nest", "feather", "wing"),
    "wildlife": ("animal", "beast", "wildlife", "insect", "bug", "gogga"),
    "jungle": ("jungle", "tarzan", "monkey", "tree tops"),
    "jungle-book": ("jungle book", "mowgli", "baloo", "bagheera", "akela"),
    "water": ("water", "sea", "ocean", "river", "boat", "ship", "swim"),
    "space": ("space", "rocket", "moon", "astronaut", "planet"),
    "nature": ("nature", "plant", "tree", "garden", "conservation", "outdoor"),
    "history": ("history", "ancient", "pharaoh", "pyramid", "colossus", "babylon", "statue"),
    "south-africa": ("south africa", "south african", "sa flag", "african"),
    "food": ("food", "fruit", "vegetable", "cooking", "kitchen", "healthy eating"),
    "health": ("health", "hygiene", "first aid", "body", "clean", "safety"),
    "transport": ("train", "plane", "car", "bicycle", "transport", "vehicle", "ship"),
    "maps-and-compass": ("compass", "map", "direction", "north", "trail signs"),
}


def norm(value: str) -> str:
    value = value.casefold().replace(".pdf.md", "").replace(".docx.md", "").replace(".doc.md", "")
    value = re.sub(r"[_ -]?attachment", "", value)
    value = re.sub(r"[-_ ]\d+$", "", value)
    return re.sub(r"[^a-z0-9]", "", value)


def slug(value: str) -> str:
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "untitled"


def markdown_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"^# .+\n\n", "", text, count=1)
    text = re.sub(r"^- Original:.*\n", "", text, count=1)
    text = re.sub(r"^- Conversion note:.*\n", "", text, count=1)
    text = re.sub(r"^\s*---\s*\n", "", text, count=1)
    return text.strip()


def pair_sources(files: list[Path]) -> tuple[dict[Path, Path], list[tuple[Path, Path, float]]]:
    mains = [p for p in files if not ATTACHMENT_RE.search(p.name)]
    attachments = [p for p in files if ATTACHMENT_RE.search(p.name)]
    pairs, scored = {}, []
    used: set[Path] = set()
    for attachment in attachments:
        key = norm(attachment.name)
        ranked = sorted(((SequenceMatcher(None, key, norm(main.name)).ratio(), main) for main in mains), reverse=True)
        exact = [main for main in mains if norm(main.name) == key]
        score, main = (1.0, exact[0]) if exact else ranked[0]
        if score >= .72 and main not in used:
            pairs[main] = attachment
            used.add(main)
            scored.append((main, attachment, score))
        else:
            scored.append((main, attachment, score))
    return pairs, scored


def extract_word_blocks(path: Path) -> list[dict[str, str]]:
    """Split an attachment at its labelled activity title tables."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    heads: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = LABEL_RE.match(line)
        if not match:
            continue
        label, title = clean(match.group(1)), clean(match.group(2))
        if title.casefold() == "find that foot (template)":
            # The paired schedule supplies the game's actual name; the
            # attachment contributes the printable footprint pattern.
            title = "Find the Footprint"
        kind = VALID_TYPES.get(label.casefold())
        if kind and title and title.casefold() not in {"time", "equipment"}:
            heads.append((index, label, title))
    blocks = []
    for pos, (start, label, title) in enumerate(heads):
        end = heads[pos + 1][0] if pos + 1 < len(heads) else len(lines)
        content = "\n".join(lines[start + 1:end]).strip()
        content = re.sub(r"^(?:\|\s*---[^\n]*\n)+", "", content).strip()
        # Drop the initial Markdown separator row belonging to the heading table.
        content = re.sub(r"^\|\s*:?-{3,}.*\n", "", content).strip()
        blocks.append({"label": label, "type": VALID_TYPES[label.casefold()], "name": title,
                       "content": content, "line": str(start + 1), "source": path.name})
    return blocks


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def pack_reward_adaptation(text: str) -> tuple[str, bool]:
    """Use Pinelands beans for historical POP reward counters, preserving real bones."""
    changed = False
    output = []
    equipment_index = None
    in_table = False
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            normalized = [cell.strip(" :/").casefold() for cell in cells]
            if "equipment" in normalized:
                equipment_index = normalized.index("equipment")
                in_table = True
                output.append(line)
                continue
            if in_table and equipment_index is not None and len(cells) > equipment_index:
                value = cells[equipment_index]
                adapted = re.sub(r"^(?:beans\s*/\s*)?bones?\b", "Beans", value, flags=re.I)
                if adapted != value:
                    cells[equipment_index] = adapted
                    changed = True
                for idx, cell in enumerate(cells):
                    if idx == equipment_index:
                        continue
                    original_cell = cell
                    cell = re.sub(r"\b(one\s+)?bone(?=\s+for\s+each\b|\s+for\s+every\b)", lambda m: ("one " if m.group(1) else "") + "bean", cell, flags=re.I)
                    cell = re.sub(r"\b(gets?|receives?|earns?|awarded?)\s+(?:a|one)\s+bone\b", lambda m: f"{m.group(1)} a bean", cell, flags=re.I)
                    if cell != original_cell:
                        cells[idx] = cell
                        changed = True
                line = "| " + " | ".join(cells) + " |"
            output.append(line)
            continue
        if re.search(r"\bINSPECTION:", line, re.I):
            adapted = re.sub(r"\b(?:beans\s*/\s*)?bones?\s*$", "Beans", line, flags=re.I)
            if adapted != line:
                line = adapted
                changed = True
        if in_table and line.strip():
            in_table = False
            equipment_index = None
        original = line
        line = re.sub(r"\b(one\s+)?bone(?=\s+for\s+each\b|\s+for\s+every\b)", lambda m: ("one " if m.group(1) else "") + "bean", line, flags=re.I)
        line = re.sub(r"\b(gets?|receives?|earns?|awarded?)\s+(?:a|one)\s+bone\b", lambda m: f"{m.group(1)} a bean", line, flags=re.I)
        if line != original:
            changed = True
        output.append(line)
    return "\n".join(output), changed


def pack_reward_equipment(value: str) -> tuple[str, bool]:
    adapted = re.sub(r"^(?:beans\s*/\s*)?bones?\b", "Beans", value, flags=re.I)
    return adapted, adapted != value


def relocate_assets(text: str, prefix: str) -> str:
    pattern = re.compile(r"\]\((?:<([^>]+)>|([^)]*))\)")
    def replace(match: re.Match[str]) -> str:
        target = match.group(1) or match.group(2)
        if target.startswith("assets/"):
            target = prefix + target[len("assets/"):]
            return f"](<{target}>)"
        return match.group(0)
    return pattern.sub(replace, text)


def extract_pdf_blocks(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    heads: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines):
        match = re.match(r"^\s*(Yarn|Story|Team\s+Game|Game|Activity|Handcraft|Craft|Relay\s+Game|Quiet\s+Game|Circle\s+Game)\s*:\s*(.*?)\s*$", line, re.I)
        if match and match.group(2):
            label = clean(match.group(1))
            heads.append((i, label, clean(match.group(2)), ""))
        elif re.match(r"^\s*(?:Team\s*)?$", line, re.I) and i + 1 < len(lines):
            match2 = re.match(r"^\s*(Yarn|Story|Team\s+Game|Game|Activity|Handcraft|Craft|Relay\s+Game|Quiet\s+Game|Circle\s+Game)\s*:\s*(.*?)\s*$", lines[i + 1], re.I)
            if match2 and match2.group(2):
                heads.append((i, clean(match2.group(1)), clean(match2.group(2)), ""))
    blocks = []
    for pos, (start, label, title, _) in enumerate(heads):
        end = heads[pos + 1][0] if pos + 1 < len(heads) else len(lines)
        body = "\n".join(lines[start + 1:end]).strip()
        body = re.sub(r"^\s*Game:\s*[^\n]+\n", "", body, flags=re.I)
        kind = VALID_TYPES.get(label.casefold(), "activity")
        blocks.append({"label": label, "type": kind, "name": title, "content": body,
                       "line": str(start + 1), "source": path.name})
    return blocks


def extract_levels(text: str) -> list[tuple[str, str]]:
    result = []
    for line in text.splitlines():
        cells = [clean(x.strip()) for x in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].casefold() in LEVELS and cells[1]:
            result.append((cells[0], cells[1]))
    return result


def extract_advancement_notes(text: str) -> list[tuple[str, str]]:
    notes = []
    for claim in advancement_claims(text):
        item = (claim["level"], clean(claim["source_text"]))
        if item[1] and item not in notes:
            notes.append(item)
    normalized_text = re.sub(r"##\s*Page\s+\d+", " ", text, flags=re.I)
    normalized_text = re.sub(r"\bTime\s+Min\s+Activity\s+Equipment\s+Scouter\b", " ", normalized_text, flags=re.I)
    normalized_text = clean(normalized_text)
    for claim in activity_advancement_claims(normalized_text):
        item = (claim["level"], clean(claim["source_text"]))
        if item[1] and item not in notes:
            notes.append(item)
    pattern = re.compile(r"\b(Silver|Gold)\s+Wolf\s+requirements?\s*(?:/\s*Revision)?\s*[-:–—]\s*([^.;]+)", re.I)
    for match in pattern.finditer(normalized_text):
        level = "Silver Wolf" if match.group(1).casefold() == "silver" else "Gold Wolf"
        item = (level, clean(match.group(2)))
        if item[1] and item not in notes:
            notes.append(item)
    return notes


def combine_advancement(*sources: list[tuple[str, str]]) -> list[tuple[str, str]]:
    combined = []
    for source in sources:
        for task in source:
            if task not in combined:
                combined.append(task)
    return combined


@lru_cache(maxsize=2048)
def official_matches(task: str) -> list[tuple[str, str]]:
    target = re.sub(r"[^a-z0-9]+", " ", task.casefold()).strip()
    matches = []
    for level, filename in (("Silver Wolf", "Silver-Wolf-Challenge-Badge-Requirements.md"),
                            ("Gold Wolf", "Gold-Wolf-Challenge-Badge-Requirements.md")):
        path = ROOT / "docs" / filename
        content = path.read_text(encoding="utf-8", errors="replace")
        pages = re.findall(r"^## Source page (\d+)\s*\n([\s\S]*?)(?=^## Source page \d+|\Z)", content, re.M)
        for page, body in pages:
            normalized = re.sub(r"[^a-z0-9]+", " ", body.casefold())
            if target and target in normalized:
                matches.append((level, page))
        if not matches and target:
            target_words = target.split()
            for page, body in pages:
                words = re.sub(r"[^a-z0-9]+", " ", body.casefold()).split()
                length = len(target_words)
                best = 0.0
                for window in range(max(1, length - 3), length + 5):
                    for start in range(max(0, len(words) - window + 1)):
                        candidate = " ".join(words[start:start + window])
                        best = max(best, SequenceMatcher(None, target, candidate).ratio())
                if best >= .76:
                    matches.append((level, page))
            if not matches and re.search(r"\bpurif\w* water\b", task, re.I) and level == "Gold Wolf":
                # The Gold sheet has a conditional clean-water task; the POP
                # wording omits that condition, so this remains a review lead.
                matches.append((level, "1"))
    return matches


def run_sheet_records(path: Path, text: str, programme: str) -> list[dict[str, str]]:
    records = extract_table_activities(path, text, programme, path.name.removesuffix(".md"), [])
    if not records:
        records = extract_fixed_width_activities(path, text, programme, path.name.removesuffix(".md"), [])
    return records


def schedule_title(activity: str, label: str, number: int) -> tuple[str, bool]:
    raw = re.sub(r"^[^:]{1,60}:\s*", "", activity).strip()
    quoted = re.match(r"^[\"'“‘](.+?)[\"'”’](?:\s|$)", raw)
    if quoted:
        return quoted.group(1).strip(), True
    stop = re.search(
        r"\b(?:Cubs|The Cubs|One Cub|One Six|Divide the|Have the|Stand in|Set the|Scatter|Each Cub|Each Six|First Cub|The game|This game|This can be played|Players|The Scouter|To start|To play|The first player|A Leader|The Sixers|The cannon|The Pirate|The playing|Pack in|Cubs to|The Cub|All Cubs|The Pack|The leader|The Explorers|The Captain|Buy|Mark|Make|Tie|Draw|Place|Set up|Line up|Preparation|For this game|Using|When the|When Cubs|The whole Pack|The whole pack|Three stations|Play in|Two Scouters|Two Leaders|Explain|Chalk|Sixes are|Sixes line|Sixes|In Sixes|Half the Pack|Cut out|In relay formation|In the relay|Footprints in|Lay a rope|Best played|Choose|Slips of paper|Before commencing|Split the|Fold|Look at|At go|10 minutes for explanation)\b",
        raw, re.I,
    )
    title = raw[:stop.start()].strip(" :.,-–—\"'“”‘’") if stop and stop.start() else ""
    if not title:
        title = raw.split(".", 1)[0].strip(" :.,-–—\"'“”‘’")[:70]
    is_confident = bool(title and len(title.split()) <= 8 and len(title) < 65 and not re.match(r"^(?:the|a|an) cubs?\b", title, re.I))
    return (title if is_confident else f"{label.title()} item {number}"), is_confident


def block_equipment(content: str) -> str:
    lines = content.splitlines()
    for i, line in enumerate(lines):
        match = re.match(r"^\s*(?:#{1,6}\s*)?(?:equipment|materials|what you(?:'|’)ll need|you will need)\s*:\s*(.*)$", line, re.I)
        if not match:
            continue
        if match.group(1).strip():
            return clean(match.group(1))
        values = []
        for following in lines[i + 1:]:
            if re.match(r"^\s*(?:#{1,6}\s*)?(?:procedure|instructions|how to|steps|gameplay)\s*:?", following, re.I):
                break
            if re.match(r"^\s*(?:Trace|Draw|Write|Hold|Use|Put|Make|Cubs?\b|The Cubs\b|First Cub|Fold|Colour|Color|Stick|Decorate|Glue\s+(?:it|the|a|both)|Tape\s+(?:it|the|a|both)|Cut\s+(?:it|the|a|both)|Tie\s+(?:it|the|a|both)|Roll\s+(?:it|the|a|both)|Please\s+don.t)\b", following, re.I):
                break
            if "![" in following:
                continue
            if following.strip():
                values.append(following.strip())
        if values:
            return clean("; ".join(values))
    return "Not stated in this attachment."


def semantic_tags(name: str, content: str, kind: str, programme: str = "") -> list[str]:
    haystack = f"{name} {programme} {content}".casefold()
    title_and_theme = f"{name} {programme}".casefold()
    tags = [kind]
    for tag, words in KEYWORDS.items():
        search_text = title_and_theme if tag == "space" else haystack
        if any(re.search(rf"\b{re.escape(word)}\b", search_text) for word in words):
            tags.append(tag)
    return list(dict.fromkeys(tags))


def unique_target(folder: Path, base: str) -> Path:
    candidate = folder / f"{base}.md"
    suffix = 2
    while True:
        key = str(candidate).casefold()
        existing = candidate.read_text(encoding="utf-8", errors="replace") if candidate.exists() else ""
        generated = "## Source" in existing and ("- [Converted source document]" in existing or "- [Converted attachment]" in existing)
        if key not in ALLOCATED_TARGETS and (not candidate.exists() or generated):
            ALLOCATED_TARGETS.add(key)
            return candidate
        candidate = folder / f"{base}-variant-{suffix}.md"
        suffix += 1


def element_document(block: dict[str, str], programme: str, tasks: list[tuple[str, str]],
                     programme_context: list[tuple[str, str]]) -> tuple[Path, str]:
    kind, name, content = block["type"], block["name"], block["content"].strip()
    folder = FOLDERS[kind]
    folder.mkdir(parents=True, exist_ok=True)
    target = unique_target(folder, slug(name))
    source_archive = f"../pop/source-conversions/{block['source']}"
    equipment, equipment_changed = pack_reward_equipment(block.get("equipment") or block_equipment(content))
    content, content_changed = pack_reward_adaptation(content)
    tasks_with_adaptation = [(rank, *pack_reward_adaptation(task)) for rank, task in tasks]
    context_with_adaptation = [(rank, *pack_reward_adaptation(task)) for rank, task in programme_context]
    reward_changed = equipment_changed or content_changed or any(changed for _, _, changed in tasks_with_adaptation + context_with_adaptation)
    tasks = [(rank, task) for rank, task, _ in tasks_with_adaptation]
    programme_context = [(rank, task) for rank, task, _ in context_with_adaptation]
    content = relocate_assets(content, "../pop/source-conversions/assets/")
    lines = [f"# {name}", "", f"## Type", "", block["label"], "", "## Equipment", "", equipment, "", "## Instructions", "",
             content if content else "The source contains a title for this item but no readable instructions; inspect the source.",
             "", "## Advancement covered / badge link", ""]
    if block.get("title_uncertain"):
        position = lines.index("## Advancement covered / badge link")
        lines.insert(position, "**Review:** the run sheet does not clearly separate an activity title from its instructions; the heading was inferred. Confirm the name before reuse.\n")
    if reward_changed:
        position = lines.index("## Advancement covered / badge link")
        lines.insert(position, "**1st Pinelands reward adaptation:** use beans where this POP source uses bones as reward counters. References to actual bones remain unchanged.\n")
    if tasks:
        for _rank, task in tasks:
            task = relocate_assets(task, "../pop/source-conversions/assets/")
            matches = official_matches(task)
            if matches:
                lines.append(f"- Historical source task: {task}")
                for level, page in matches:
                    file = f"../{level.replace(' ', '-')}-Challenge-Badge-Requirements.md#source-page-{page}"
                    caveat = " The POP wording does not state the Gold requirement’s clean-water-availability condition." if level == "Gold Wolf" and re.search(r"\bpurif\w* water\b", task, re.I) else ""
                    lines.append(f"  - Possible {level} wording match: [source page {page}]({file}). Verify the complete requirement and that this activity provides suitable evidence.{caveat}")
            else:
                lines.append("- Historical source task; no current Silver Wolf or Gold Wolf match is verified. Review the source before use.")
    else:
        lines.append("No activity-specific advancement task was identified in this attachment. Check the programme-level notes; no badge completion is implied.")
    context_only = []
    lines.extend(["", "## Visual aid / image reference", ""])
    image_text = content + "\n" + "\n".join(relocate_assets(task, "../pop/source-conversions/assets/") for _, task in tasks + context_only)
    images = re.findall(r"!\[[^\]]*\]\((?:<([^>]+)>|([^)]*))\)", image_text)
    images = [a or b for a, b in images]
    if images:
        lines.extend(["Embedded source visuals are retained below:", ""])
        for image in images:
            lines.append(f"![Source image](<{image}>)")
    elif block["source"].endswith(".pdf.md"):
        stem = block["source"]
        pages = sorted((ARCHIVE / "assets" / stem).glob("page-*.png"))
        if pages:
            for page in pages:
                relative = f"../pop/source-conversions/assets/{stem}/{page.name}"
                lines.append(f"![Original source page](<{relative}>)")
        else:
            lines.append(f"Review the original PDF page images in [the converted source document](<{source_archive}>).")
    else:
        lines.append("No embedded visual was found in this extracted section. Review the original source if the activity refers to a layout or template.")
    lines.extend(["", "## Tags", "", " ".join(f"#{tag}" for tag in semantic_tags(name, content, kind, programme)), "", "## Source", "",
                  f"- [Converted source document](<{source_archive}>)", f"- Original file: [`{block['source'].removesuffix('.md')}`](<../pop/src/{block['source'].removesuffix('.md')}>)"])
    if block.get("related_source"):
        related = block["related_source"]
        lines.append(f"- Related programme schedule: [`{related.removesuffix('.md')}`](<../pop/source-conversions/{related}>)")
    lines.append("")
    document = "\n".join(lines)
    target.write_text(document, encoding="utf-8")
    return target, document


def main() -> int:
    files = sorted(ARCHIVE.glob("*.md"))
    files = [p for p in files if p.name != "conversion-errors.json"]
    pairs, scored = pair_sources(files)
    mains = [p for p in files if not ATTACHMENT_RE.search(p.name)]
    PROGRAMMES.mkdir(parents=True, exist_ok=True)
    index = ["# POP Programme Draft Index", "", "First-pass reconstructions pair programme documents with matching attachments. Source wording and visuals are retained; uncertain mappings, advancement links and incomplete source instructions need Scouter review.", ""]
    element_links: dict[Path, list[Path]] = {}
    element_paths: set[Path] = set()
    item_total = 0
    review_rows = []
    for attachment in [p for p in files if ATTACHMENT_RE.search(p.name)]:
        pair = next(((main, score) for main, candidate, score in scored if candidate == attachment and main in pairs), None)
        if not pair:
            continue
        main, confidence = pair
        programme = re.sub(r"[_-]+", " ", main.name.rsplit(".", 2)[0]).strip()
        attachment_text = markdown_body(attachment)
        main_text = markdown_body(main)
        task_rows = extract_levels(attachment_text)
        combined_source = attachment_text + "\n" + main_text
        programme_context = combine_advancement(extract_levels(combined_source), extract_advancement_notes(combined_source))
        # Split detailed instructions at the attachment's explicit headings.
        blocks = extract_pdf_blocks(attachment) if attachment.name.endswith(".pdf.md") else extract_word_blocks(attachment)
        schedule_records = run_sheet_records(main, main_text, programme)
        matched_schedule: set[int] = set()
        made = []
        for block in blocks:
            # Include the adjacent legacy task row(s) in a work-session element.
            block["source"] = attachment.name
            block["related_source"] = main.name
            block["equipment"] = block_equipment(block["content"])
            block_key = norm(block["name"])
            for idx, record in enumerate(schedule_records):
                activity_key = norm(record["activity_text"])
                if block_key and (block_key in activity_key or SequenceMatcher(None, block_key, activity_key).ratio() >= .70):
                    matched_schedule.add(idx)
                    if record.get("equipment") and block["equipment"].casefold() in {"not stated in this attachment.", "see instructions", "see attachment", "refer to attachment"}:
                        block["equipment"] = record["equipment"]
                    schedule_instruction = clean(record["activity_text"])
                    if schedule_instruction and schedule_instruction.casefold() not in block["content"].casefold():
                        block["content"] = (block["content"].rstrip() + "\n\n**Programme run-sheet instructions:**\n\n" + schedule_instruction).strip()
                    break
            local_tasks = combine_advancement(extract_levels(block["content"]), extract_advancement_notes(block["content"]))
            target, _ = element_document(block, programme, local_tasks, programme_context)
            made.append(target)
            element_paths.add(target)
        for number, record in enumerate(schedule_records, 1):
            if number - 1 in matched_schedule:
                continue
            categories = record.get("categories", [])
            label = record.get("source_activity_label", "Activity").strip() or "Activity"
            if "ceremony_or_pack_routine" in categories:
                continue
            if not (set(categories) & {"game", "yarn", "craft", "sense_training", "skill_practice", "singing", "playacting"}) and not re.search(r"activity|work session|inspection|first aid|trail", label, re.I):
                continue
            kind = ("yarn" if "yarn" in categories else "craft" if "craft" in categories else
                    "game" if "game" in categories else "activity")
            title, confident = schedule_title(record["activity_text"], label, number)
            instructions = clean(record["activity_text"])
            if record.get("detail_status", "").endswith("only") or len(instructions) < 35:
                instructions += "\n\nThe run sheet gives only a title or reference here; inspect the original and attachment for complete instructions."
            block = {"label": label, "type": kind, "name": title, "content": instructions,
                     "line": str(record.get("source_markdown_line", "")), "source": main.name,
                     "equipment": record.get("equipment") or "Not stated in source.", "title_uncertain": not confident}
            local_tasks = combine_advancement(extract_levels(instructions), extract_advancement_notes(instructions))
            target, _ = element_document(block, programme, local_tasks, programme_context)
            made.append(target)
            element_paths.add(target)
        made = list(dict.fromkeys(made))
        element_links[main] = made
        out = PROGRAMMES / f"{slug(programme)}.md"
        confidence_note = "Name match" if confidence >= .95 else f"Probable name match ({confidence:.0%}); verify the pairing"
        main_output, main_reward_change = pack_reward_adaptation(relocate_assets(main_text, "../source-conversions/assets/"))
        attachment_output, attachment_reward_change = pack_reward_adaptation(relocate_assets(attachment_text, "../source-conversions/assets/"))
        lines = [f"# {programme}", "", "## Source files", "",
                 f"- Programme: [`{main.name.removesuffix('.md')}`](<../src/{main.name.removesuffix('.md')}>)",
                 f"- Attachment: [`{attachment.name.removesuffix('.md')}`](<../src/{attachment.name.removesuffix('.md')}>)",
                 f"- Pairing: {confidence_note}.", "", "## Programme run sheet", "",
                 main_output, "", "## Attachment instructions and source material", "",
                 attachment_output, "", "## Extracted elements", ""]
        if main_reward_change or attachment_reward_change:
            position = lines.index("## Programme run sheet")
            lines[position:position] = ["## 1st Pinelands reward practice", "",
                "The POP source uses bones as reward counters in this programme. At 1st Pinelands, use beans as rewards throughout the meeting. This adaptation changes reward counters only; references to actual bones as activity objects remain unchanged.", ""]
        if made:
            for path in made:
                relative = Path("..") / ".." / path.relative_to(ROOT / "docs")
                lines.append(f"- [{path.stem}]({relative.as_posix()})")
        else:
            lines.append("No labelled standalone activity section was detected automatically; the complete attachment text is retained above for review.")
        lines.extend(["", "## Review notes", "",
                      "- This is a first-pass reconstruction from historical POP material. Check that the schedule and attachment instructions correspond before running.",
                      "- Inspect every source visual and confirm the page/layout is understandable in the rendered programme.",
                      "- Historical Caracal, Cheetah, Leopard and Lion task labels are retained as source wording. Any official sheet wording match is only a candidate for review; confirm the full current requirement.",
                      "- Where the source says only ‘See instructions’, a module page, or gives incomplete steps, confirm the extracted attachment supplies the missing details.", ""])
        out.write_text("\n".join(lines), encoding="utf-8")
        review_rows.append((programme, out, main, attachment, confidence, len(made)))
        index.append(f"- [{programme}](programmes/{out.name}) — {len(made)} standalone elements; {confidence_note.lower()}.")
    # Draft records for main documents with no paired attachment retain their
    # complete programme text and identify the missing attachment explicitly.
    paired_mains = set(pairs)
    for main in mains:
        if main in paired_mains:
            continue
        programme = re.sub(r"[_-]+", " ", main.name.rsplit(".", 2)[0]).strip()
        out = PROGRAMMES / f"{slug(programme)}.md"
        text, reward_change = pack_reward_adaptation(relocate_assets(markdown_body(main), "../source-conversions/assets/"))
        schedule_records = run_sheet_records(main, markdown_body(main), programme)
        programme_context = combine_advancement(extract_levels(markdown_body(main)), extract_advancement_notes(markdown_body(main)))
        made = []
        for number, record in enumerate(schedule_records, 1):
            categories = record.get("categories", [])
            label = record.get("source_activity_label", "Activity").strip() or "Activity"
            if "ceremony_or_pack_routine" in categories:
                continue
            if not (set(categories) & {"game", "yarn", "craft", "sense_training", "skill_practice", "singing", "playacting"}) and not re.search(r"activity|work session|inspection|first aid|trail", label, re.I):
                continue
            kind = ("yarn" if "yarn" in categories else "craft" if "craft" in categories else "game" if "game" in categories else "activity")
            title, confident = schedule_title(record["activity_text"], label, number)
            instructions = clean(record["activity_text"])
            if record.get("detail_status", "").endswith("only") or len(instructions) < 35:
                instructions += "\n\nThe run sheet gives only a title or reference here; inspect the original for complete instructions."
            block = {"label": label, "type": kind, "name": title, "content": instructions,
                     "line": str(record.get("source_markdown_line", "")), "source": main.name,
                     "equipment": record.get("equipment") or "Not stated in source.", "title_uncertain": not confident}
            local_tasks = combine_advancement(extract_levels(instructions), extract_advancement_notes(instructions))
            target, _ = element_document(block, programme, local_tasks, programme_context)
            made.append(target)
            element_paths.add(target)
        made = list(dict.fromkeys(made))
        lines = [f"# {programme}", "", "## Source files", "",
                 f"- Programme: [`{main.name.removesuffix('.md')}`](<../src/{main.name.removesuffix('.md')}>)",
                 "- No matching attachment was identified in the retained source set.", "", "## Programme run sheet", "", text,
                 "", "## Extracted elements", ""]
        if reward_change:
            position = lines.index("## Programme run sheet")
            lines[position:position] = ["## 1st Pinelands reward practice", "",
                "The POP source uses bones as reward counters in this programme. At 1st Pinelands, use beans as rewards throughout the meeting. This adaptation changes reward counters only; references to actual bones as activity objects remain unchanged.", ""]
        if made:
            for path in made:
                relative = Path("..") / ".." / path.relative_to(ROOT / "docs")
                lines.append(f"- [{path.stem}]({relative.as_posix()})")
        else:
            lines.append("No labelled activity entries were detected automatically.")
        lines.extend(["", "## Review notes", "",
                      "- Confirm whether a separate attachment exists; the retained source set did not contain a confident filename match.",
                      "- Inspect source visuals, advancement notes and any incomplete instructions before use.", ""])
        out.write_text("\n".join(lines), encoding="utf-8")
        index.append(f"- [{programme}](programmes/{out.name}) — no confident attachment match.")
    # Remove only our own unreferenced generated artifacts; programme links
    # remain the source of truth and hand-authored files are retained.
    for folder in FOLDERS.values():
        for candidate in folder.glob("*.md"):
            if candidate.name == "POP-EXTRACTED-INDEX.md":
                continue
            if candidate in element_paths:
                continue
            previous = candidate.read_text(encoding="utf-8", errors="replace")
            if "## Source" in previous and ("Converted attachment" in previous or "Converted source document" in previous):
                candidate.unlink()
    item_total = len(element_paths)
    for folder in FOLDERS.values():
        items = sorted((p for p in element_paths if p.parent == folder), key=lambda p: p.name.casefold())
        if not items:
            continue
        listing = [f"# POP Extracted {folder.name.title()} Index", "", f"{len(items)} first-pass elements extracted from historical POP sources. Check each source and safety before reuse.", ""]
        for item in items:
            title = re.search(r"^#\s+(.+)$", item.read_text(encoding="utf-8", errors="replace"), re.M)
            tags = re.search(r"^## Tags\s*\n+([^\n]+)", item.read_text(encoding="utf-8", errors="replace"), re.M)
            listing.append(f"- [{title.group(1) if title else item.stem}]({item.name})" + (f" — {tags.group(1)}" if tags else ""))
        (folder / "POP-EXTRACTED-INDEX.md").write_text("\n".join(listing) + "\n", encoding="utf-8")
    index.extend(["", f"Generated {len(review_rows) + len(mains) - len(paired_mains)} programme drafts and {item_total} unique labelled standalone elements.", ""])
    (ROOT / "docs" / "pop" / "PROGRAMME-DRAFT-INDEX.md").write_text("\n".join(index), encoding="utf-8")
    print(f"Programme drafts: {len(review_rows) + len(mains) - len(paired_mains)}")
    print(f"Paired attachments: {len(review_rows)} / {len([p for p in files if ATTACHMENT_RE.search(p.name)])}")
    print(f"Standalone labelled elements: {item_total}")
    print(f"Output index: docs/pop/PROGRAMME-DRAFT-INDEX.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
