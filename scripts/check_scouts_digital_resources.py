#!/usr/bin/env python3
"""Check Scouts Digital archive integrity and shared-library discoverability.

Uses only the Python standard library, so checks also work in a fresh clone.
Does not validate teaching content, SSA requirements or remote web links.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs' / 'scouts-digital'
LIBRARIES = {
    'games': 'GAMES-INDEX.md',
    'activities': 'ACTIVITIES-INDEX.md',
    'crafts': 'CRAFTS-INDEX.md',
    'yarns': 'YARNS-INDEX.md',
}


def local_links(path: Path, text: str) -> set[Path]:
    result = set()
    for match in re.finditer(r'!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)', text):
        target = match.group(1).strip('<>')
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        result.add((path.parent / unquote(parts.path)).resolve())
    return result


def main() -> int:
    errors = []
    inspected = {}
    catalogue = BASE / 'PROGRAMMES-INDEX.md'
    if not catalogue.exists():
        print('FAIL: missing Scouts Digital programme catalogue')
        return 1
    coverage_pages = [catalogue]
    batch_coverage = BASE / 'INITIAL-BATCH-COVERAGE.md'
    if batch_coverage.exists():
        coverage_pages.append(batch_coverage)
    bulk_coverage = BASE / 'BULK-PROGRAMMES.md'
    if bulk_coverage.exists():
        coverage_pages.append(bulk_coverage)
    coverage = set().union(*(local_links(path, path.read_text(encoding='utf-8')) for path in coverage_pages))
    extracted = []
    page_count = 0
    originals = sorted(path for path in (BASE / 'src').rglob('*') if path.is_file() and path.suffix.lower() in {'.pdf', '.docx', '.doc', '.xlsx'})
    pending = 0
    converted_count = 0
    if not originals:
        errors.append('No source documents found')
    for original in originals:
        conversion = BASE / 'source-conversions' / original.relative_to(BASE / 'src').with_suffix(original.suffix + '.md')
        if not conversion.exists():
            pending += 1
            continue
        converted_count += 1
        text = conversion.read_text(encoding='utf-8')
        inspected[conversion] = text
        digest = re.search(r'\*\*SHA-256:\*\* `([0-9a-f]{64})`', text)
        if not digest or digest.group(1) != hashlib.sha256(original.read_bytes()).hexdigest():
            errors.append(f'Source hash mismatch: {conversion.relative_to(ROOT)}')
        if original.suffix.lower() == '.pdf':
            pages = re.search(r'\*\*Pages:\*\* (\d+)', text)
            sections = [int(number) for number in re.findall(r'^## Page (\d+)\s*$', text, re.M)]
            if not pages or sections != list(range(1, int(pages.group(1)) + 1)):
                errors.append(f'Page-section mismatch: {conversion.relative_to(ROOT)}')
            else:
                page_count += len(sections)
            for section in re.split(r'^## Page \d+\s*$', text, flags=re.M)[1:]:
                if 'No extractable text' in section and '![Original page' not in section:
                    errors.append(f'Image-only page has no retained visual: {conversion.relative_to(ROOT)}')
        elif '## Document text' not in text:
            errors.append(f'Missing Word document text: {conversion.relative_to(ROOT)}')
        if re.search(r'```text\s*```', text):
            errors.append(f'Empty extracted page: {conversion.relative_to(ROOT)}')

    for folder, index_name in LIBRARIES.items():
        library = ROOT / 'docs' / folder
        index = library / index_name
        indexed = local_links(index, index.read_text(encoding='utf-8'))
        pop_index = library / 'POP-EXTRACTED-INDEX.md'
        pop_indexed = local_links(pop_index, pop_index.read_text(encoding='utf-8')) if pop_index.exists() else set()
        for entry in library.glob('*.md'):
            if entry.name in {index_name, 'POP-EXTRACTED-INDEX.md'}:
                continue
            text = entry.read_text(encoding='utf-8')
            tag_section = re.search(r'^## Tags\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
            tags = set(re.findall(r'#[a-z0-9-]+', tag_section.group(1))) if tag_section else set()
            if '#source-scouts-digital' not in tags:
                continue
            extracted.append(entry)
            inspected[entry] = text
            for heading in ('Type', 'Equipment', 'Instructions', 'Visual aid / image reference', 'Tags', 'Source'):
                if f'## {heading}' not in text:
                    errors.append(f'Missing {heading}: {entry.relative_to(ROOT)}')
            if not re.search(r'^## Advancement(?: covered)? / badge link\s*$', text, re.M):
                errors.append(f'Missing advancement field: {entry.relative_to(ROOT)}')
            if not re.search(r'\breused\b|\badapted\b', text, re.I):
                errors.append(f'Missing reuse/adaptation status: {entry.relative_to(ROOT)}')
            if len(tags) < 3:
                errors.append(f'Insufficient search tags: {entry.relative_to(ROOT)}')
            if entry.resolve() not in indexed:
                errors.append(f'Not in source-neutral index: {entry.relative_to(ROOT)}')
            if entry.resolve() not in coverage:
                errors.append(f'Not linked from coverage table: {entry.relative_to(ROOT)}')
            if entry.resolve() in pop_indexed and '#source-pop' not in tags:
                errors.append(f'Non-POP entry in POP-only index: {entry.relative_to(ROOT)}')
            if folder == 'yarns' and re.search(r'\btransition snippets\b', text, re.I):
                errors.append(f'Programme transitions must stay source-only: {entry.relative_to(ROOT)}')
    if not extracted:
        errors.append('No Scouts Digital library entries found')
    for path in (*coverage_pages, BASE / 'README.md', ROOT / 'docs' / 'RESOURCE-GUIDE.md'):
        inspected[path] = path.read_text(encoding='utf-8')
    for path, text in inspected.items():
        for target in local_links(path, text):
            if not target.exists():
                errors.append(f'Broken local link in {path.relative_to(ROOT)}: {target}')
    if errors:
        for error in errors:
            print(f'FAIL: {error}')
        return 1
    print(f'OK: {len(originals)} source documents, {converted_count} converted, {page_count} PDF page sections, {len(extracted)} tagged library entries.')
    print(f'Pending conversion (not completed extractions): {pending}. See IMPORT-STATUS.md.')
    print('Source hashes, required fields, coverage links, source-neutral indexes, POP separation and local file links checked.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
