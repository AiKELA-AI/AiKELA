from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlsplit, unquote
from pathlib import Path
import re

PAGE = "https://scoutwiki.scouts.org.za/wiki/Programmes_on_a_Plate"
DEST = Path.home() / "cub-ai" / "docs" / "programmes-on-a-plate"
YEARS = {"2016", "2015", "2014", "2013", "2012"}
EXTENSIONS = {
    ".doc", ".docx", ".pdf", ".xls", ".xlsx",
    ".ppt", ".pptx", ".odt", ".ods", ".zip"
}


class ProgrammeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_heading = False
        self.pending_heading_id = None
        self.current_year = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "h3":
            self.in_heading = True
            self.pending_heading_id = None
            self.current_year = None

        elif tag == "span" and self.in_heading:
            self.pending_heading_id = attrs.get("id")

        elif tag == "a" and self.current_year in YEARS:
            href = attrs.get("href", "")
            extension = Path(urlsplit(href).path).suffix.lower()

            if extension in EXTENSIONS:
                self.links.append(
                    (self.current_year, urljoin(PAGE, href))
                )

    def handle_endtag(self, tag):
        if tag == "h3":
            self.in_heading = False
            match = re.search(
                r"Programmes_on_a_plate_(\d{4})$",
                self.pending_heading_id or ""
            )
            year = match.group(1) if match else None
            self.current_year = year if year in YEARS else None


def main():
    DEST.mkdir(parents=True, exist_ok=True)

    request = Request(
        PAGE,
        headers={"User-Agent": "Mozilla/5.0 (compatible; CubResourceDownloader/1.0)"}
    )

    print("Reading the Programme on a Plate page...")
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = ProgrammeParser()
    parser.feed(html)

    # Remove duplicate URLs while preserving their year.
    links = list(dict.fromkeys(parser.links))

    if not links:
        print("No matching documents found. The page structure may have changed.")
        return

    print(f"Found {len(links)} document links for 2016–2012.")
    counts = {year: 0 for year in YEARS}

    for year, url in links:
        filename = unquote(Path(urlsplit(url).path).name)
        if not filename:
            continue

        destination = DEST / filename

        if destination.exists():
            print(f"SKIP  {filename} (already exists)")
            counts[year] += 1
            continue

        try:
            request = Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urlopen(request, timeout=60) as response:
                data = response.read()

            # Avoid saving an HTML error page as a document.
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" in content_type and not filename.lower().endswith(".html"):
                print(f"FAIL  {filename} (server returned HTML, not a document)")
                continue

            destination.write_bytes(data)
            print(f"OK    [{year}] {filename} ({len(data):,} bytes)")
            counts[year] += 1

        except Exception as error:
            print(f"FAIL  [{year}] {filename}: {error}")

    print(f"\nFiles saved in: {DEST}")
    print("\nFiles processed by year:")
    for year in sorted(YEARS, reverse=True):
        print(f"  {year}: {counts[year]}")


if __name__ == "__main__":
    main()
