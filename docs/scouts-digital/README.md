# Scouts Digital Cub programmes

User-downloaded Cub programme examples from [Scouts Digital shared programmes](https://ssa.scouts.digital/shared-programs). These are shared planning resources, not official SSA requirement documents or local instructions for any AiKELA Pack.

- [Programme catalogue and review notes](PROGRAMMES-INDEX.md)
- `src/`: original downloaded PDFs and supplied attachments; preserve filenames and content.
- `source-conversions/`: searchable, page-by-page archival text with links to original PDF pages and embedded web links. Table columns may interleave; consult the PDF for layout. No embedded pictures or separate templates are supplied by a text conversion.

Both initial imports were checked for Cub context on 12 November 2026. Their reusable elements have been extracted or matched to existing library entries, with tags, source pages, advancement limits and visual references. See the catalogue's coverage tables. Story transitions and Pack-specific routines remain only in the original programmes; they are not standalone yarns. Search the shared libraries before adapting or extracting an element and preserve its actual provenance.

Programme authors and individual sharing URLs were not supplied. Dates in the catalogue are meeting dates printed in the PDFs. Source files may include names and Pack-specific awards; keep those as archival context and review personal information and redistribution permission before publishing. No public upload was performed.

## Importing more source files

Drop downloaded Cub programme PDF, DOCX, DOC or XLSX files and any attachments directly into `docs/scouts-digital/src/`. No renaming or programme subfolders are required. The importer accepts files directly in `src/` as well as files in existing subfolders. XLSX conversion preserves populated worksheet cells, cached formula results and embedded media; it does not execute formulas or reproduce spreadsheet layout.

Tell the assistant when the downloads are ready. It should identify the programmes from their contents, check for duplicates, convert them, extract/reuse and tag their elements, and update the catalogues. Programme-named folders are optional organisation for the assistant to handle, not preparation required of the Akela. Preserve original filenames and contents; if organising files later, update every affected source/conversion/library link. Match attachments from evidence in the files rather than guessing from proximity in the download folder. Record individual sharing URLs, authors and reuse terms when available; missing metadata must not be invented.

PDF import requires PyMuPDF; legacy Word DOC import requires olefile. DOCX and XLSX import use Python's standard library. These are maintenance dependencies, not requirements for planning from an existing clone. Install dependencies only when converting new sources:

```sh
python -m pip install pymupdf olefile
```

Run from the repository root:

```sh
python scripts/import_scouts_digital.py
```

The script skips existing conversions whose recorded source hash is unchanged and refuses to replace a changed conversion unless `--overwrite` is supplied. New PDF conversions retain every page as an image, explicitly flagging pages without extractable text. DOCX conversions retain tables and embedded media; DOC conversions preserve text but refer to the original for layout/images. Do not describe image-only pages as missing attachments. The importer does not access an account, verify badges or extract library elements automatically.

## Direct downloads

The user-supplied [download queue](DOWNLOAD-QUEUE.md) contains 172 unique document filenames. `python scripts/download_scouts_digital.py` downloads sequentially with a minimum five-second request interval, preserves existing valid files, validates file formats and records source URLs/hashes in the [download log](DOWNLOAD-LOG.md). It does not crawl the site, guess URLs or bypass a login. [Import status](IMPORT-STATUS.md) distinguishes downloaded-only, converted-only and reviewed extractions. Duplicate downloads and archival filenames are preserved rather than deleting originals.

## Complete the library extraction

1. Read each converted programme against its original PDF. Check it is Cub content and inspect instructions, links and required attachments.
2. Search the shared libraries for existing elements. Reuse a matching canonical entry and record a separately attributed variant when needed; otherwise create a source-based entry in the appropriate shared library.
3. Record runnable instructions supplied by the source, timing, equipment, source/page references, tags, advancement limits and visual references. Label safety guidance and adaptations separately. Keep incomplete named activities as flagged references; do not invent missing rules or teaching content.
4. Keep transitions and source-Pack opening, inspection, scoring and closing details in the original programme. Extract genuine standalone source yarns, not connective snippets.
5. Update the catalogue's programme-to-element coverage table, including source-only exclusions. Rebuild the source-neutral indexes using the commands in the [resource guide](../RESOURCE-GUIDE.md).
6. Run `python scripts/build_scouts_digital_status.py`, then `python scripts/check_scouts_digital_resources.py` from the repository root. These distinguish pending downloads from completed conversions, check converted-source hashes/page sections, and validate extracted-entry fields/tags, catalogue coverage, index membership and local file links without PDF software or a login. Report pending conversion/extraction separately; a successful check does not mean every downloaded file is fully imported.

Planning uses the already extracted Markdown directly. The importer and maintenance checks are needed only when adding or changing resources.

## Bulk extraction and maintenance

The [bulk coverage catalogue](BULK-PROGRAMMES.md) accounts for the remaining 160 source files, including byte-identical copies. All 175 originals have archival conversions. Bulk parsing is distinct from independent review of every activity: incomplete references, clinical instruction and source visuals retain explicit review flags. See [source quality notes](SOURCE-QUALITY.md).

`extract_scouts_digital.py` scans source tables into a draft under `.tools/`; it requires the conversion dependencies. The shared `BULK-EXTRACTION-DATA.json` preserves source records and visual-review additions. Do not replace this reviewed data directly with a raw scan. `python scripts/build_scouts_digital_bulk.py` rebuilds the library entries and coverage from that shared data using the standard library. It protects manually edited generated entries and records canonical reuse separately. Rebuild the four source-neutral indexes afterwards, then run the status builder and resource checker. Planning from a clone requires neither these import dependencies nor a Scouts Digital account.
