#!/usr/bin/env python3
"""Download only user-listed Scouts Digital documents, sequentially and slowly.

No login, crawling, URL guessing, concurrent requests or automatic retries.
Existing valid originals (including nested files) are preserved and skipped.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/scouts-digital'
PREFIX = 'https://ssa.scouts.digital/uploadedFiles/'
PATTERN = r'Program_Doc_ID_\d+_\d+_\d{4}-\d{2}-\d{2}\.(?:pdf|docx|doc|xlsx)'


def fetch(url: str, target: Path) -> bytes:
    if sys.platform != 'win32':
        with urllib.request.urlopen(url, timeout=45) as response:
            if response.geturl().split('/uploadedFiles/')[0] != PREFIX.split('/uploadedFiles/')[0]:
                raise ValueError('Unexpected redirect outside source site')
            return response.read()
    # Use Windows' standard HTTP client, as for the verified single download.
    # No browser impersonation, credentials, cookies or security bypass settings.
    temporary = target.with_name(target.name + '.download-part')
    if temporary.exists():
        raise FileExistsError(f'Partial file already exists: {temporary.name}')
    quote = lambda value: "'" + str(value).replace("'", "''") + "'"
    command = "$ErrorActionPreference='Stop'; try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 45 -Uri " + quote(url) + ' -OutFile ' + quote(temporary) + " } catch { if ($_.Exception.Response) { [Console]::Error.WriteLine('HTTP ' + [int]$_.Exception.Response.StatusCode) } else { [Console]::Error.WriteLine($_.Exception.Message) }; exit 1 }"
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], capture_output=True, text=True, timeout=55, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            message = result.stderr.strip()
            match = re.search(r'HTTP (\d+)', message)
            if match:
                raise urllib.error.HTTPError(url, int(match.group(1)), message, {}, None)
            raise RuntimeError(message[:400])
        return temporary.read_bytes()
    finally:
        if temporary.exists():
            temporary.unlink()


def valid(data: bytes, suffix: str) -> bool:
    if suffix == '.pdf':
        return data[:1024].lstrip().startswith(b'%PDF-') and b'%%EOF' in data[-2048:]
    if suffix == '.doc':
        return data.startswith((b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', b'{\\rtf'))
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            member = 'word/document.xml' if suffix == '.docx' else 'xl/workbook.xml'
            return member in archive.namelist() and archive.testzip() is None
    except (zipfile.BadZipFile, OSError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interval', type=float, default=5.0)
    args = parser.parse_args()
    if args.interval < 5:
        parser.error('Use at least five seconds between requests for this queue')
    filenames = list(dict.fromkeys(re.findall(PATTERN, (BASE / 'DOWNLOAD-QUEUE.md').read_text(encoding='utf-8'))))
    source = BASE / 'src'
    source.mkdir(parents=True, exist_ok=True)
    log = BASE / 'DOWNLOAD-LOG.md'
    if not log.exists():
        log.write_text('# Scouts Digital download log\n\nFiles are originals, not completed library extractions. Existing-file rows record a user-supplied URL associated by exact filename; no new request was made.\n\n| UTC time | Status | Source URL | Local file | Bytes | SHA-256 / result |\n| --- | --- | --- | --- | --- | --- |\n', encoding='utf-8')
    downloaded = skipped = failed = 0
    last_request = None
    print(f'Queue: {len(filenames)} unique documents; interval {args.interval}s; destination {source}', flush=True)
    for index, filename in enumerate(filenames, 1):
        url = PREFIX + filename
        matches = sorted(source.rglob(filename))
        existing = next((path for path in matches if path.is_file() and valid(path.read_bytes(), path.suffix.lower())), None)
        target = existing or source / filename
        status, data, note = 'EXISTING', b'', ''
        if existing:
            data = existing.read_bytes()
            skipped += 1
        else:
            if target.exists():
                status, note = 'FAILED', 'Existing invalid file preserved; not overwritten'
                failed += 1
            else:
                if last_request is not None:
                    time.sleep(max(0, args.interval - (time.monotonic() - last_request)))
                last_request = time.monotonic()
                try:
                    data = fetch(url, target)
                    if not valid(data, target.suffix.lower()):
                        raise ValueError('Response is not a valid document of the requested type')
                    with target.open('xb') as stream:
                        stream.write(data)
                    status = 'DOWNLOADED'
                    downloaded += 1
                except urllib.error.HTTPError as exc:
                    status, note = 'FAILED', f'HTTP {exc.code}'
                    failed += 1
                    if exc.code in {401, 403, 429}:
                        note += '; stopped without retrying or bypassing'
                except Exception as exc:
                    status, note = 'FAILED', f'{type(exc).__name__}: {exc}'
                    failed += 1
        digest = hashlib.sha256(data).hexdigest() if status != 'FAILED' else note
        local = target.relative_to(BASE).as_posix()
        stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
        with log.open('a', encoding='utf-8') as stream:
            stream.write(f'| {stamp} | {status} | [{filename}]({url}) | [{filename}](<{local}>) | {len(data) if status != "FAILED" else ""} | {digest.replace(chr(124), "/")} |\n')
        print(f'[{index}/{len(filenames)}] {status} {filename}' + (f' — {note}' if note else ''), flush=True)
        if 'stopped without' in note:
            break
    print(f'Finished: {downloaded} downloaded, {skipped} existing, {failed} failed. Log: {log}', flush=True)
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
