# CLAUDE.md — Codex Civica

> This file is the persistent briefing for Claude Code on the Codex Civica project.
> Read this at the start of every session before doing anything else.

---

## Project Overview

**Codex Civica** is an open, markdown-parsed, interlinked repository of laws — starting with the State of Israel, expanding globally. Every law is a Markdown file, version-controlled in Git, published as a searchable static site via Docusaurus.

**Mission:** Make the law readable, searchable, and interconnected for everyone — free of charge, free of paywalls.

**Current phase:** Israel state laws (primary legislation from the Knesset).

**Live reference:** See QLC (prior project by same author) at https://yuvaldv.github.io/qlc/ — Hugo-based, Git-hosted, Markdown-parsed curriculum site. Codex Civica follows the same philosophy but uses Docusaurus for richer cross-referencing and versioning.

---

## Environment

- **OS:** Windows 11 + WSL2 (Ubuntu 24.04)
- **Project path (Windows):** `C:\Dev\codex-civica`
- **Project path (WSL2):** `/mnt/c/Dev/codex-civica`
- **Python venv:** `~/.venv-codex` (Linux-side, not on NTFS)
- **Alias:** `cdev` → `cd /mnt/c/Dev`
- **Claude Code alias:** `ccode` → `claude --dangerously-skip-permissions`

---

## Repository Structure

```
codex-civica/
├── CLAUDE.md                  ← You are here
├── .claude/
│   └── skills/                ← Project-level Claude Code skills
├── pipeline/                  ← Python ingestion + conversion scripts
│   ├── fetch.py               ← Knesset API / OData ingestion
│   ├── convert.py             ← .docx → Markdown conversion
│   ├── link.py                ← Cross-reference resolver + linker
│   ├── validate.py            ← Frontmatter + link integrity checks
│   └── requirements.txt
├── laws/
│   └── israel/                ← Flat dump of all Israeli law .md files
├── data/
│   └── raw/
│       └── israel/            ← Original .docx files (never edit these)
├── site/                      ← Docusaurus site (TypeScript)
│   ├── docusaurus.config.ts
│   └── ...
└── .github/
    └── workflows/
        └── deploy.yml         ← GitHub Actions: push → build → GitHub Pages
```

---

## Law File Format (Canonical Schema)

Every law is a single `.md` file inside `laws/israel/`. The frontmatter is mandatory and machine-readable.

```markdown
---
title: "Law Name in English"
title_he: "שם החוק בעברית"
law_id: "knesset-XXXX"
category: "health"
tags: ["welfare", "taxation"]
enacted: "YYYY-MM-DD"
last_amended: "YYYY-MM-DD"
status: "active"              # active | repealed | suspended
language: ["he", "en"]
source_url: "https://www.knesset.gov.il/..."
related_laws:
  - id: "knesset-XXXX"
    title: "Related Law Name"
    relationship: "amends"    # amends | amended-by | references | supersedes
---

# Law Name

> **Enacted:** YYYY | **Last amended:** YYYY | **Status:** Active

## Summary
[2-3 sentence plain-language summary]

---

## Full Text

### Section 1 — [Section Title]

[Law text here]

**References:** [Law Name, YYYY](./related-law.md), Section X

---

## Amendment History

| Date | Amendment | Description |
|------|-----------|-------------|
| YYYY-MM-DD | Amendment No. X | Brief description |

---

## See Also
- [Related Law](./related-law.md)
```

---

## Law Structure — Flat Dump

All laws live in a **flat dump** inside `laws/israel/`. No subfolders. Categories are handled entirely via frontmatter `category` (primary) and `tags` (secondary).

```
laws/
└── israel/
    ├── basic-law-human-dignity-and-liberty.md
    ├── national-health-insurance-law.md
    ├── companies-law.md
    └── ...
```

When adding a new country in the future:
```
laws/
├── israel/
└── jordan/
```

---

## Law Categories (Knesset Taxonomy)

The `category` frontmatter field uses one value from this list. `tags` handles secondary categories.

