# Find and reuse Cub programme resources

Start here when planning from AiKELA's shared collection. A clone contains searchable Markdown libraries and programme references: reading and planning do not require Python, conversion software or a Scouts Digital login. Some source items lack attachments or complete instructions; check the selected entry before putting it into a meeting plan.

## Start with your Pack

Copy the [Pack profile template](../PACK-PROFILE-TEMPLATE.md) to `packs/<your-pack>/PACK-PROFILE.md`. Record meeting length, routine, Sixes, calendar, reward system and planning priorities. Add your programme template if available. Keep year plans, term plans, meeting plans and local visuals in that Pack folder. The existing 1st Pinelands folder is a separate Pack's example, not a default to inherit.

## Search across the collection

| Need | Starting point |
| --- | --- |
| Games, relays and sense training | [Games catalogue](games/GAMES-INDEX.md) |
| Standalone sourced stories | [Yarns catalogue](yarns/YARNS-INDEX.md) |
| Crafts and construction | [Crafts catalogue](crafts/CRAFTS-INDEX.md) |
| Work sessions, skills, singing, dancing and other activities | [Activities catalogue](activities/ACTIVITIES-INDEX.md) |
| Full historical POP programme context | [POP programme catalogue](pop/PROGRAMME-DRAFT-INDEX.md) and `pop/programmes/` |
| Imported Scouts Digital programmes and extraction coverage | [Scouts Digital programme catalogue](scouts-digital/PROGRAMMES-INDEX.md) |
| Scouts Digital files still awaiting conversion or extraction | [Import status](scouts-digital/IMPORT-STATUS.md) |
| Exact advancement wording and practice links | [Advancement guide](advancements/README.md), [Silver Wolf](advancements/silver-wolf/INDEX.md), [Gold Wolf](advancements/gold-wolf/INDEX.md) |
| Website scope and provenance | [Website resources](WEB-RESOURCES.md) |

Search titles, tags, skills, equipment and potential themes. A game filed under one theme may fit another with an adaptation. Search complete programme text too: older entries may have weak tags, and source attachments may contain more detail. Source-neutral catalogues include all sources; POP-only indexes are not the full library.

Programme planning usually centres on a few verified challenge or interest badge requirements, with a familiar theme creating the adventure around them. Keep the underlying skill and activity mechanics separate from the theme: sourced compass and mapping activities could become a Pokémon tracking expedition, for example. Reuse the same activity across different themes when it fits, preserving its source, learning objective, requirement conditions and safety instructions. Identify the themed adaptation rather than treating it as an unrelated new game.

Linking sentences carry that adventure forward and explain why Cubs undertake the next activity. These programme-specific passages may be generated and belong in the run sheet where they are read. Substantive games, teaching sessions and standalone yarns must still come from existing sources or adaptations; theme changes do not justify inventing missing instructions.

The Scouts Digital extractions use `#source-scouts-digital` plus theme/skill/type tags such as `#knots`, `#hanking`, `#hearing`, `#masks` and `#home-safety`. Provenance and practice tags do not mean a Cub has earned badge credit.

## Turn sources into year, term and meeting plans

1. Read `AGENTS.md` and only the supported Pack's profile. Establish its calendar, planning cycle and priorities for year/term plans. Do not invent dates or turn required tasks into optional choices.
2. Verify advancement against authoritative supplied SSA material. The latest Cub Trail available here is [November 2019](The-Cub-Trail-Nov-19.pdf); use it where historical sheets or programme claims differ.
3. Source games, crafts, skills, work sessions, songs, playacting and standalone yarns from existing elements and complete imported programmes. Reuse or adapt them to the meeting theme. If no suitable source exists, flag the gap or find another source; do not invent a substantive element without an explicit user exception.
4. Read the selected element and its source. Check instructions, equipment, timing, missing attachments, safety and the exact limits of any advancement link. Resolve `#reference-only`, `#needs-instructions`, missing templates and teaching materials before running the affected item.
5. Identify adaptations clearly: retain the sourced mechanic and say what changes, such as using another set of animal calls in Animal Sounds. Adapting a game to revise another topic requires checked questions and answers, not an invented external origin or assumed badge credit.
6. Generate connective story passages and transitions when needed for the chosen meeting. Keep them at their read-aloud positions in that Pack's programme and label newly written text. Original transitions remain only in their source programme; do not add them to the shared yarn library or turn them into a standalone yarn.
7. Apply your Pack's template, routine, leader assignments and reward system. Another Pack's marbles or bones used as reward counters become your selected counters; actual game equipment remains equipment. Keep complete runnable instructions and necessary visuals with the meeting plan.
8. Record which substantive elements were reused or adapted and their sources. Track exact verified requirements and opportunities across year/term plans; programme participation does not automatically sign off advancement.

## Example request for an assistant

> Read `AGENTS.md`, `docs/RESOURCE-GUIDE.md` and `packs/my-pack/PACK-PROFILE.md`. Help me create a year, term or meeting plan using ideas from all supplied programme sources. Search the shared catalogues and complete programmes. Reuse or adapt substantive elements with attribution; only connective story passages may be newly generated. Check missing instructions and visuals, verify advancement against the supplied SSA documents, and keep my Pack's details in its folder.

Replace the Pack path and specify the planning period, theme or known constraints.

## Adding more sources

Preserve originals, create source-linked conversions, then extract and tag reusable elements. A text conversion alone is not an extracted library. Search for a canonical entry before creating duplicates; record source-specific variants with their own provenance. Maintain a coverage table linking each substantial source element to its library entry or explaining why it remains source-only. Preserve incomplete source items as labelled references. Transitions, local ceremonies, inspection rewards and named badge awards stay in the original programme.

For Scouts Digital, see its [import instructions](scouts-digital/README.md). Refresh the four source-neutral catalogues after library changes:

```sh
python scripts/build_game_index.py
python scripts/build_yarn_index.py
python scripts/build_craft_index.py
python scripts/build_activity_index.py
```

These maintenance tools are optional for using existing resources. The originals and archival conversions remain unchanged when a library entry is adapted. Missing visuals must be recovered from permitted sources or resolved by a labelled adaptation before use; a link in a conversion does not mean an image is included. Check attribution and reuse terms before publishing source material.
