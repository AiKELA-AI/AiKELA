# AiKELA: a Cub Scouting knowledge base for South Africa

AiKELA is a shared, growing collection of Scouts South Africa (SSA) Cub resources, activity ideas and planning examples. It is intended to help Pack Scouters find trustworthy source material and build useful year, term and meeting plans with an AI assistant.

You do not need to be a programmer to use the knowledge files. The simplest way to begin is to download the repository and ask an AI tool that can read local files to work with it.

> **Source and licensing:** Some files are transcribed or adapted from SSA and ScoutWiki resources. Check the original source and its reuse terms before republishing source documents. The repository does not currently state a project-wide licence; contributors should not assume that every file is freely redistributable. Please retain source names, dates and links.

## What is in this repository?

| Location | Contents |
| --- | --- |
| `AGENTS.md` | Canonical shared instructions for AiKELA, including source authority and SSA accuracy requirements. |
| `CLAUDE.md` | Entry point for Claude Code; points to the shared instructions in `AGENTS.md`. |
| `GEMINI.md` | Gemini CLI compatibility note pointing to the canonical instructions in `AGENTS.md`. |
| `PACK-PROFILE-TEMPLATE.md` | Starter file for your own Pack's local arrangements. |
| `packs/` | Pack-specific profiles, templates, year/term planners and programmes, kept separate from shared resources. |
| `packs/1st-pinelands/` | Example Pack folder. Do not use its local details for another Pack. |
| `docs/` | Shared knowledge base, badge material, POP programmes and extracted activity libraries. |
| `docs/pop/` | Programme on a Plate Markdown references. |
| `docs/pop/src/` | Local original POP files used during conversion. Binary source files are excluded from the Markdown-only GitHub upload; Markdown entries keep the source filename and link to the ScoutWiki resource page. |
| `docs/games/`, `docs/yarns/`, `docs/crafts/`, `docs/activities/` | Growing libraries extracted from programmes, with source references where available. |
| `docs/games/GAMES-INDEX.md`, `docs/yarns/YARNS-INDEX.md` | Source-neutral catalogues for finding reusable games and yarns. |
| `docs/crafts/CRAFTS-INDEX.md`, `docs/activities/ACTIVITIES-INDEX.md` | Source-neutral catalogues for finding reusable crafts and activities. |
| `packs/<pack-slug>/templates/` | A Pack's own programme template, when supplied. |
| `packs/<pack-slug>/planners/` | Pack-specific year and term plans. |
| `packs/<pack-slug>/programmes/` | Pack-specific meeting programmes and exports. |
| `scripts/` | POP conversion, catalogue generation, review and PDF export tools. |

The knowledge base is for South African Cub Scouting. Official SSA sources are the authority for requirements. An activity idea or an AI suggestion must not be presented as an official badge requirement.

## Getting started

### 1. Install Git and download a copy

**On Mac:** Open **Terminal** and check whether Git is installed:

```sh
git --version
```

