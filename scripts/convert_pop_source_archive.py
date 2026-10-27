#!/usr/bin/env python3
"""Convert every original POP source file into a reviewable Markdown archive.

Word documents are exported to HTML by LibreOffice so that tables and embedded
images survive. PDFs retain page text and get a rendered page image for visual
review. Originals in docs/pop/src are read-only inputs.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "pop" / "src"
DEST = ROOT / "docs" / "pop" / "source-conversions"
SUPPORTED = {".doc", ".docx", ".pdf"}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


class WordHtmlParser(HTMLParser):
    """Collect Word HTML in reading order while preserving table rows."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.table = self.row = self.cell = None
        self.block_tag = None
        self.block_text = []
        self.metadata = {}
        self.ignored_tags = []

    def flush_block(self):
        value = clean("".join(self.block_text))
        if value:
            self.blocks.append((self.block_tag or "p", value))
        self.block_tag, self.block_text = None, []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"head", "style", "script", "title"}:
            self.ignored_tags.append(tag)
            return
        if self.ignored_tags:
            return
        if tag == "table":
            self.flush_block()
            self.table = []
            self.blocks.append(("table", self.table))
        elif tag == "tr" and self.table is not None:
            self.row = []
            self.table.append(self.row)
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = {"parts": []}
            self.row.append(self.cell)
        elif tag in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"} and self.table is None:
            self.flush_block()
            self.block_tag = tag
        elif tag == "br":
            (self.cell["parts"] if self.cell is not None else self.block_text).append(" ")
        elif tag == "img":
            src = values.get("src", "")
            alt = values.get("alt") or "Source image"
            item = f"![{alt}](<{src}>)"
            (self.cell["parts"] if self.cell is not None else self.block_text).append(item)

    def handle_endtag(self, tag):
        if tag in self.ignored_tags:
            self.ignored_tags.remove(tag)
            return
        if self.ignored_tags:
            return
        if tag in {"td", "th"}:
            self.cell = None
        elif tag == "tr":
            self.row = None
        elif tag == "table":
            self.table = None
        elif tag in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"} and self.cell is None:
            self.flush_block()

    def handle_data(self, data):
        if self.ignored_tags:
            return
        (self.cell["parts"] if self.cell is not None else self.block_text).append(data)


def render_table(raw_rows):
    rows = [[clean("".join(cell["parts"])) for cell in row] for row in raw_rows]
    rows = [row for row in rows if any(row)]
    if not rows:
        return ""
    width = max(map(len, rows))
    rows = [row + [""] * (width - len(row)) for row in rows]
    output = ["| " + " | ".join(cell.replace("|", r"\|") for cell in rows[0]) + " |",
              "| " + " | ".join("---" for _ in range(width)) + " |"]
    output.extend("| " + " | ".join(cell.replace("|", r"\|") for cell in row) + " |" for row in rows[1:])
    return "\n".join(output)


def render_blocks(parser: WordHtmlParser) -> str:
    parser.flush_block()
    output = []
    for kind, value in parser.blocks:
        if kind == "table":
            item = render_table(value)
            if item:
                output.append(item)
        elif kind == "li":
            output.append(f"- {value}")
        elif kind.startswith("h") and kind[1:].isdigit():
            output.append("#" * min(int(kind[1:]) + 1, 6) + f" {value}")
        else:
            output.append(value)
    return "\n\n".join(output)


