#!/usr/bin/env python3
"""Archive user-downloaded Scouts Digital PDF/DOCX/DOC/XLSX as Markdown.

PDF requires PyMuPDF; legacy DOC requires olefile. DOCX/XLSX use the standard library.
Originals are never modified. PDFs retain page renders; DOCX retains embedded
media and tables; legacy DOC retains piece-table text. Review before cataloguing.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import posixpath
import re
import struct
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

SUPPORTED = {'.pdf', '.docx', '.doc', '.xlsx'}
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def relative_link(target: Path, output: Path) -> str:
    return quote(Path(os.path.relpath(target, output.parent)).as_posix(), safe='/')


def fenced(text: str) -> str:
    fence = '`' * max(3, max((len(part) for part in re.findall(r'`+', text)), default=0) + 1)
    return f'{fence}text\n{text}\n{fence}'


def legacy_doc_text(original: Path) -> str:
    """Read Word 97–2003 text pieces; refuse encrypted/unsupported structures."""
    import olefile
    with olefile.OleFileIO(original) as ole:
        word = ole.openstream('WordDocument').read()
        flags = struct.unpack_from('<H', word, 10)[0]
        if flags & 0x8100:
            raise ValueError('Encrypted/obfuscated DOC is unsupported')
        table = ole.openstream('1Table' if flags & 0x0200 else '0Table').read()
        fc, length = struct.unpack_from('<II', word, 0x1A2)
        clx = table[fc:fc + length]
        offset = 0
        while offset < len(clx) and clx[offset] == 1:
            offset += 3 + struct.unpack_from('<H', clx, offset + 1)[0]
        if offset + 5 > len(clx) or clx[offset] != 2:
            raise ValueError('Unsupported DOC piece table; use a Word/LibreOffice export')
        size = struct.unpack_from('<I', clx, offset + 1)[0]
        plc = clx[offset + 5:offset + 5 + size]
        if len(plc) != size or (size - 4) % 12:
            raise ValueError('Invalid DOC piece table')
        count = (size - 4) // 12
        positions = struct.unpack_from(f'<{count + 1}I', plc)
        chunks = []
        for index in range(count):
            start = struct.unpack_from('<I', plc, 4 * (count + 1) + index * 8 + 2)[0]
            compressed = bool(start & 0x40000000)
            start &= 0x3fffffff
            if compressed:
                start //= 2
            length = positions[index + 1] - positions[index]
            end = start + length * (1 if compressed else 2)
            if end > len(word):
                raise ValueError('DOC piece points outside WordDocument stream')
            chunks.append(word[start:end].decode('cp1252' if compressed else 'utf-16-le', errors='replace'))
    text = ''.join(chunks).replace('\r', '\n').replace('\x07', '\t').replace('\x0b', '\n')
    return re.sub(r'[\x00-\x06\x08\x0e-\x1f]', '', text).strip()


def convert_docx(original: Path, output: Path, assets: Path) -> tuple[str, list[str]]:
    with zipfile.ZipFile(original) as archive:
        document = ET.fromstring(archive.read('word/document.xml'))
        rel_name = 'word/_rels/document.xml.rels'
        relationships = {node.get('Id'): node.attrib for node in ET.fromstring(archive.read(rel_name))} if rel_name in archive.namelist() else {}
        images = {}
        for name in archive.namelist():
            if name.startswith('word/media/') and not name.endswith('/'):
                assets.mkdir(parents=True, exist_ok=True)
                target = assets / Path(name).name
                target.write_bytes(archive.read(name))
                images[name] = relative_link(target, output)

        def paragraph(node):
            parts = []
            for child in node.iter():
                if child.tag == W + 't':
                    parts.append(child.text or '')
                elif child.tag == W + 'tab':
                    parts.append(' ')
                elif child.tag in {W + 'br', W + 'cr'}:
                    parts.append('<br>')
                elif child.tag.endswith('}blip'):
                    relation = relationships.get(child.get(R + 'embed'), {})
                    name = posixpath.normpath('word/' + relation.get('Target', ''))
                    if name in images:
                        parts.append(f' ![Embedded source visual](<{images[name]}>) ')
                elif child.tag == W + 'hyperlink':
                    relation = relationships.get(child.get(R + 'id'), {})
                    if relation.get('TargetMode') == 'External':
                        parts.append(f" <{relation['Target']}>")
            return ''.join(parts).strip()

        blocks = []
        for child in document.find(W + 'body'):
            if child.tag == W + 'p':
                text = paragraph(child)
                if text:
                    blocks.append(text)
            elif child.tag == W + 'tbl':
                rows = []
                for row in child.findall(W + 'tr'):
                    cells = ['<br>'.join(filter(None, (paragraph(p) for p in cell.findall('.//' + W + 'p')))).replace('|', '\\|') for cell in row.findall(W + 'tc')]
                    rows.append(cells)
                if rows:
                    width = max(map(len, rows))
                    rows = [row + [''] * (width - len(row)) for row in rows]
                    blocks.append('\n'.join(['| ' + ' | '.join(rows[0]) + ' |', '| ' + ' | '.join(['---'] * width) + ' |'] + ['| ' + ' | '.join(row) + ' |' for row in rows[1:]]))
        for name in archive.namelist():
            if re.fullmatch(r'word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml', name):
                extra = [''.join(p.itertext()).strip() for p in ET.fromstring(archive.read(name)).iter(W + 'p')]
                if any(extra):
                    blocks.append(f'### Additional source part: {Path(name).name}\n\n' + '\n\n'.join(filter(None, extra)))
        if images:
            blocks.append('## Embedded source visuals\n\n' + '\n\n'.join(f'![{Path(name).name}](<{link}>)' for name, link in images.items()))
        if not any(''.join(p.itertext()).strip() for p in document.iter(W + 't')):
            raise ValueError('DOCX has no readable text; manual review/OCR required')
        return original.stem, ['- **Format:** DOCX; section/table references only, original pagination not reproduced.',
                               '- **Conversion limitations:** Tables and embedded media retained; floating shapes, automatic numbering and page layout may differ from Word.',
                               '## Document text\n\n' + '\n\n'.join(blocks)]


def convert_xlsx(original: Path, output: Path, assets: Path) -> tuple[str, list[str]]:
    """Keep populated worksheet cells, cached values/formulas and source media."""
    namespace = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(original) as archive:
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings = [''.join(node.itertext()) for node in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', namespace)]
        relations = {node.get('Id'): node.get('Target') for node in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        blocks = ['## Document text']
        for sheet in ET.fromstring(archive.read('xl/workbook.xml')).findall('s:sheets/s:sheet', namespace):
            target = relations[sheet.get(R + 'id')]
            target = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
            content = ET.fromstring(archive.read(target))
            blocks.append(f"### Worksheet: {sheet.get('name')}\n\n| Cell | Source content |\n| --- | --- |")
            for cell in content.findall('.//s:sheetData/s:row/s:c', namespace):
                value = cell.find('s:v', namespace)
                value = value.text or '' if value is not None else ''
                if cell.get('t') == 's' and value:
                    value = strings[int(value)]
                elif cell.get('t') == 'inlineStr':
                    inline = cell.find('s:is', namespace)
                    value = ''.join(inline.itertext()) if inline is not None else ''
                formula = cell.find('s:f', namespace)
                if formula is not None:
                    value = f'Formula: ={formula.text}; cached value: {value or "not supplied"}'
                if value.strip():
                    blocks.append(f"| {cell.get('r')} | {value.replace('|', r'\|').replace(chr(10), '<br>')} |")
        for name in archive.namelist():
            if name.startswith('xl/media/') and not name.endswith('/'):
                assets.mkdir(parents=True, exist_ok=True)
                target = assets / Path(name).name
                target.write_bytes(archive.read(name))
                blocks.append(f'![Embedded worksheet visual](<{relative_link(target, output)}>)')
        if not any(line.startswith('| ') and not line.startswith('| Cell') and not line.startswith('| ---') for line in blocks):
            raise ValueError('No populated worksheet cells found')
        return original.stem, ['- **Format:** XLSX; populated cells by worksheet and cell reference.',
                               '- **Conversion limitations:** Formatting, merged-cell layout and print pagination are not reconstructed. Formulas are not executed; cached values are identified. Retain original for layout.',
                               '\n\n'.join(blocks)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('docs/scouts-digital/src'))
    parser.add_argument('--destination', type=Path, default=Path('docs/scouts-digital/source-conversions'))
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--file', action='append', help='Import only this exact source filename; repeat for a selected batch')
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    if destination == source or source in destination.parents:
        parser.error('Destination must be outside the original source archive.')
    files = sorted(p for p in source.rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED)
    if args.file:
        files = [path for path in files if path.name in args.file]
        missing = set(args.file) - {path.name for path in files}
        if missing:
            parser.error('Requested source not found/supported: ' + ', '.join(sorted(missing)))
    if not files:
        parser.error('No PDF/DOCX/DOC files found; nothing converted.')
    failures = 0
    skipped = 0
    for original in files:
        output = destination / original.relative_to(source).with_suffix(original.suffix + '.md')
        try:
            digest = hashlib.sha256(original.read_bytes()).hexdigest()
            if output.exists() and not args.overwrite:
                if f'**SHA-256:** `{digest}`' in output.read_text(encoding='utf-8'):
                    print(f'SKIP unchanged {original.name}')
                    skipped += 1
                    continue
                raise FileExistsError(f'{output}: use --overwrite to replace a conversion')
            original_link = relative_link(original, output)
            assets = destination / 'assets' / original.relative_to(source)
            body = []
            title = original.stem
            if original.suffix.lower() == '.pdf':
                import pymupdf
                with pymupdf.open(original) as document:
                    title = document.metadata.get('title') or original.stem
                    body = [f'- **Pages:** {len(document)}', '- **Format:** PDF; text and a rendered original retained for every page.',
                            '- **Conversion limitations:** Text from table columns may interleave; use original page visuals for layout and image-only content.']
                    if not len(document):
                        raise ValueError('PDF has no pages')
                    assets.mkdir(parents=True, exist_ok=True)
                    for number, page in enumerate(document, 1):
                        text = page.get_text(sort=True).replace('\u200b', '').strip()
                        visual = assets / f'page-{number:03}.png'
                        page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(visual)
                        body.append(f'## Page {number}\n\n[Original page {number}]({original_link}#page={number})\n\n' + (fenced(text) if text else '_No extractable text: review the retained page visual below; it may contain diagrams or blank layout._') + f'\n\n![Original page {number}](<{relative_link(visual, output)}>)')
                        links = sorted({link['uri'] for link in page.get_links() if link.get('uri')})
                        if links:
                            body.append('### Links embedded on this page\n\n' + '\n'.join(f'- <{uri}>' for uri in links))
            elif original.suffix.lower() == '.xlsx':
                title, body = convert_xlsx(original, output, assets)
            elif original.suffix.lower() == '.docx':
                title, body = convert_docx(original, output, assets)
            else:
                text = legacy_doc_text(original)
                if not text:
                    raise ValueError('DOC has no readable text; manual review/OCR required')
                body = ['- **Format:** DOC; Word 97–2003 piece-table text, not a paginated rendering.',
                        '- **Conversion limitations:** Text extracted without Word layout, cell boundaries, embedded pictures or diagrams. Control/field text may remain. Review the original Word file for all visuals and formatting.',
                        '## Document text\n\n' + fenced(text)]
            header = [f'# {title}', f'- **Original:** [{original.name}]({original_link})',
                      '- **Provenance:** User-downloaded from https://ssa.scouts.digital/shared-programs; individual programme URL not supplied. Author, if stated, remains in source text.',
                      f'- **SHA-256:** `{digest}`',
                      '- **Status:** Archival source conversion, not an adapted programme or verified SSA requirement source.',
                      '- **Advancement / badge link:** Source claims only; verify against authoritative SSA material before use.',
                      '- **Visual aid / image reference:** See source visuals/format limitations below and the linked original. External links are retained, not downloaded.']
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text('\n\n'.join(header + body) + '\n', encoding='utf-8')
            print(f'OK {original.name} -> {output}')
        except Exception as exc:
            failures += 1
            print(f'FAIL {original}: {exc}')
    print(f'{len(files) - failures - skipped} converted; {skipped} unchanged; {failures} failed; {len(files)} source files.')
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
