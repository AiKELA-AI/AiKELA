#!/usr/bin/env python3
"""Export a Markdown Cub programme to a print-ready PDF using LibreOffice.

Local Markdown images are embedded in the temporary HTML before conversion.
Source documents remain links/references; their embedded images are not extracted
automatically by this exporter.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def inline_markup(text: str, source_dir: Path) -> str:
    text = html.escape(text, quote=False)

    def image(match: re.Match[str]) -> str:
        alt = html.escape(match.group(1), quote=True)
        raw_path = html.unescape(match.group(2)).strip().strip("<>")
        if re.match(r"^https?://", raw_path, re.I):
            return f'<span class="external-image">[Online image: {alt or raw_path}]</span>'
        image_path = (source_dir / raw_path.split("#", 1)[0]).resolve()
        if not image_path.is_file():
            return f'<span class="missing-image">[Image not found: {alt or html.escape(raw_path)}]</span>'
        return f'<img src="{image_path.as_uri()}" alt="{alt}">'

    text = IMAGE_RE.sub(image, text)

    def link(match: re.Match[str]) -> str:
        label = match.group(1)
        target = html.unescape(match.group(2)).strip().strip("<>")
        safe_target = html.escape(target, quote=True)
        return f'<a href="{safe_target}">{label}</a>'

    text = LINK_RE.sub(link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text.replace("&lt;br&gt;", "<br>").replace("  \n", "<br>")


def split_table_row(line: str) -> list[str]:
    value = line.strip().strip("|")
    return [cell.strip().replace(r"\|", "|") for cell in re.split(r"(?<!\\)\|", value)]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def markdown_to_html(markdown: str, source_dir: Path) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    index = 0
    in_list: str | None = None

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append(f"</{in_list}>")
            in_list = None

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            close_list()
            index += 1
            continue

        if stripped.startswith("```"):
            close_list()
            index += 1
            code: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            output.append(f"<pre><code>{html.escape(chr(10).join(code))}</code></pre>")
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            close_list()
            headers = split_table_row(stripped)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(split_table_row(lines[index]))
                index += 1
            output.append('<table><thead><tr>' + ''.join(f'<th>{inline_markup(cell, source_dir)}</th>' for cell in headers) + '</tr></thead><tbody>')
            for row in rows:
                row.extend([""] * max(0, len(headers) - len(row)))
                output.append('<tr>' + ''.join(f'<td>{inline_markup(cell, source_dir)}</td>' for cell in row[:len(headers)]) + '</tr>')
            output.append('</tbody></table>')
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{inline_markup(heading.group(2), source_dir)}</h{level}>")
            index += 1
            continue

        bullet = re.match(r"^[-*+]\s+(.*)$", stripped)
        numbered = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if bullet or numbered:
            desired = "ul" if bullet else "ol"
            if in_list != desired:
                close_list()
                output.append(f"<{desired}>")
                in_list = desired
            output.append(f"<li>{inline_markup((bullet or numbered).group(1), source_dir)}</li>")
            index += 1
            continue

        if stripped.startswith("> "):
            close_list()
            output.append(f"<blockquote>{inline_markup(stripped[2:], source_dir)}</blockquote>")
            index += 1
            continue

        close_list()
        paragraph = [stripped]
        index += 1
        while index < len(lines) and lines[index].strip() and not re.match(r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s|```|\|)", lines[index].strip()):
            paragraph.append(lines[index].strip())
            index += 1
        output.append(f"<p>{inline_markup(' '.join(paragraph), source_dir)}</p>")

    close_list()
    return "\n".join(output)


def render_document(markdown: str, source_dir: Path, title: str) -> str:
    body = markdown_to_html(markdown, source_dir)
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{safe_title}</title>
<style>
@page {{ size: A4 landscape; margin: 13mm; }}
body {{ font-family: Arial, sans-serif; color: #18212b; font-size: 10pt; line-height: 1.35; }}
h1 {{ font-size: 22pt; color: #174f35; }} h2 {{ font-size: 16pt; color: #174f35; border-bottom: 1px solid #9aa; padding-bottom: 3px; }}
h3 {{ font-size: 12pt; color: #245b40; }}
table {{ width: 100%; border-collapse: collapse; table-layout: auto; font-size: 8.5pt; margin: 8px 0 14px; }}
thead {{ display: table-header-group; }} tr {{ page-break-inside: avoid; }}
th, td {{ border: 1px solid #87928c; padding: 5px; vertical-align: top; }}
th {{ background: #e5eee8; text-align: left; }}
img {{ max-width: 100%; max-height: 170mm; object-fit: contain; }}
li {{ margin: 2px 0; }} a {{ color: #174f78; text-decoration: underline; overflow-wrap: anywhere; }}
code, pre {{ font-family: monospace; white-space: pre-wrap; }}
.missing-image, .external-image {{ color: #8b3c00; font-weight: bold; }}
blockquote {{ border-left: 3px solid #75a58a; padding-left: 10px; color: #445; }}
</style></head><body>{body}</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("programme", type=Path, help="Markdown programme file")
    parser.add_argument("-o", "--output-dir", type=Path, help="PDF output folder (default: alongside source in pdf/)")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing PDF with the same name")
    args = parser.parse_args()

    source = args.programme.expanduser().resolve()
    if not source.is_file():
        parser.error(f"Programme file not found: {source}")
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if not office:
        parser.error("LibreOffice was not found. Install LibreOffice, then rerun this command.")

    output_dir = (args.output_dir.expanduser().resolve() if args.output_dir else source.parent / "pdf")
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{source.stem}.pdf"
    if pdf_path.exists() and not args.overwrite:
        parser.error(f"PDF already exists: {pdf_path}. Use --overwrite to replace it.")
    markdown = source.read_text(encoding="utf-8")
    document = render_document(markdown, source.parent, source.stem)
    with tempfile.TemporaryDirectory(prefix="aikela-pdf-", dir=output_dir) as temp_dir:
        temp_path = Path(temp_dir)
        html_path = temp_path / f"{source.stem}.html"
        html_path.write_text(document, encoding="utf-8")
        result = subprocess.run(
            [office, "--headless", "--convert-to", "pdf", "--outdir", str(temp_path), str(html_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        generated_path = temp_path / f"{source.stem}.pdf"
        if result.returncode or not generated_path.is_file():
            detail = result.stderr.strip() or result.stdout.strip() or f"LibreOffice exited with status {result.returncode}"
            raise SystemExit(f"PDF export failed: {detail}")
        generated_path.replace(pdf_path)
    print(f"PDF created: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