def convert_word(path: Path, out: Path, asset_dir: Path) -> tuple[str, list[str]]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("LibreOffice (soffice) is required to convert Word files")
    with tempfile.TemporaryDirectory(prefix="pop-word-") as tmp:
        work = Path(tmp)
        profile = work / "lo-profile"
        result = subprocess.run(
            [soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless",
             "--convert-to", "html", "--outdir", str(work), str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        html_path = next(iter(work.glob("*.html")), None) or next(iter(work.glob("*.htm")), None)
        if result.returncode or html_path is None:
            raise RuntimeError((result.stderr or result.stdout).strip() or "LibreOffice produced no HTML")
        html = html_path.read_text(encoding="utf-8", errors="replace")
        # Keep source images as local assets, and replace their source names with
        # Markdown-relative links before parsing the document structure.
        references = []
        for image in sorted(p for p in work.iterdir() if p.is_file() and p != html_path):
            if image.suffix.casefold() not in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}:
                continue
            asset_dir.mkdir(parents=True, exist_ok=True)
            safe_image_name = re.sub(r"[()]", "_", image.name)
            target = asset_dir / safe_image_name
            shutil.copy2(image, target)
            references.append(f"![Source image: {image.name}](<assets/{asset_dir.name}/{safe_image_name}>)")
            html = re.sub(
                rf'(<img\b[^>]*\bsrc=[\"\']){re.escape(image.name)}([\"\'])',
                rf'\1assets/{asset_dir.name}/{safe_image_name}\2', html, flags=re.I,
            )
        parser = WordHtmlParser()
        # The parser treats HTML text in source order. Add image refs to cell or
        # paragraph text in a small parser subclass-like preprocessing step.
        class ImageParser(WordHtmlParser):
            def handle_starttag(self, tag, attrs):
                if tag == "img":
                    values = dict(attrs)
                    src = values.get("src", "")
                    alt = values.get("alt") or "Source image"
                    value = f"![{alt}]({src})"
                    if self.cell is not None:
                        self.cell["parts"].append(value)
                    else:
                        self.block_text.append(value)
                    return
                super().handle_starttag(tag, attrs)
        parser = ImageParser()
        parser.feed(html.replace("\x00", ""))
        body = render_blocks(parser)
        if not body.strip():
            raise RuntimeError("Word conversion yielded no readable text")
        return body, references


def convert_pdf(path: Path, asset_dir: Path) -> tuple[str, list[str]]:
    pdftotext = shutil.which("pdftotext")
    pdfinfo = shutil.which("pdfinfo")
    if not pdftotext or not pdfinfo:
        raise RuntimeError("Poppler pdftotext and pdfinfo are required to convert PDF files")
    text_result = subprocess.run([pdftotext, "-layout", "-enc", "UTF-8", str(path), "-"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    info_result = subprocess.run([pdfinfo, str(path)], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
    if text_result.returncode or info_result.returncode:
        raise RuntimeError((text_result.stderr or info_result.stderr).strip() or "PDF text extraction failed")
    match = re.search(r"^Pages:\s+(\d+)", info_result.stdout, re.M)
    page_count = int(match.group(1)) if match else 1
    page_texts = text_result.stdout.split("\f")
    chunks, references = [], []
    for number in range(1, page_count + 1):
        text = page_texts[number - 1].strip() if number <= len(page_texts) else ""
        chunks.append(f"## Page {number}\n\n{text or '_No extractable text on this page._'}")
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        asset_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pop-pdf-") as tmp:
            prefix = Path(tmp) / "page"
            result = subprocess.run(
                [pdftoppm, "-png", "-scale-to", "1400", str(path), str(prefix)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "pdftoppm failed")
            for index, image in enumerate(sorted(Path(tmp).glob("page-*.png")), 1):
                target = asset_dir / f"page-{index:03}.png"
                shutil.copy2(image, target)
                references.append(f"### Original page {index}\n\n![Page {index} visual](assets/{asset_dir.name}/{target.name})")
    else:
        references.append("Page images were not rendered: `pdftoppm` is unavailable. Use the original PDF for visual review.")
    body = "\n\n".join(chunks)
    if references:
        body += "\n\n## Original page visuals\n\n" + "\n\n".join(references)
    return body, []


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", type=Path, default=SOURCE)
    cli.add_argument("--destination", type=Path, default=DEST)
    args = cli.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    files = sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED)
    destination.mkdir(parents=True, exist_ok=True)
    successes, errors = 0, []
    for path in files:
        out = destination / f"{path.name}.md"
        asset_dir = destination / "assets" / path.name
        try:
            if path.suffix.lower() in {".doc", ".docx"}:
                body, _ = convert_word(path, out, asset_dir)
            elif path.suffix.lower() == ".pdf":
                body, _ = convert_pdf(path, asset_dir)
            document = f"# {path.stem.replace('_', ' ')}\n\n- Original: [`{path.name}`](../src/{path.name})\n- Conversion note: source images are retained as local assets; review page visuals against the original before reuse.\n\n---\n\n{body.strip()}\n"
            out.write_text(document, encoding="utf-8")
            successes += 1
            print(f"OK    {path.name}")
        except Exception as exc:
            errors.append({"source": path.name, "error": f"{type(exc).__name__}: {exc}"})
            print(f"FAIL  {path.name}: {errors[-1]['error']}")
    (destination / "conversion-errors.json").write_text(__import__("json").dumps(errors, indent=2) + "\n", encoding="utf-8")
    print(f"Finished: {successes}/{len(files)} converted; {len(errors)} failed. Output: {destination}")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
