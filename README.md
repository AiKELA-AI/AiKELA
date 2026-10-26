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
| `1stPinelands.md` | One Pack's profile, included as an example. Do not use its local details for another Pack. |
| `docs/` | Shared knowledge base, badge material, POP programmes and extracted activity libraries. |
| `docs/pop/` | Programme on a Plate Markdown references. |
| `docs/pop/src/` | Local original POP files used during conversion. Binary source files are excluded from the Markdown-only GitHub upload; Markdown entries keep the source filename and link to the ScoutWiki resource page. |
| `docs/games/`, `docs/yarns/`, `docs/crafts/`, `docs/activities/` | Growing libraries extracted from programmes, with source references where available. |
| `docs/programmes/PROGRAMME-TEMPLATE.md` | The meeting-plan format used for new programme plans. |
| `docs/programmes/2027/` | Example 2027 meeting plans for 1st Pinelands. |
| `docs/programmes/visuals/` | Local permitted images that can be embedded in programme PDFs. |
| `export_programme_pdf.py` | Turns a programme Markdown file into a print-ready landscape PDF using LibreOffice. |

The knowledge base is for South African Cub Scouting. Official SSA sources are the authority for requirements. An activity idea or an AI suggestion must not be presented as an official badge requirement.

## Getting started

### 1. Download a copy

Install Git if it is not already on your computer. Then open Terminal (macOS/Linux) or a terminal application (Windows), and run:

```sh
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
```

Replace `OWNER/REPOSITORY` with the address shown on the repository's GitHub page. For example, if the page is `https://github.com/pinelands/aikela`, use:

```sh
git clone https://github.com/ron-tuffin/aikela.git
cd aikela
```

If you do not want to use Terminal, GitHub's **Code → Download ZIP** option downloads a copy, but it is less convenient for receiving updates or contributing changes.

### Optional: open and preview the Markdown files