If macOS prompts you to install command-line developer tools, follow the prompt. You can also use the [official Git for macOS options](https://git-scm.com/install/mac).

**On Windows:** Install [Git for Windows](https://git-scm.com/install/windows), then open **Git Bash** from the Start menu.

**On both Mac and Windows:** Clone the repository in the terminal (Terminal on Mac, Git Bash on Windows):

```sh
git clone https://github.com/ron-tuffin/aikela.git
cd aikela
```

If you do not want to use a terminal, GitHub's **Code → Download ZIP** option downloads a copy, but it is less convenient for receiving updates or contributing changes.

### Optional: open and preview the Markdown files

**[Visual Studio Code](https://code.visualstudio.com/)** is a free editor that shows formatted Markdown as you type. It renders the preview in the document itself rather than in a separate pane. You can also read the files directly on GitHub without installing an editor.

### 2. Install one AI assistant

Choose one assistant below. These command-line tools work on both Mac and Windows, though Windows may require Git Bash or PowerShell depending on the tool. Each provider may require an account, subscription or billing arrangement. Check the provider's current terms before signing in.

**On both Windows and Mac:** Install [Node.js](https://nodejs.org/) if needed, then use the same npm command for Gemini CLI or Codex. Run the command in Terminal on Mac or Git Bash/PowerShell on Windows.

#### Gemini CLI

Install Gemini CLI:

```sh
npm install -g @google/gemini-cli
```

From inside the repository folder, start it with:

```sh
gemini
```

Follow its sign-in prompts. See Google's [Gemini CLI installation guide](https://github.com/google-gemini/gemini-cli) for current options and requirements.

#### OpenAI Codex CLI

Install Codex CLI:

```sh
npm install -g @openai/codex
```

From inside the repository folder, start it with:

```sh
codex
```

Follow the sign-in prompts. See the [Codex CLI documentation](https://developers.openai.com/codex/cli) for current setup instructions.

#### Claude Code

**On both Windows and Mac:** With Node.js installed, install Claude Code using npm:

```sh
npm install -g @anthropic-ai/claude-code
```

On Windows, use Git Bash or WSL if required by your setup. See Anthropic's [Claude Code setup guide](https://docs.anthropic.com/en/docs/claude-code/getting-started) for platform details and alternatives.

From inside the repository folder, start it with:

```sh
claude
```

Follow the sign-in prompts.

> **Already use another tool?** You can use any assistant that can read the files in this folder and follow project instructions. Check that it supports repository-level instruction files. `AGENTS.md` is the canonical guidance; small compatibility files point Gemini CLI and Claude Code to it.

### 3. Tell the assistant which Pack you are planning for

In the assistant's project session, try:

> Please read `AGENTS.md` and the profile at `packs/my-pack/PACK-PROFILE.md`. Help me plan a Cub meeting using the shared SSA resources in `docs/`. Show which source supports each badge requirement, and label any new ideas as suggestions.

Replace `packs/my-pack/PACK-PROFILE.md` with your Pack's profile path. For a year or term plan, say which year/term and any dates, ages, meeting constraints or badge priorities you already know.

## Set up your Pack profile

The shared knowledge files are for all Packs. Your profile holds local arrangements such as meeting night, term dates, Six names, opening routine and planning preferences.

1. Create `packs/<pack-slug>/` for your Pack.
2. Copy `PACK-PROFILE-TEMPLATE.md` there as `PACK-PROFILE.md`.
3. Add Pack-specific `templates/`, `planners/` and `programmes/` subfolders as needed.
4. Replace the profile prompts with arrangements approved by your Pack.
5. Tell the AI assistant to read that profile whenever it plans for your Pack.

`packs/1st-pinelands/` is an example, not a default. Create a separate folder for your Pack; do not add your local plans to another Pack's folder. A profile cannot override official SSA requirements. Avoid putting children's names, contact details, medical information or other private member information in a public repository.

## Using and improving the knowledge base

Ask the assistant to work from the supplied files. For example:

> Using my Pack profile and the SSA advancement material, suggest a term outline. Include the source for each advancement item. If the source does not verify a requirement, flag it instead of guessing.

To add or improve resources:

* Keep original source files in `docs/pop/src/` and do not overwrite them.
* Add readable, source-linked references in the appropriate `docs/` library.
* Record the source title or filename, source URL when known, and date/version when available.
* Search the existing library before creating a new game, yarn, craft or activity. Label an item as reused, adapted or newly created. Add new reusable elements as standalone files in the relevant shared library and update its source-neutral index; name AI-created material honestly rather than inventing a source.
* Keep official requirements distinct from interpretations, activity connections and new suggestions.
* Flag outdated, conflicting, ambiguous or incomplete information for review.
* For a new meeting plan, use the template in the selected Pack's folder. Keep the programme and its instructions with that Pack.
* Review every AI-generated plan before running it, especially badge links, equipment and activity instructions.

Each game, yarn, craft and instruction/activity library entry has an **Advancement / badge link** field. It may say that a programme-level note is context only or that a connection is unverified. This prevents a broad POP note from being mistaken for proof that every activity meets a badge requirement.

Every extracted entry also carries the full advancement/badge information stated by its POP programme. This is copied as programme-level context for later review; edit each activity's copy to retain only the links that activity supports.

### Export a meeting plan to PDF

Install LibreOffice on your computer if it is not already installed. Then, from the repository folder, run:

```sh
python3 scripts/export_programme_pdf.py packs/<pack-slug>/programmes/<meeting-plan>.md
```

The PDF is saved in a `pdf/` folder beside the programme. Use `-o FOLDER` to choose a different destination. If a PDF with that name already exists, the exporter stops rather than replacing it; add `--overwrite` only when you intend to replace that copy.

For pictures to appear in the PDF, place permitted image files alongside the Pack programme (for example, in its `visuals/` folder) and add them using Markdown image syntax with a relative path. Put a list of required visuals and attachments in the plan's **Visual aids and attachments** section. The exporter embeds local Markdown images. Current POP converters do not extract pictures embedded inside source Word/PDF files, so if a plan depends on one of those visuals, cite the original filename, link to its ScoutWiki resource page and record its page/section; add a local image copy only when reuse is permitted.

To contribute through GitHub, create a branch or fork, make your changes, then open a Pull Request describing what changed and naming the sources you used. If you are not comfortable with Git, you can open an Issue on the repository and describe the resource or correction for a maintainer to add.

## Optional: maintaining the conversion tools

Most users do not need Python or the conversion scripts. They are for maintainers who process source documents or refresh library catalogues. After adding or renaming a library item, run its index builder from the repository root: `python3 scripts/build_game_index.py`, `python3 scripts/build_yarn_index.py`, `python3 scripts/build_craft_index.py` or `python3 scripts/build_activity_index.py`. The scripts and their dependencies can change; inspect the current script and its instructions before running it. Never use a conversion command that writes over files under `docs/pop/src/`.

## Important use notes

* Use current, authoritative SSA sources to confirm requirements; the supplied material may include older editions.
* Do not invent badge requirements, programme rules or safety instructions.
* Distinguish source statements, Pack-approved practice and AI suggestions.
* Keep Pack-specific details in that Pack's profile so they are not mistaken for shared SSA guidance.

## Official tool setup links

* [Gemini CLI](https://github.com/google-gemini/gemini-cli)
* [OpenAI Codex CLI](https://developers.openai.com/codex/cli)
* [Claude Code](https://docs.anthropic.com/en/docs/claude-code/getting-started)