| Value | Hebrew | English |
|---|---|---|
| `basic-laws` | חוק-יסוד | Basic Laws |
| `citizenship-immigration` | אזרחות, תשובות וכניסה לישראל | Citizenship & Immigration |
| `elections` | בחירות | Elections |
| `defense` | ביטחון | Defense |
| `internal-security` | ביטחון הפנים | Internal Security |
| `construction-housing` | בינוי ושיכון | Construction & Housing |
| `banking-finance` | בנקאות וכספים | Banking & Finance |
| `health` | בריאות | Health |
| `religion` | דתות | Religion |
| `environment` | הגנת הסביבה | Environment |
| `foreign-affairs` | חוץ | Foreign Affairs |
| `arrangements-laws` | חוקי הסדרים | Arrangements Laws |
| `education` | חינוך | Education |
| `agriculture` | חקלאות | Agriculture |
| `technology-cyber` | טכנולוגיה וסייבר | Technology & Cyber |
| `knesset` | כנסת | Knesset |
| `science` | מדע | Science |
| `holidays` | מועדים | Holidays |
| `state-loans` | מילווה למדינה | State Loans |
| `taxation` | מיסוי | Taxation |
| `commerce-industry` | מסחר ותעשייה | Commerce & Industry |
| `personal-status` | מעמד אישי | Personal Status |
| `emergency` | מצב חירום | Emergency |
| `health-professions` | מקצועות הבריאות | Health Professions |
| `real-estate` | מקרקעין | Real Estate |
| `civil-law` | משפט אזרחי | Civil Law |
| `administrative-law` | משפט מינהלי | Administrative Law |
| `criminal-law` | משפט פלילי | Criminal Law |
| `asset-management` | ניהול נכסים | Asset Management |
| `sport` | ספורט | Sport |
| `shipping` | ספנות | Shipping |
| `judicial-courts` | ערכאות שיפוטיות | Judicial Courts |
| `development-investment` | פיתוח והשקעות | Development & Investment |
| `pension-insurance-capital-markets` | פנסיה, ביטוח ושוק ההון | Pension, Insurance & Capital Markets |
| `consumer-affairs` | צרכנות | Consumer Affairs |
| `immigrant-absorption` | קליטת עלייה | Immigrant Absorption |
| `evidence-procedure` | ראיות וסדרי דין | Evidence & Procedure |
| `heads-of-state` | ראשי המדינה | Heads of State |
| `welfare` | רווחה | Welfare |
| `local-authorities` | רשויות מקומיות | Local Authorities |
| `public-service` | שירות הציבור | Public Service |
| `corporations` | תאגידים | Corporations |
| `transport-road-safety` | תחבורה ובטיחות בדרכים | Transport & Road Safety |
| `tourism` | תיירות | Tourism |
| `planning-building` | תכנון ובנייה | Planning & Building |
| `aviation` | תעופה | Aviation |
| `employment` | תעסוקה | Employment |
| `budget` | תקציב | Budget |
| `communications` | תקשורת | Communications |
| `culture` | תרבות | Culture |
| `infrastructure` | תשתיות | Infrastructure |

---

## Naming Conventions

### File names
- Slugified English law name: `basic-law-human-dignity-and-liberty.md`
- Always lowercase, hyphens only, no spaces
- For laws with no official English name: transliterate from Hebrew

### Law IDs
- Format: `knesset-{bill_id}` (e.g. `knesset-10234`)
- If no Knesset ID: `il-{year}-{slug}` (e.g. `il-1992-human-dignity`)

---

## Data Sources

### Primary: Knesset National Legislation Database
- **URL:** `https://main.knesset.gov.il/Activity/Legislation/Laws/Pages/lawlaws.aspx?t=lawlaws&st=lawlaws`
- **Format:** `.docx` files, Hebrew text
- **Important:** The Knesset site blocks WSL2 IP ranges (Reblaze). Download `.docx` files manually from Windows browser → save to `C:\Dev\codex-civica\data\raw\israel\`

### Secondary: Knesset OData API
- **Endpoint:** `https://knesset.gov.il/Odata/ParliamentInfo.svc/`
- **Key table:** `KNS_Bill` — bills where `StatusID = 118` are enacted laws
- **Python package:** `knesset-data` (already installed in venv)
- **Note:** Always call `is_reblaze_content()` before parsing any response

### Tertiary
- **WIPO Lex Israel:** `https://www.wipo.int/wipolex/en/members/profile/IL`
- **NATLEX (ILO):** Labor law supplement
- **Library of Congress:** `https://guides.loc.gov/law-israel/legislative`

---

## Pipeline: How to Process Laws

**Fully automated from WSL2** — no manual browser download required. The OData API and
`fs.knesset.gov.il` file server are both accessible from WSL2 (Reblaze only blocks the
main Knesset website, not the API or file server).

### Step 1 — Fetch metadata and PDFs
```bash
source ~/.venv-codex/bin/activate
python pipeline/fetch.py
```
- Queries `KNS_Bill` (OData) for all `StatusID eq 118` in-effect laws (~7,699)
- Downloads official PDFs from `fs.knesset.gov.il` to `data/raw/israel/{bill_id}.pdf`
- Writes `data/raw/israel/manifest.json` (crash-safe: saves every 100 laws)
- Re-running is safe — already-downloaded PDFs are skipped
- Use `--limit N` for testing with a small batch

### Step 2 — Convert PDFs to Markdown
```bash
python pipeline/convert.py
```
- Reads `data/raw/israel/manifest.json`
- Extracts Hebrew text with `pymupdf` (correct RTL word order)
- Writes `laws/israel/{slug}.md` with complete YAML frontmatter

### Step 3 — Validate
```bash
python pipeline/validate.py --laws laws/israel/ --report
```
- Checks all frontmatter fields populated
- Verifies all internal links resolve
- Outputs `data/validation_report.json`

### Step 4 — Commit & Deploy
```bash
git checkout -b batch/israel-{category}-{N}
git add laws/israel/
git commit -m "feat(laws): add {description}"
gh pr create --title "Israel {category} — batch {N}" --body "Adds X laws"
# GitHub Actions auto-builds Docusaurus on merge
```