On Mac, **[MarkText](https://marktext.me/)** is a simple free editor that shows formatted Markdown as you type. It renders the preview in the document itself rather than in a separate pane. **[Visual Studio Code](https://code.visualstudio.com/)** is another free option with a separate Markdown preview, but has more menus and features. You can also read the files directly on GitHub without installing an editor.

### 2. Choose one AI assistant

These are examples; you only need one. Each provider may require an account, subscription or billing arrangement. Check the provider's current terms before signing in. Installation instructions can change, so use the linked official guide if a command does not work.

#### Gemini CLI

Install Node.js first if needed, then install Gemini CLI from a terminal:

```sh
npm install -g @google/gemini-cli
```

From inside the repository folder, start it with:

```sh
gemini
```

Follow its sign-in prompts. See Google's [Gemini CLI installation guide](https://github.com/google-gemini/gemini-cli) for current options and requirements.

#### OpenAI Codex CLI

Install Node.js first if needed:

```sh
npm install -g @openai/codex
```

From inside the repository folder, start it with:

```sh
codex
```

Follow the sign-in prompts. See the [Codex CLI documentation](https://developers.openai.com/codex/cli) for current setup instructions.

#### Claude Code

On macOS or Linux, Anthropic currently recommends its native installer:

```sh
curl -fsSL https://claude.ai/install.sh | bash
```

The command downloads and runs Anthropic's installer. If you would rather not run a downloaded installer from Terminal, see Anthropic's setup guide for other installation methods.

From inside the repository folder, start it with:

```sh
claude
```

Follow the sign-in prompts. See Anthropic's [Claude Code setup guide](https://docs.anthropic.com/en/docs/claude-code/getting-started) for current system requirements and authentication choices.

> **Already use another tool?** You can use any assistant that can read the files in this folder and follow project instructions. Check that it supports repository-level instruction files. `AGENTS.md` is the canonical guidance; small compatibility files point Gemini CLI and Claude Code to it.

### 3. Tell the assistant which Pack you are planning for

In the assistant's project session, try:

> Please read the project instructions and the Pack profile `MyPack.md`. Help me plan a Cub meeting using the SSA resources in `docs/`. Show which source supports each badge requirement, and label any new ideas as suggestions.

Replace `MyPack.md` with your Pack's profile filename. For a year or term plan, say which year/term and any dates, ages, meeting constraints or badge priorities you already know.

## Set up your Pack profile

The shared knowledge files are for all Packs. Your profile holds local arrangements such as meeting night, term dates, Six names, opening routine and planning preferences.

1. Make a copy of `PACK-PROFILE-TEMPLATE.md` in the repository root.
2. Rename the copy to your Pack name, for example `2ndExamplePack.md`.
3. Replace the prompts in the copy with information approved by your Pack.
4. Tell the AI assistant to use that profile whenever it plans for your Pack.

`1stPinelands.md` is an example, not a default. Create your own profile instead of changing it. A profile cannot override official SSA requirements. Avoid putting children's names, contact details, medical information or other private member information in a public repository.

## Using and improving the knowledge base

Ask the assistant to work from the supplied files. For example:

> Using my Pack profile and the SSA advancement material, suggest a term outline. Include the source for each advancement item. If the source does not verify a requirement, flag it instead of guessing.

To add or improve resources:

* Keep original source files in `docs/pop/src/` and do not overwrite them.
* Add readable, source-linked references in the appropriate `docs/` library.
* Record the source title or filename, source URL when known, and date/version when available.
* Keep official requirements distinct from interpretations, activity connections and new suggestions.
* Flag outdated, conflicting, ambiguous or incomplete information for review.
* For a new meeting plan, use `docs/programmes/PROGRAMME-TEMPLATE.md` and retain the practical activity table format.
* Review every AI-generated plan before running it, especially badge links, equipment and activity instructions.

Each game, yarn, craft and instruction/activity library entry has an **Advancement / badge link** field. It may say that a programme-level note is context only or that a connection is unverified. This prevents a broad POP note from being mistaken for proof that every activity meets a badge requirement.

Every extracted entry also carries the full advancement/badge information stated by its POP programme. This is copied as programme-level context for later review; edit each activity's copy to retain only the links that activity supports.

### Export a meeting plan to PDF

Install LibreOffice on your computer if it is not already installed. Then, from the repository folder, run:

```sh
python3 export_programme_pdf.py docs/programmes/2027/20270122-Sun-Smart-Expedition.md
```

The PDF is saved in a `pdf/` folder beside the programme. Use `-o FOLDER` to choose a different destination. If a PDF with that name already exists, the exporter stops rather than replacing it; add `--overwrite` only when you intend to replace that copy.

For pictures to appear in the PDF, place permitted image files in `docs/programmes/visuals/` and add them to the programme using Markdown image syntax, for example `![Sun-safety picture cards](../visuals/sun-safety-cards.png)`. Put a list of required visuals and attachments in the plan's **Visual aids and attachments** section. The exporter embeds local Markdown images. Current POP converters do not extract pictures embedded inside source Word/PDF files, so if a plan depends on one of those visuals, cite the original filename, link to its ScoutWiki resource page and record its page/section; add a local image copy only when reuse is permitted.

To contribute through GitHub, create a branch or fork, make your changes, then open a Pull Request describing what changed and naming the sources you used. If you are not comfortable with Git, you can open an Issue on the repository and describe the resource or correction for a maintainer to add.

## Optional: maintaining the conversion tools

Most users do not need Python or the conversion scripts. They are for maintainers who process source documents. The scripts and their dependencies can change; inspect the current script and its instructions before running it. Never use a conversion command that writes over files under `docs/pop/src/`.

## Important use notes

* Use current, authoritative SSA sources to confirm requirements; the supplied material may include older editions.
* Do not invent badge requirements, programme rules or safety instructions.
* Distinguish source statements, Pack-approved practice and AI suggestions.
* Keep Pack-specific details in that Pack's profile so they are not mistaken for shared SSA guidance.

## Official tool setup links

* [Gemini CLI](https://github.com/google-gemini/gemini-cli)
* [OpenAI Codex CLI](https://developers.openai.com/codex/cli)
* [Claude Code](https://docs.anthropic.com/en/docs/claude-code/getting-started)
