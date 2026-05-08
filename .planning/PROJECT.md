# Codex Civica

## What This Is

An open, markdown-parsed, interlinked repository of laws — starting with Israeli Knesset legislation, expanding globally. Every law is a Markdown file, version-controlled in Git, published as a searchable static site via Docusaurus. No paywalls, no logins, no friction.

## Core Value

Anyone — lawyer, student, or citizen — can find and read any Israeli law in plain, readable form in under 30 seconds.

## Requirements

### Validated

- ✓ Docusaurus site scaffold initialized (`site/`) with TypeScript config — existing
- ✓ GitHub Actions deploy workflow configured (push → build → GitHub Pages) — existing
- ✓ Law file schema defined: frontmatter + Markdown structure with 50-category taxonomy — existing
- ✓ Python pipeline skeleton: `requirements.txt` with all dependencies (knesset-data, python-docx, pandoc, etc.) — existing
- ✓ Flat law directory structure established: `laws/israel/` — existing
- ✓ Codebase architecture mapped in `.planning/codebase/` — existing

### Active

**Pipeline**
- [ ] `pipeline/convert.py` — `.docx` → Markdown with frontmatter generation (via Pandoc + python-docx)
- [ ] `pipeline/validate.py` — frontmatter completeness + internal link integrity checks
- [ ] Manual download workflow documented for Knesset .docx files (WSL2 IP blocked by Reblaze)

**Content — Basic Laws Batch**
- [ ] 14 Basic Laws downloaded (.docx) and converted to Markdown
- [ ] Each law has complete frontmatter (title, title_he, law_id, category, enacted, status)
- [ ] Laws committed to `laws/israel/` following naming conventions

**Site — Configuration**
- [ ] Docusaurus boilerplate removed; `laws/israel/` wired as docs source
- [ ] Hebrew RTL support configured (i18n `he`)
- [ ] Docusaurus local search plugin installed and configured
- [ ] Sidebar auto-generated from law categories

**Site — Custom UI**
- [ ] Homepage: project mission, category browse, quick-start call to action
- [ ] Law pages: clean Hebrew text rendering, frontmatter metadata display
- [ ] Mobile-responsive, accessible (WCAG AA target)
- [ ] Public-first / warm aesthetic — readable for non-lawyers

**Deployment**
- [ ] Site builds cleanly from `laws/israel/` content
- [ ] GitHub Pages deployment verified end-to-end

### Out of Scope

- English full-text translations — Phase 2 (Hebrew-only acceptable to start)
- `pipeline/link.py` cross-reference resolver — Phase 2 (links need volume to be meaningful)
- `pipeline/fetch.py` OData API ingestion — Phase 2 (manual download workflow for Phase 1)
- Algolia DocSearch — Phase 2 (local search sufficient for Basic Laws volume)
- Non-Basic-Law categories — Phase 2+ (volume and pipeline validation first)
- Jordan, other countries — future milestone

## Context

- **Environment:** Windows 11 + WSL2 (Ubuntu 24.04). Project at `/mnt/c/Dev/codex-civica`. Python venv at `~/.venv-codex`.
- **Knesset download constraint:** The Knesset site (Reblaze WAF) blocks WSL2 IP ranges. `.docx` files must be downloaded from a Windows browser and saved to `data/raw/israel/` manually — this is a permanent workflow constraint, not a bug to fix.
- **Content language:** All source law text is Hebrew (RTL). English translations are out of scope for Phase 1.
- **Reference project:** QLC at https://yuvaldv.github.io/qlc/ — same philosophy (Git + Markdown + static site), different stack (Hugo). Codex Civica uses Docusaurus for richer cross-referencing.
- **Docusaurus is scaffolded but contains boilerplate** (`site/blog/`, `site/docs/tutorial-*`). Phase 1 must clean this up.
- **Basic Laws:** Israel has ~14 Basic Laws (חוקי יסוד) — the constitutional-tier legislation. They're small, well-known, and high-value as a first batch.

## Constraints

- **Tech Stack:** Docusaurus (TypeScript) for site — locked. Python + Pandoc for pipeline — locked. No Hugo shortcodes.
- **Data source:** Knesset `.docx` files only (primary). WIPO/NATLEX as supplement for missing metadata.
- **File structure:** Flat dump `laws/israel/` — no subfolders. Categories via frontmatter only.
- **Content integrity:** Never invent law data. Missing dates/IDs → leave blank, open GitHub issue.
- **WSL2 download:** Knesset site blocked from WSL2 — manual download from Windows browser is required workflow.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hebrew-only for Phase 1 | Translation quality risk; Hebrew content is the source of truth | — Pending |
| Basic Laws as first batch | Small (14), high-value, well-scoped for pipeline validation | — Pending |
| Local search before Algolia | Algolia requires approval + index setup; local search ships faster | — Pending |
| Manual .docx download workflow | WSL2 blocked by Knesset WAF — no automated fix available | — Pending |
| Public-first UI aesthetic | Target audience is citizens, not just lawyers | — Pending |
| Flat file structure, categories via frontmatter | Simpler than nested dirs; Docusaurus sidebars handle grouping | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-08 after initialization*