> **Note:** `pipeline/link.py` (cross-reference resolver) is deferred to a future milestone
> when the corpus reaches sufficient volume (100+ laws) for cross-references to be meaningful.

---

## Installed Tools & MCP Servers

| Tool | Purpose |
|------|---------|
| MemPalace MCP | Persistent memory across sessions |
| Filesystem MCP | Scoped to `/mnt/c/Dev/codex-civica/` |
| Context7 MCP | Live docs for python-docx, Docusaurus, etc. |
| Firecrawl | Web scraping (for non-Knesset sources) |
| GSD | Spec-driven workflow — discuss→plan→execute→verify→ship |
| GitHub CLI (`gh`) | Repo management, PRs, issues |
| Pandoc | `.docx` → Markdown conversion |

---

## GSD Workflow for Codex Civica

Each law processing batch = one GSD phase:

```
/gsd-map-codebase        # first time or after major changes
/gsd-new-project         # set up planning context

# Per batch:
/gsd-discuss-phase N     # lock in decisions
/gsd-plan-phase N        # research + atomic task plans
/gsd-execute-phase N     # execute with atomic commits
/gsd-verify-work N       # verification + UAT
/gsd-ship N              # finalize, prep next

/gsd-progress            # lost? this tells you where you are
/gsd-quick "fix X"       # one-off fixes without full planning
```

---

## Language & Hebrew Handling

- All law text is originally in **Hebrew (RTL)**
- English versions are translations — always note if machine-translated vs. official
- Frontmatter uses both `title` (English) and `title_he` (Hebrew)
- In Markdown body, Hebrew block quotes: `> *Original Hebrew text*`
- If uncertain about a term, flag with `<!-- TODO: verify translation -->`
- Use accepted English equivalents: "Knesset" not "parliament", "Basic Law" not "constitutional law"

---

## Docusaurus Configuration Notes

- **TypeScript** config (`docusaurus.config.ts`)
- **Search:** Algolia DocSearch — free for open-source
- **i18n:** Hebrew (`he`) + English (`en`) — RTL configured for Hebrew
- **Cross-references:** Standard relative Markdown links — Docusaurus resolves at build time
- **Law relationship graph:** Mermaid.js (built into Docusaurus)

---

## MemPalace Memory Keys

| Prefix | What to store |
|--------|--------------|
| `schema:` | Frontmatter field decisions |
| `processed:` | Law IDs successfully converted and committed |
| `pending:` | Laws fetched but not yet converted |
| `issue:` | Known problems with specific laws |
| `convention:` | Naming/categorization decisions |
| `translation:` | Agreed English translations for Hebrew legal terms |

---

## GitHub Issues Taxonomy

| Label | Meaning |
|-------|---------|
| `law:missing-date` | Enacted date not found in source |
| `law:bad-docx` | Source .docx corrupt or malformed |
| `law:untranslated` | No English version exists yet |
| `law:needs-review` | Cross-references need human verification |
| `law:repealed` | Law no longer active |
| `pipeline:bug` | Issue with pipeline scripts |
| `site:build` | Docusaurus build failure |

---

## What NOT to Do

- **Do not edit files in `data/raw/`** — source files, treat as immutable
- **Do not create subfolders inside `laws/israel/`** — flat dump only, categories via frontmatter
- **Do not commit `.docx` files larger than 10MB** — store externally if needed
- **Do not invent law data** — if a date or ID can't be found, leave blank and open a GitHub issue
- **Do not translate entire law bodies in one pass** — section by section, flag for review
- **Do not use Hugo shortcodes** — this is Docusaurus/CommonMark only

---

## Useful Commands

```bash
# Activate Python venv
source ~/.venv-codex/bin/activate

# Convert a single .docx manually
pandoc data/raw/israel/some-law.docx -f docx -t markdown -o laws/israel/some-law.md

# Validate all laws
python pipeline/validate.py --laws laws/israel/ --report

# Run local Docusaurus dev server
cd site && npm start

# Build Docusaurus for production
cd site && npm run build

# Open GitHub issue for a problematic law
gh issue create --title "law:missing-date — [Law Name]" --label "law:missing-date"

# Check MemPalace for project state
mempalace get "schema:*"
mempalace get "processed:*" | wc -l
```

---

## Current Status (update each session via MemPalace)

```
Last updated: [DATE]
Laws fetched: [N]
Laws converted: [N]
Laws linked: [N]
Laws validated + committed: [N]
Open issues: [N]
Current batch: [description]
Blocked on: [if anything]
```

---

## Session Startup Checklist

1. `mempalace get "schema:*"` — reload schema decisions from past sessions
2. `mempalace get "convention:*"` — reload naming conventions
3. Read **Current Status** above
4. Ask: *"What are we working on this session?"* before starting any task
5. Do not assume continuity — verify current state from Git and MemPalace

---

*Codex Civica — the law belongs to everyone.*
