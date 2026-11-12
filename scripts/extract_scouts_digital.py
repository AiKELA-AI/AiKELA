#!/usr/bin/env python3
"""Scan source activity tables without inventing rules or importing transitions.

Scan data is a review intermediate, not an approved activity catalogue. PDF
tables use PyMuPDF; DOCX/XLSX use XML; legacy DOC uses its archived tab text.
The scan records source locations and possible existing-library matches.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/scouts-digital'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
ROUTINE = re.compile(r'^(?:grand\s*howl|opening\b|closing\b|flag\s*(?:down|break|ceremony)|notices\b|announcements?\b|badges?\b|inspection\b|water\s*break|juice\b|refreshments?\b|snack\b|dismiss\b|tidy\b|clean\s*up|pack\s*(?:up|away|dismissed|ceremony)|set\s*up\s*for\s*closing|arriv|register\b|attendance\b|prayer\b|duty\s*six|collection\s*of\s*(?:bones|beans)|investiture\b|break\b|points\b|prepare\s*flag|thank\s*you|leaping\s*wolf\s*celebration|membership\b|new\s*chums\b)', re.I)
LABEL = re.compile(r'\b(?:game|relay|race|steam.?release|activity|advancement|work.?session|handcraft|craft|yarn|story|singing|song|play.?acting|base|instruction|station|knot|kim|compass|trail|experiment|challenge|silver|gold|sw\b|gw\b)\b', re.I)
THEMES = {
    'knots': r'\bknot|\bhank|\brope', 'maps-and-compass': r'\bmap|\bcompass|\bnorth|\bdirection',
    'water-safety': r'water safety|\bswim|\brescue|\bdrown', 'first-aid': r'first.?aid|\bbandage|\bsling|\bbleed|\bburn',
    'nature': r'\bnature|\bplant|\bleaves|\bseeds|\bgarden|\binsect|\bcompost', 'birds': r'\bbird|\bfeather|\bowl',
    'animals': r'\banimal|\bwildlife|\bsilkworm', 'memory': r'\bmemory|\bremember|\bkim.?s',
    'sense-training': r'sense.?training|\btaste|\bsmell|\blisten|\bblindfold', 'codes': r'\bcode|\bcipher|\bcypher|secret message',
    'fire': r'\bfire|\bmatch|\bcandle|\bstove', 'food': r'\bfood|\bcook|\bsweet|\brecipe|\bpeanut|\bmeal',
    'teamwork': r'\bteam|\bcooperat|\brelay', 'movement': r'\brun|\bhop|\bjump|\bchase|\btag\b',
    'culture': r'\bcultur|\btraditional|\blanguage', 'time': r'\bclock|\b24.hour', 'flag': r'\bflag',
    'camp': r'\bcamp|\btent|\bshelter', 'environment': r'\bconserv|\bpollution|\blitter|\brecycl',
    'jungle-book': r'jungle book|mowgli|bagheera|baloo|shere khan', 'space': r'\bspace|\bplanet|\bmoon|\brocket',
}


def clean(value):
    value = (value or '').encode('utf-16', errors='surrogatepass').decode('utf-16', errors='replace')
    return re.sub(r'[ \t]+', ' ', value.replace('\u200b', '').replace('\xa0', ' ')).strip()


def norm(value):
    return re.sub(r'[^a-z0-9]+', ' ', value.casefold()).strip()


def table_columns(row):
    values = [norm(value or '').replace(' ', '') for value in row]
    activity = next((i for i, value in enumerate(values) if value in {'activity', 'activities', 'activityandvenue', 'activityvenue', 'activitydescription', 'descriptiondetails', 'descriptionanddetails'}), None)
    time = next((i for i, value in enumerate(values) if value in {'time', 'times', 'themetime'}), None)
    equipment = next((i for i, value in enumerate(values) if value in {'equipment', 'materials', 'material', 'itemsneeded'}), None)
    minutes = next((i for i, value in enumerate(values) if value in {'min', 'mins', 'minutes', 'duration', 'dur'}), None)
    notes = next((i for i, value in enumerate(values) if value in {'notes', 'instructions', 'details'}), None)
    if activity is None and time is not None and minutes is not None and equipment is not None and minutes + 1 < equipment:
        activity = next((i for i in range(minutes + 1, equipment) if values[i] and values[i] != values[minutes]), minutes + 1)
    if activity is None or time is None:
        return None
    return {'activity': activity, 'time': time, 'equipment': equipment, 'minutes': minutes, 'notes': notes, 'width': len(row)}


def consume_rows(tables):
    current = None
    mapping = None
    records = []
    excluded = []
    for location, rows in tables:
        for number, row in enumerate(rows, 1):
            row_location = f'{location}, row {number}'
            found = table_columns(row)
            if found:
                mapping = found
                continue
            if mapping is None or len(row) != mapping['width']:
                continue
            values = [clean(value) for value in row]
            nonempty = [value for value in values if value]
            activity = values[mapping['activity']]
            if activity and mapping.get('notes') is not None and values[mapping['notes']]:
                activity += '\n' + values[mapping['notes']]
            # Merged spacer rows contain the narrative transition in one column
            # or repeat it across every column. They are kept only in the source.
            if not activity or (len(nonempty) > 1 and len(set(nonempty)) == 1):
                if nonempty:
                    excluded.append({'location': row_location, 'reason': 'merged transition/source-only row', 'text': nonempty[0][:160]})
                continue
            time = values[mapping['time']]
            equipment = values[mapping['equipment']] if mapping['equipment'] is not None else ''
            if equipment == activity:
                equipment = ''
            minutes = values[mapping['minutes']] if mapping['minutes'] is not None else ''
            valid_time = bool(re.search(r'\b\d{1,2}\s*[:h.\-]\s*\d\s*\d', time) or re.fullmatch(r'\d{1,3}(?:\.\d+)?', time))
            valid_minutes = bool(re.fullmatch(r'\(?\s*\d+(?:\s*[-–]\s*\d+)?\s*(?:min|minutes|mins|m|:00)?\s*\)?', minutes, re.I))
            if time and not valid_time and not valid_minutes:
                excluded.append({'location': row_location, 'reason': 'non-timetable/appendix row; source-only', 'text': activity[:160]})
                continue
            if not time and not minutes and current is None:
                excluded.append({'location': row_location, 'reason': 'untimed source note or appendix; not a scheduled element', 'text': activity[:160]})
                continue
            if ROUTINE.match(activity):
                excluded.append({'location': row_location, 'reason': 'Pack routine/source-only', 'text': activity[:160]})
                current = None
                if re.match(r'closing\b|pack\s*(?:dismissed|ceremony)|flag\s*down', activity, re.I):
                    mapping = None
                continue
            if not time and not minutes and not LABEL.search(activity[:160]) and len(nonempty) == 1:
                # A solitary sentence in the activity column may be a transition;
                # only append obvious lower-case/numbered continuation fragments.
                if current and re.match(r'^(?:[a-z]|\d+[.)]|[•●○])', activity):
                    current['activity'] += '\n' + activity
                    current['locations'].append(row_location)
                else:
                    excluded.append({'location': row_location, 'reason': 'untimed note; retained in programme for review', 'text': activity[:160]})
                continue
            if not time and not minutes and current and not re.match(r'^(?:Silver|Gold|SW\b|GW\b|Base\b|Game\b|Activity\b|Yarn\b|Craft\b|Instruction\b)', activity, re.I):
                current['activity'] += '\n' + activity
                if equipment:
                    current['equipment'] = (current['equipment'] + '\n' + equipment).strip()
                current['locations'].append(row_location)
                continue
            if norm(activity) in {'time activity equipment scouter', 'activity', 'min'}:
                continue
            current = {'activity': activity, 'equipment': equipment, 'time': time, 'minutes': minutes, 'locations': [row_location]}
            records.append(current)
    return records, excluded


def word_tables(original):
    with zipfile.ZipFile(original) as archive:
        root = ET.fromstring(archive.read('word/document.xml'))
        tables = []
        for number, table in enumerate(root.findall('.//' + W + 'tbl'), 1):
            rows = []
            for row in table.findall(W + 'tr'):
                before = row.find(W + 'trPr/' + W + 'gridBefore')
                values = [''] * (int(before.get(W + 'val')) if before is not None else 0)
                for cell in row.findall(W + 'tc'):
                    value = '\n'.join(''.join(t.text or '' for t in p.iter(W + 't')) for p in cell.findall('.//' + W + 'p'))
                    span = cell.find(W + 'tcPr/' + W + 'gridSpan')
                    values.extend([value] * (int(span.get(W + 'val')) if span is not None else 1))
                rows.append(values)
            width = max(map(len, rows), default=0)
            rows = [row + [''] * (width - len(row)) for row in rows]
            tables.append((f'Word table {number}', rows))
        text = '\n'.join(''.join(t.text or '' for t in p.iter(W + 't')) for p in root.iter(W + 'p'))
        return tables, text


def spreadsheet_tables(original):
    from import_scouts_digital import convert_xlsx
    namespace = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(original) as archive:
        strings = [''.join(node.itertext()) for node in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', namespace)] if 'xl/sharedStrings.xml' in archive.namelist() else []
        tables = []
        for name in sorted(archive.namelist()):
            if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml', name):
                continue
            rows = []
            for row in ET.fromstring(archive.read(name)).findall('.//s:sheetData/s:row', namespace):
                values = {}
                for cell in row.findall('s:c', namespace):
                    letters = re.match(r'[A-Z]+', cell.get('r')).group()
                    column = 0
                    for char in letters:
                        column = column * 26 + ord(char) - 64
                    v = cell.find('s:v', namespace)
                    value = (v.text or '') if v is not None else ''
                    if cell.get('t') == 's' and value:
                        value = strings[int(value)]
                    elif cell.get('t') == 'inlineStr':
                        value = ''.join(cell.find('s:is', namespace).itertext())
                    values[column - 1] = value
                width = max(values, default=-1) + 1
                rows.append([values.get(i, '') for i in range(max(5, width))])
            width = max(map(len, rows), default=5)
            tables.append((f'Worksheet {Path(name).stem}', [row + [''] * (width - len(row)) for row in rows]))
        return tables, '\n'.join(value for _, rows in tables for row in rows for value in row)


def pdf_fallback(page):
    """Read a clearly labelled timetable by column rectangles and time anchors."""
    words = page.get_text('words')
    headers = [word for word in words if word[4].casefold() == 'time']
    for time_word in headers:
        line = sorted((word for word in words if abs(word[1] - time_word[1]) < 6), key=lambda w: w[0])
        activity_word = next((word for word in line if re.match(r'activity|description', word[4], re.I)), None)
        if not activity_word:
            continue
        equipment_word = next((word for word in line if word[4].casefold() in {'equipment', 'materials'}), None)
        leader_word = next((word for word in line if word[4].casefold() in {'scouter', 'runner', 'leader', 'who', 'person'}), None)
        notes_word = next((word for word in line if word[4].casefold() == 'notes'), None)
        end = min([word[0] for word in (equipment_word, leader_word) if word and word[0] > activity_word[0]] or [page.rect.width - 20])
        anchors = sorted((word for word in words if word[1] > time_word[1] + 5 and word[0] < activity_word[0] and re.fullmatch(r'\d{1,2}[:h.]\d{2}', word[4])), key=lambda w: w[1])
        if not anchors:
            continue
        rows = [['Time', 'Activity', 'Equipment', 'Notes']]
        for index, anchor in enumerate(anchors):
            bottom = anchors[index + 1][1] - 1 if index + 1 < len(anchors) else min(anchor[1] + 45, page.rect.height - 15)
            rect = (activity_word[0] - 4, anchor[1] - 1, end - 2, bottom)
            activity = page.get_text(clip=rect, sort=True).strip()
            equipment_end = notes_word[0] - 2 if notes_word else leader_word[0] - 2 if leader_word and leader_word[0] > end else page.rect.width - 15
            equipment = page.get_text(clip=(end, anchor[1] - 1, equipment_end, bottom), sort=True).strip() if equipment_word else ''
            notes = page.get_text(clip=(notes_word[0] - 1, anchor[1] - 1, page.rect.width - 15, bottom), sort=True).strip() if notes_word else ''
            rows.append([anchor[4], activity, equipment, notes])
        return rows
    return []


def pdf_tables(original, appendices=None):
    import pymupdf
    tables = []
    texts = []
    positions = None
    with pymupdf.open(original) as document:
        for number, page in enumerate(document, 1):
            before = len(tables)
            texts.append(page.get_text(sort=True))
            found = page.find_tables().tables
            if found:
                for index, table in enumerate(found, 1):
                    raw = table.extract()
                    if appendices is not None and raw and any(re.match(r'Game\s*/?\s*Activity\s*:', clean(cell or ''), re.I) for cell in raw[0]):
                        label = next(clean(cell) for cell in raw[0] if re.match(r'Game\s*/?\s*Activity\s*:', clean(cell or ''), re.I))
                        instructions = []
                        for row in raw[1:]:
                            for cell in row:
                                value = clean(cell)
                                if value and value not in instructions:
                                    instructions.append(value)
                        appendices.append({'title': label, 'text': '\n'.join(instructions), 'location': f'PDF p. {number}, detailed game/attachment table {index}'})
                        continue
                    own_header = None
                    for row_index, row in enumerate(raw):
                        header = table_columns(row)
                        if header:
                            positions = {key: (table.rows[row_index].cells[column][0] + table.rows[row_index].cells[column][2]) / 2 for key, column in header.items() if key != 'width' and column is not None and table.rows[row_index].cells[column] is not None}
                            own_header = row_index
                            break
                    if positions and (own_header is not None or table.col_count >= 3):
                        normalized = [['Time', 'Min', 'Activity', 'Equipment', 'Notes']] if own_header is not None or not tables else []
                        for row_index, row in enumerate(raw):
                            if own_header is not None and row_index <= own_header:
                                continue
                            cells = table.rows[row_index].cells
                            values = []
                            for key in ['time', 'minutes', 'activity', 'equipment', 'notes']:
                                x = positions.get(key)
                                value = ''
                                if x is not None:
                                    for column, rect in enumerate(cells):
                                        if rect and rect[0] <= x <= rect[2]:
                                            value = row[column] or ''
                                            break
                                values.append(value)
                            normalized.append(values)
                            if re.match(r'closing\b|pack\s*(?:dismissed|ceremony)|flag\s*down', values[2], re.I):
                                positions = None
                                break
                        tables.append((f'PDF p. {number}, table {index}', normalized))
            if len(tables) == before:
                fallback = pdf_fallback(page)
                if fallback:
                    tables.append((f'PDF p. {number}, rectangular timetable fallback — check against visual', fallback))
    if not tables:
        # Some programmes use timed headings rather than a table.
        full = '\n'.join(texts)
        sections = list(re.finditer(r'(?m)^(\d{1,2}[:h.]\d{2})\s*[-–]\s*\d{1,2}[:h.]\d{2}\s*\|\s*(.+)$', full))
        if sections:
            rows = [['Time', 'Activity', 'Equipment']]
            for index, match in enumerate(sections):
                end = sections[index + 1].start() if index + 1 < len(sections) else full.find('EQUIPMENT / PACKING LIST', match.end())
                if end < 0:
                    end = len(full)
                rows.append([match.group(1), match.group(2) + '\n' + full[match.end():end].strip(), 'See source packing list'])
            tables.append(('Timed source headings; source packing list retained separately', rows))
    return tables, '\n'.join(texts)


def doc_tables(original, conversion):
    text = conversion.read_text(encoding='utf-8').split('```text\n', 1)[-1].rsplit('```', 1)[0]
    chunks = re.split(r'\t{2,}', text)
    width = 5 if 'MIN\t' in text[:400] else 3
    rows = [['Time', 'Min', 'Activity', 'Equipment', 'Scouter']] if width == 5 else [['Time', 'Activity', 'Leader / equip']]
    for chunk in chunks:
        cells = chunk.strip().split('\t')
        if len(cells) >= 3 and re.search(r'\b\d{1,2}[:h.]\d{2}\b', cells[0]):
            rows.append(cells[:width] + [''] * max(0, width - len(cells)))
        elif width == 5 and len(cells) >= 3 and re.fullmatch(r'\s*\d+\s*min(?:s)?\s*', cells[1], re.I):
            rows.append(cells[:width] + [''] * max(0, width - len(cells)))
    return [('Legacy Word tab-text table — original layout must be checked', rows)], text


def get_title(text, original):
    patterns = [r'(?im)^\s*(?:theme|name)\s*[:：]\s*([^\n]{3,130})', r'(?im)^\s*Theme\s+([^\n]{3,100})']
    for pattern in patterns:
        match = re.search(pattern, text[:4500])
        if match:
            return clean(match.group(1))
    return original.stem


def classify(activity):
    head = activity.split('\n')[0]
    if re.search(r'\b(?:yarn|story)\s*[:–—-]', head, re.I) or re.match(r'^Yarn\b', head, re.I):
        return 'yarns'
    if re.search(r'\b(?:craft|handcraft|make a? ?(?:mask|bird.?feeder|paper|pot|bookmark))\b', head, re.I):
        return 'crafts'
    if re.search(r'\b(?:game|relay|race|steam.?release)\b', head, re.I):
        return 'games'
    return 'activities'


def entry_title(activity):
    lines = [clean(line).strip('•●- ') for line in activity.splitlines() if clean(line)]
    head = lines[0]
    if re.fullmatch(r'(?:Advancement|Silver\s*Wol(?:f|ves)|Gold\s*Wol(?:f|ves)|SW|GW|Game|Activity|Steam Release|Instruction)[: ]*', head, re.I) and len(lines) > 1:
        head += ' — ' + lines[1]
    head = re.sub(r'\s+(?:Cubs|The Cubs|Divide|Players|Each Cub)\b.*', '', head, flags=re.I)
    return head[:140].strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.tools/scouts-digital-scan.json')
    args = parser.parse_args()
    reviewed = (BASE / 'PROGRAMMES-INDEX.md').read_text(encoding='utf-8') + (BASE / 'INITIAL-BATCH-COVERAGE.md').read_text(encoding='utf-8')
    reviewed_names = set(re.findall(r'Program_Doc_ID_\d+_\d+_\d{4}-\d{2}-\d{2}\.(?:pdf|docx|doc)', reviewed))
    existing = []
    for folder in ['games', 'activities', 'crafts', 'yarns']:
        for path in (ROOT / 'docs' / folder).glob('*.md'):
            if 'INDEX' in path.name or path.name.startswith('sd-'):
                continue
            content = path.read_text(encoding='utf-8')
            title = re.search(r'^# (.+)', content)
            if title:
                existing.append((norm(title.group(1)), path.relative_to(ROOT / 'docs').as_posix()))
    documents = []
    seen = {}
    for original in sorted((BASE / 'src').rglob('*')):
        if not original.is_file() or original.suffix.lower() not in {'.pdf', '.docx', '.doc', '.xlsx'}:
            continue
        digest = hashlib.sha256(original.read_bytes()).hexdigest()
        if original.name in reviewed_names:
            seen[digest] = original.name
            continue
        relative = original.relative_to(BASE / 'src')
        conversion = BASE / 'source-conversions' / relative.with_suffix(original.suffix + '.md')
        record = {'source': relative.as_posix(), 'sha256': digest, 'records': [], 'excluded': []}
        if digest in seen:
            record['duplicate_of'] = seen[digest]
            documents.append(record)
            continue
        seen[digest] = original.name
        try:
            if original.suffix.lower() == '.pdf':
                appendices = []
                tables, text = pdf_tables(original, appendices)
                record['appendices'] = appendices
            elif original.suffix.lower() == '.docx':
                tables, text = word_tables(original)
            elif original.suffix.lower() == '.xlsx':
                tables, text = spreadsheet_tables(original)
            else:
                tables, text = doc_tables(original, conversion)
            records, excluded = consume_rows(tables)
            record.update(title=get_title(text, original), text_preview=text[:1500], records=records, excluded=excluded,
                          cub_evidence=bool(re.search(r'\bcubs?\b|grand\s*howl|silver\s*wol|gold\s*wol|\bakela\b', text, re.I)),
                          other_branch_evidence=bool(re.search(r'\bmeerkats?\b|\brovers?\b|troop\s*meeting', text[:1500], re.I)))
            for index, item in enumerate(records, 1):
                item['id'] = f'{original.stem}-r{index:02}'
                item['title'] = entry_title(item['activity'])
                item['folder'] = classify(item['activity'])
                item['tags'] = [tag for tag, pattern in THEMES.items() if re.search(pattern, item['activity'] + ' ' + item['equipment'], re.I)]
                needle = norm(re.sub(r'^(?:activity \d+|steam release|game|relay|yarn|craft|handcraft)\s*[:—–-]*\s*', '', item['title'], flags=re.I))
                ranked = sorted(((SequenceMatcher(None, needle, title).ratio(), path) for title, path in existing), reverse=True)
                item['existing_candidates'] = [(round(score, 2), path) for score, path in ranked[:3] if score > .55]
            print(f'{original.name}: {len(records)} element rows; Cub={record["cub_evidence"]}', flush=True)
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}: {exc}'
            print(f'FAIL {original.name}: {record["error"]}', flush=True)
        documents.append(record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(documents, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    print(f'{len(documents)} source files scanned; {sum(len(d["records"]) for d in documents)} element rows; {sum("error" in d for d in documents)} errors. Review intermediate: {args.output}')


if __name__ == '__main__':
    main()
