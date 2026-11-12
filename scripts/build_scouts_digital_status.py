#!/usr/bin/env python3
"""Catalogue originals, duplicates and conversion/extraction status; no network."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/scouts-digital'
SUPPORTED = {'.pdf', '.docx', '.doc', '.xlsx'}


def main():
    catalogue = BASE / 'PROGRAMMES-INDEX.md'
    coverage = BASE / 'INITIAL-BATCH-COVERAGE.md'
    reviewed_text = catalogue.read_text(encoding='utf-8') + '\n' + (coverage.read_text(encoding='utf-8') if coverage.exists() else '')
    reviewed_names = set(re.findall(r'Program_Doc_ID_\d+_\d+_\d{4}-\d{2}-\d{2}\.(?:pdf|docx|doc)', reviewed_text))
    files = sorted(p for p in (BASE / 'src').rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED)
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    groups = defaultdict(list)
    for path, digest in hashes.items():
        groups[digest].append(path)
    reviewed_hashes = {hashes[path] for path in files if path.name in reviewed_names}
    bulk_data = BASE / 'BULK-EXTRACTION-DATA.json'
    bulk = json.loads(bulk_data.read_text(encoding='utf-8')) if bulk_data.exists() else []
    parsed_hashes = {item['sha256'] for item in bulk if item.get('cub_evidence') and any(record.get('target') for record in item.get('records', []))}
    totals = Counter()
    rows = []
    for path in files:
        relative = path.relative_to(BASE / 'src')
        converted = BASE / 'source-conversions' / relative.with_suffix(path.suffix + '.md')
        if converted.exists() and hashes[path] in reviewed_hashes:
            state = 'Reviewed extraction / canonical reuse linked'
        elif converted.exists() and hashes[path] in parsed_hashes:
            state = 'Bulk source elements indexed; entry-level review flags retained'
        elif converted.exists():
            state = 'Converted; Cub content / library extraction review pending'
        else:
            state = 'Downloaded only; Cub content / conversion / extraction pending'
        totals[state] += 1
        group = groups[hashes[path]]
        alias = 'Identical content: ' + ', '.join(other.name for other in group if other != path) if len(group) > 1 else ''
        source_link = quote(path.relative_to(BASE).as_posix(), safe='/')
        conversion_link = f'[Markdown](<{quote(converted.relative_to(BASE).as_posix(), safe="/")}>)' if converted.exists() else 'Not converted'
        rows.append(f'| [{relative.as_posix()}](<{source_link}>) | {state} | {conversion_link} | {alias} |')
    lines = ['# Scouts Digital import status', '',
             f'{len(files)} original files; {len(groups)} unique content hashes. Originals and duplicate copies are preserved.', '',
             'Downloaded, converted and extracted are separate states. Bulk indexed entries contain source text and review flags, not independently validated teaching or badge credit. Resolve reference-only entries, missing source detail and safety/attachment flags when planning. A converted document may still need branch checks, extraction or corrections; no source is assumed to be an official requirement.', '',
             '| State | Original files |', '| --- | --- |']
    lines += [f'| {state} | {count} |' for state, count in totals.items()]
    lines += ['', '[Reviewed programme catalogue](PROGRAMMES-INDEX.md) · [Initial twelve-upload coverage](INITIAL-BATCH-COVERAGE.md) · [Bulk programme coverage](BULK-PROGRAMMES.md) · [Download log and exact source URLs](DOWNLOAD-LOG.md)', '',
              'The three `(1)`, `(2)` and `(3)` Fire Safety DOCX downloads are byte-identical to the unsuffixed 16 October file. They are not three additional unique programmes. Source filenames, internal dates and authorship must be read from content rather than inferred from a download name.', '',
              '| Original | Status | Conversion | Duplicate content |', '| --- | --- | --- | --- |', *rows]
    (BASE / 'IMPORT-STATUS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Wrote import status for {len(files)} files / {len(groups)} unique hashes.')
    for state, count in totals.items():
        print(f'{count}: {state}')


if __name__ == '__main__':
    main()
