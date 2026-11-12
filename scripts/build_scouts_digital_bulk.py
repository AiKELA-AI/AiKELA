#!/usr/bin/env python3
"""Build source-based library extractions and coverage from reviewed scan data.

No story, game rule, badge requirement or missing worksheet is generated. Source
text remains quoted; exact text duplicates share one entry. Existing-library
reuse requires an explicit mapping or strong matching instruction text.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

from extract_scouts_digital import THEMES, classify, clean, entry_title, norm

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/scouts-digital'
DATA = BASE / 'BULK-EXTRACTION-DATA.json'
MARKER = '<!-- Scouts Digital bulk provenance: start -->'
END_MARKER = '<!-- Scouts Digital bulk provenance: end -->'
TYPE_TAG = {'games': 'game', 'activities': 'activity', 'crafts': 'craft', 'yarns': 'yarn'}
GENERIC = {'game', 'yarn', 'activity', 'activities', 'advancement', 'advancements', 'instruction', 'instructions', 'bases', 'topic', 'silver wolf', 'gold wolf', 'silver wolves', 'gold wolves', 'silver gold wolf', 'sw', 'gw', 'new', 'day start', 'close', 'time', 'min', 'minutes'}
SOURCE_ONLY = re.compile(r'^(?:linking\s*sentence|report\s*in|cubs?\s*arriv|set\s*up\s*flag|prepare\s*flag|meeting\s*briefing|allocate\s*new|hot\s*chocolate|hotdogs?\b|lunch\b|snack\b|juice\b|recap\s*and\s*wrap|clean.?up\b|cleaning\s*up|sixer\s*boxes|switch\s*urn|parents\s*behind|invest\w*\b|adult\s*investiture|burrowing\s*up|.*going\s*up\s*ceremony|take\s*home\s*tasks|return\s*via\b|cubs\s*to\s*bring|.*log\s*books|combined\s*campfire\s*with\s*scouts)', re.I)
STORY_LINK = re.compile(r'^(?:[“"\s]*(?:Tonight[, ]|We.ve arrived|Two weeks ago|A great storm swept|Cubs - mission|At last,|The Queen has gone|Our clever cubs)|Short Story\s*[–—:-]|A pen pal is a friend|Thank you)', re.I)
MANUAL_REUSE = {
    'beware the sabertooth': 'games/beware-the-sabertooth.md',
    'darkness into the sunlight': 'games/darkness-into-sunlight.md',
    'go fly a kite': 'yarns/go-fly-a-kite.md',
    'tails': 'games/tails.md',
    'chain tag': 'games/chain-tag.md',
    'if you re happy': 'activities/if-you-re-happy.md',
    'my bonny lies over the ocean': 'activities/my-bonnie-lies-over-the-ocean.md',
    'my bonnie lies over the ocean': 'activities/my-bonnie-lies-over-the-ocean.md',
    'the queen s royal commands': 'games/queens-coming-commands.md',
    'the queens royal commands': 'games/queens-coming-commands.md',
    'be water safe tags': 'crafts/be-water-safe-tags.md',
    'a day at the beach or swimming pool': 'games/beach-bag-memory-circle.md',
    'a day at the beach': 'games/beach-bag-memory-circle.md',
    'active game plan': 'games/plan-mime-command-game.md',
    'learn safe ways by making a plan': 'activities/plan-water-safety-discussion.md',
    'the newspaper kite': 'crafts/the-newspaper-kite.md',
    'newspaper kites': 'crafts/the-newspaper-kite.md',
    'floating feather kite': 'games/floating-feather-kite-the-object-of.md',
    'finding kevin s chicks': 'games/finding-kevin-s-chicks-the.md',
    'stop drop and roll': 'games/stop-drop-and-roll.md',
    'out on a lion hunt': 'activities/out-on-a-lion-hunt.md',
    'the life of a super hero': 'yarns/the-life-of-a-super-hero.md',
    'bean planting': 'games/bean-planting.md',
    'plan': 'games/plan-mime-command-game.md',
}


def stripped_title(value):
    value = re.sub(r'^(?:Activity\s*\d+\s*[:–—-]\s*)', '', value, flags=re.I)
    value = re.sub(r'^(?:steam\s*release(?:\s*game)?|(?:active|relay|circle|quiet|revision|team|round)\s*(?:game|yarn)|game|yarn|singing|campfire song|handcraft|craft)\s*[:–—-]*\s*', '', value, flags=re.I)
    return norm(value).strip()


def disposition(item):
    title = item['title']
    first = re.sub(r'^Activities?\s*:\s*', '', title, flags=re.I)
    first = re.sub(r'^Activity\s*\d+\s*[:–—-]\s*', '', first, flags=re.I)
    body = item['activity']
    if SOURCE_ONLY.match(first) or re.search(r'springbok\s*award|going\s*up\s*ceremony|^.*investiture|\blog\s*books?\b', first, re.I):
        return 'source-only Pack administration/presentation record'
    if STORY_LINK.match(first):
        return 'programme-specific transition/story snippet; not a shared yarn'
    if re.search(r'\bmeerkats?\b|\brovers?\b', body, re.I):
        return 'mixed-branch source text held in programme; isolate Cub-only content before reuse'
    if norm(first).strip() in GENERIC or not re.search(r'[A-Za-z]', first):
        return 'generic heading only; no isolated reusable element identified'
    if re.match(r'^(?:opening|closing|tidy|notices|badges|break|water break|prayer)\b', first, re.I):
        return 'source-only meeting routine'
    if len(body.split()) <= 1:
        return 'bare topic/worksheet fragment; retained only in source'
    if len(body.split()) < 8 and not item.get('tags') and not re.search(r'game|yarn|craft|sing|play.?act|charades', first, re.I):
        return 'short record/reference without reusable instructions; retained only in source'
    if re.match(r'^Task\s*\d+|^\(?assigned\b|^\d+[.)]\s', first, re.I) and not item.get('time'):
        return 'programme-wide advancement/checklist note; not an isolated activity'
    return ''


def flags_for(item):
    body = item['activity']
    flags = set()
    if len(body.split()) < 25:
        flags.update({'reference-only', 'needs-source-detail'})
    if re.search(r'first.?aid|recovery position|stop.*bleed|treat.*(?:wound|burn|cut|sting)|CPR|splinter|nosebleed|clinical|poison', body, re.I):
        flags.update({'reference-only', 'needs-qualified-instruction'})
    if re.search(r'\b(?:dive|diving|swim|axemanship|axe|knife|saw|hot wax|fire.?lighter|fire.?lighting|light.*fire|light.*candle)\b|pull.*(?:over|drag)|carry.*(?:cub|patient)', body, re.I):
        flags.add('needs-safety-review')
    if re.search(r'template|worksheet|sheet|picture|diagram|card|attached|see below|see instructions|see resources', body + ' ' + item['equipment'], re.I):
        flags.add('check-visuals')
    if '\ufffd' in body:
        flags.add('check-source-text')
    return flags


def shingle(value):
    words = norm(value).split()
    return {' '.join(words[i:i + 5]) for i in range(max(0, len(words) - 4))}


def source_links(document, item, parent='..'):
    original = f'{parent}/scouts-digital/src/{quote(document["source"], safe="/")}'
    conversion = f'{parent}/scouts-digital/source-conversions/{quote(document["source"] + ".md", safe="/")}'
    pages = sorted({int(page) for value in item['locations'] for page in re.findall(r'PDF p\. (\d+)', value)})
    if pages:
        original += f'#page={pages[0]}'
        conversion += f'#page-{pages[0]}'
    return original, conversion, pages


def variant(document, item):
    original, conversion, pages = source_links(document, item)
    locations = '; '.join(dict.fromkeys(item['locations']))
    title = clean(item['title']).replace('\n', ' ')
    text = item['activity'].rstrip()
    fence = '`' * max(3, max((len(x) for x in re.findall(r'`+', text)), default=0) + 1)
    method = item.get('extraction_method', 'Source text extracted from timetable cells; compare layout with original.')
    return f'''### {document['source']} — {title}

**Reuse status:** Reused source text, extracted from {locations}. Timing: {item.get('time') or 'not stated'}; duration: {item.get('minutes') or 'not separately stated'}. These are source timings, not defaults for another Pack.

**Extraction:** {method}

**Variant preparation flags:** {', '.join(item.get('flags', [])) or 'Compare source and equipment before adapting.'}

**Source equipment:** {item['equipment'] or 'Not separately stated in this source row; inspect the original.'}

{fence}text
{text}
{fence}

[Original](<{original}>) · [Archival conversion](<{conversion}>)
'''


def write_owned(path, body):
    digest = hashlib.sha256(body.encode('utf-8')).hexdigest()
    if path.exists():
        current = path.read_text(encoding='utf-8')
        match = re.match(r'<!-- SD generated sha256: ([0-9a-f]{64}) -->\n', current)
        if not match or hashlib.sha256(current[match.end():].encode('utf-8')).hexdigest() != match.group(1):
            raise ValueError(f'Refusing to overwrite a manually edited library entry: {path}')
    path.write_text(f'<!-- SD generated sha256: {digest} -->\n' + body, encoding='utf-8')


def main():
    documents = json.loads(DATA.read_text(encoding='utf-8'))
    existing = []
    for folder in TYPE_TAG:
        for path in (ROOT / 'docs' / folder).glob('*.md'):
            if 'INDEX' in path.name or path.name.startswith('sd-'):
                continue
            content = path.read_text(encoding='utf-8')
            title = re.search(r'^# (.+)', content, re.M)
            instructions = content.split('## Instructions', 1)[-1].split('## Advancement', 1)[0]
            if title:
                existing.append((path.relative_to(ROOT / 'docs').as_posix(), norm(title.group(1)), shingle(instructions)))
    targets = {}
    exact = {}
    count = Counter()
    source_aliases = {}
    for document in documents:
        if document.get('duplicate_of'):
            source_aliases[document['source']] = document['duplicate_of']
            continue
        if not document.get('cub_evidence'):
            document['disposition'] = 'Cub branch not confirmed; source-only pending review'
            continue
        for item in document['records']:
            excluded = disposition(item)
            if excluded:
                item['disposition'] = excluded
                count['source-only rows'] += 1
                continue
            title_key = stripped_title(item['title'])
            target = None
            basis = ''
            for label, path in MANUAL_REUSE.items():
                if title_key == label or title_key.startswith(label + ' ') or len(label) >= 16 and title_key.endswith(label):
                    if (ROOT / 'docs' / path).exists():
                        target, basis = path, 'reviewed source-title/mechanic match; source variant retained separately'
                        break
            pieces = shingle(item['activity'])
            if target is None and len(pieces) >= 12:
                ranked = []
                for path, title, old_pieces in existing:
                    score = len(pieces & old_pieces) / max(1, min(len(pieces), len(old_pieces)))
                    if score >= .88 and SequenceMatcher(None, title_key, title).ratio() >= .62:
                        ranked.append((score, path))
                if ranked:
                    target, basis = max(ranked)[1], 'matching source instruction shingles and title; source variant retained separately'
            signature = norm(item['activity'])
            if target is None and len(signature) > 40 and signature in exact:
                target, basis = exact[signature], 'identical normalised source instructions; one entry with separate source attributions'
            if target is None:
                folder = item['folder']
                if re.search(r'\btag\b|soccer|hockey|tug.of.war|charades|simon.says|\bmancala\b', item['title'], re.I):
                    folder = 'games'
                slug = re.sub(r'[^a-z0-9]+', '-', norm(item['title'])).strip('-')[:75]
                suffix = hashlib.sha256(item['id'].encode()).hexdigest()[:8]
                target = f'{folder}/sd-{slug}-{suffix}.md'
                basis = 'source-based standalone extraction after searching existing library titles/instructions'
                count['new standalone entries'] += 1
            else:
                count['reused entries/variants'] += 1
            exact[signature] = target
            item['target'] = target
            item['match_basis'] = basis
            item['flags'] = sorted(flags_for(item))
            targets.setdefault(target, []).append((document, item))

    # A new scan can withdraw an earlier match. Remove its managed provenance
    # instead of leaving source tags and citations without programme coverage.
    for folder in TYPE_TAG:
        for old in (ROOT / 'docs' / folder).glob('*.md'):
            if old.relative_to(ROOT / 'docs').as_posix() in targets:
                continue
            content = old.read_text(encoding='utf-8')
            if MARKER in content and END_MARKER in content:
                start = content.index(MARKER)
                stop = content.index(END_MARKER, start) + len(END_MARKER)
                content = content[:start] + content[stop:]
                if 'scouts-digital/' not in content:
                    content = content.replace('#source-scouts-digital', '').replace('#source-extracted', '')
                old.write_text(content.rstrip() + '\n', encoding='utf-8')

    for target, uses in targets.items():
        path = ROOT / 'docs' / target
        folder = path.parent.name
        tags = {TYPE_TAG[folder], 'source-scouts-digital', 'source-extracted'}
        flags = set()
        for document, item in uses:
            tags.update(item['tags'])
            flags.update(item['flags'])
        tags.update(flags)
        if len(tags) < 4:
            tags.add('programme-resource')
        variants = '\n\n'.join(variant(document, item) for document, item in uses)
        if path.name.startswith('sd-'):
            title = uses[0][1]['title'].replace('|', '—').strip()
            review = ('**Reference only:** Resolve the source detail/qualified-instruction flags before scheduling this as a complete activity.' if 'reference-only' in flags else '**Source instructions extracted:** Compare the source row and any supporting attachments before adapting it into a meeting plan.')
            preparation = ['Use the selected Pack profile for rewards, Sixes and leader assignments; identify any retheming or adaptation.']
            if 'needs-qualified-instruction' in flags:
                preparation.append('Obtain checked current first-aid teaching and a competent instructor before using the treatment/first-aid content; source text is retained for traceability.')
            if 'needs-safety-review' in flags:
                preparation.append('Review the actual fire, tool, water or physical-contact setup and supervision before choosing this activity.')
            if 'food' in tags:
                preparation.append('Check food suitability, dietary needs and hygiene before preparing or tasting food.')
            if 'check-visuals' in flags:
                preparation.append('Inspect the named worksheet/card/template or demonstration in the source; resolve any missing material before the meeting.')
            body = f'''# {title}

## Type

{TYPE_TAG[folder].capitalize()} — source-based extraction. The heading is the source heading or its first line, not an invented official activity name.

## Equipment

See the separately attributed source variants below. Source quantities, Six colours, venue references and reward counters require adaptation to the selected Pack profile.

## Instructions

{review}

The extracts below are source text or explicitly identified summaries/transcriptions, not newly invented rules or verified SSA requirements. Programme-specific transitions stay with their original programme. Resolve missing steps, recipes, scripts or worksheets from actual sources.

{variants}

## Preparation and safety

{' '.join(preparation)}

## Advancement / badge link

No current badge credit has been verified by this mechanical extraction. Any task numbers, badge labels, distances, scores or conditions inside a source quotation remain that source's claims. Check the full applicable SSA wording in the supplied authoritative material before planning assessment. Do not attach unrelated programme-wide targets or treat participation as sign-off.

## Visual aid / image reference

The original and archival-conversion links above identify the actual source pages/tables. PDF conversions retain page images; DOCX/XLSX conversions retain embedded source media; legacy DOC text does not extract diagrams. A mention of a card, worksheet, map, picture or template does not establish that a separate printable was supplied. Inspect the linked source visuals and resolve required attachments before use; no new visual or missing instructional content has been invented.

## Tags

{' '.join('#' + tag for tag in sorted(tags))}

## Source

Reused from the user-supplied Scouts Digital documents cited individually above. Source-level facts, authorship and dates are not inferred from leader assignments or filenames. Exact supplied download URLs are recorded in [the download log](../scouts-digital/DOWNLOAD-LOG.md); originals and conversions remain unchanged. Multiple source uses do not imply that one originated from another.
'''
            write_owned(path, body)
        else:
            text = path.read_text(encoding='utf-8')
            # Add provenance without replacing hand-written canonical instructions.
            addition = f'''{MARKER}
## Additional Scouts Digital source uses

The existing canonical element is reused for the matching source-based variants below. Source text is separately attributed; these are not new AI-created games or official SSA rules. Compare differences before adapting. Source-only rewards/leader assignments do not replace the selected Pack profile. Short references and safety-critical teaching still need their source detail checked.

{variants}
{END_MARKER}'''
            if MARKER in text:
                text = text[:text.index(MARKER)].rstrip() + '\n\n' + addition + '\n'
            else:
                text = text.rstrip() + '\n\n' + addition + '\n'
            if '## Equipment' not in text:
                text = text.replace('## Instructions', '## Equipment\n\nSee the original instructions and separately attributed variants below.\n\n## Instructions', 1)
            if not re.search(r'^## Advancement(?: covered)? / badge link', text, re.M):
                text += '\n## Advancement / badge link\n\nNo badge credit verified for the additional source uses; assess the complete official requirement.\n'
            if '## Visual aid / image reference' not in text:
                text += '\n## Visual aid / image reference\n\nInspect the individually linked original pages and conversions for visuals; no missing printable is implied to be included.\n'
            section = re.search(r'^## Tags\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
            if section:
                old_tags = set(re.findall(r'#[a-z0-9-]+', section.group(1)))
                if '../pop/' in text:
                    old_tags.add('#source-pop')
                values = old_tags | {'#' + tag for tag in tags - flags}
                text = text[:section.start(1)] + ' '.join(sorted(values)) + '\n\n' + text[section.end(1):]
            path.write_text(text.rstrip() + '\n', encoding='utf-8')

    # Remove only unchanged, marker-owned outputs superseded by canonical reuse.
    # Refuse to remove anything edited by a Scouter or outside these libraries.
    wanted = {str((ROOT / 'docs' / target).resolve()) for target in targets}
    for folder in TYPE_TAG:
        library = (ROOT / 'docs' / folder).resolve()
        for path in library.glob('sd-*.md'):
            if str(path.resolve()) in wanted:
                continue
            current = path.read_text(encoding='utf-8')
            owner = re.match(r'<!-- SD generated sha256: ([0-9a-f]{64}) -->\n', current)
            if owner and path.resolve().parent == library and hashlib.sha256(current[owner.end():].encode('utf-8')).hexdigest() == owner.group(1):
                path.unlink()

    lines = ['# Bulk Scouts Digital programme coverage', '',
             'Source-table extraction with library search and separately attributed reuse. This is parsing/coverage, not a claim that every instruction, badge link, language fact or safety statement has been validated. Scouter review flags remain visible in each entry. Transitions and local administration stay in the original programme. All originals and conversion page images remain available.', '',
             '[Import status](IMPORT-STATUS.md) · [Source quality and review notes](SOURCE-QUALITY.md) · [Extraction data](BULK-EXTRACTION-DATA.json)', '']
    for document in documents:
        source = document['source']
        lines += [f'## {source}', '', f"**Source heading:** {document.get('title') or 'See original'}", '',
                  f'[Original](<src/{quote(source, safe="/")}>) · [Conversion](<source-conversions/{quote(source + ".md", safe="/")}>)', '']
        if document.get('duplicate_of'):
            lines += [f"**Duplicate:** Byte-identical to `{document['duplicate_of']}`. Original preserved; reuse that programme's extraction rather than creating duplicate elements.", '']
            continue
        if not document.get('cub_evidence'):
            lines += ['**Held:** Cub branch not confirmed. Source preserved; no branch-specific requirements or reusable entries inferred.', '']
            continue
        lines += ['| Source element | Location | Library entry / disposition |', '| --- | --- | --- |']
        for item in document['records']:
            label = item['title'].replace('|', '/').replace('\n', ' ')
            location = '; '.join(item['locations']).replace('|', '/')
            if item.get('target'):
                target = item['target']
                value = f'[{label}](../{target}) — {item["match_basis"]}'
            else:
                value = item.get('disposition', 'Source-only; review needed')
            lines.append(f'| {label} | {location} | {value} |')
        if not document['records']:
            lines.append('| No timetable rows isolated | Whole source | Retained worksheet/reference; see source quality notes |')
        lines += ['', f"**Source-only rows:** {len(document.get('excluded', []))} routine, transition, untimed-note or non-timetable rows remain in the programme. Supporting/worksheet material stays linked from the conversion; an unisolated attachment is not described as missing.", '']
    (BASE / 'BULK-PROGRAMMES.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    DATA.write_text(json.dumps(documents, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    print(dict(count))
    print(f'{len(targets)} distinct shared library targets; {len(documents)} source files accounted for.')


if __name__ == '__main__':
    main()
