# Codex Civica

## What This Is

An open, markdown-parsed, interlinked repository of laws — starting with Israeli Knesset legislation, expanding globally. Every law is a Markdown file, version-controlled in Git, published as a searchable static site via Docusaurus. No paywalls, no logins, no friction.

## Core Value

Anyone — lawyer, student, or citizen — can find and read any Israeli law in plain, readable form in under 30 seconds.

## Current Milestone: v1.1 UK Laws — Pipeline + Law Directory

**Goal:** Stand up a UK legislation pipeline and law directory alongside the existing Israel work, with a source-appropriate architecture — legislation.gov.uk offers structured XML/Atom feeds, unlike Knesset's scanned PDFs — starting with England only and a small high-value batch.

**Scope for v1.1: England only.** The UK is not one legal jurisdiction — Scotland, Wales, and Northern Ireland each have devolved legislation with different bodies, extents, and (for Scotland/NI) different legal systems. v1.1 covers England-applicable legislation only (Westminster Acts and instruments that extend to England, primarily England & Wales / UK-wide Acts read for their England extent). Scotland, Wales, and Northern Ireland are explicit future milestones, not a v1.1 concern — directory/data structure should leave room for them (e.g. a `uk/` umbrella with `england/` as the first nation) without being built out now.

**Target features:**
- Research legislation.gov.uk's data source (API/XML schema) and design a pipeline architecture suited to structured input, rather than reusing the Israel OCR/Gemini pipeline as-is
- Build the pipeline (fetch/convert/validate) and convert a small starter batch of England-applicable legislation to Markdown
- A law directory for England content, wired into the same Docusaurus site as `laws/israel/`, structured to leave room for other UK nations later
- 🇬🇧 (or England-specific) entry added to the homepage "Pick a country" grid and navbar, matching the existing Israel pattern
- Amendments linked proactively, two directions: (1) every amendment affecting a document is listed at the **end of the original document**, not inline mid-text; (2) each amendment document links **inline, at the specific point in its own text**, back to the original provision it amends. CLML's `Commentary`/`CommentaryRef` and `ukm:UnappliedEffect` elements (found by the pitfalls research) are the likely data source for this — needs its own requirement/design pass, not assumed solved by cross-linking.

**Note:** Milestone v1.0 (Israeli Basic Laws) is not yet complete — Phase 4 (Content, 111/718 laws) is paused by user request and Phase 6 (Search) hasn't started. v1.1 proceeds in parallel by deliberate choice; v1.0's remaining phases stay in the roadmap and will be resumed later, not abandoned.

## Requirements

### Validated

- ✓ Docusaurus site scaffold initialized (`site/`) with TypeScript config — existing
- ✓ GitHub Actions deploy workflow configured (push → build → GitHub Pages) — existing
- ✓ Law file schema defined: frontmatter + Markdown structure with 50-category taxonomy — existing
- ✓ Python pipeline skeleton: `requirements.txt` with all dependencies (knesset-data, python-docx, pandoc, etc.) — existing
- ✓ Flat law directory structure established: `laws/israel/` — existing
- ✓ Codebase architecture mapped in `.planning/codebase/` — existing

### Active

**UK Laws (v1.1, England only)**
- [ ] Research legislation.gov.uk data source (XML/Atom API schema, coverage, rate limits) and propose pipeline architecture
- [ ] `pipeline_uk/` (or equivalent): fetch → convert → validate for a small starter batch of England-applicable legislation (capped at 10 Acts or fewer for the initial fetch — user-requested 2026-08-09)
- [ ] Starter batch (≤10 Acts) of England laws converted to Markdown with complete frontmatter, committed to the law directory
- [ ] Law directory wired into Docusaurus alongside `laws/israel/`, structured so Scotland/Wales/NI can be added later without a reshuffle
- [ ] 🇬🇧 (or England-specific) entry added to homepage country grid and navbar country picker
- [ ] Amendments listed at the end of the original document they affect (user-requested 2026-08-09; not the same as passive cross-referencing)
- [ ] Each amendment document links inline, at the specific point in its own text, back to the original provision it amends (user-requested 2026-08-09)

**Pipeline (Israel, v1.0 — carried over, unchanged)**
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
- UK legislation beyond the v1.1 starter batch (full Acts corpus, Statutory Instruments) — future milestone, scope after starter batch validates the pipeline
- Scotland, Wales, Northern Ireland legislation — future milestone; different legal systems/devolved bodies, deliberately deferred so v1.1 stays scoped to one England-only starter batch
- Jordan, other countries beyond the UK — future milestone

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
| v1.1 UK milestone proceeds in parallel with unfinished v1.0 | User explicitly chose "new milestone" over pausing Israel work or a separate workstream; v1.0 Phase 4/6 remain in the roadmap, not abandoned | — Pending |
| UK pipeline architecture: research first, don't reuse Israel's OCR/Gemini pipeline blindly | legislation.gov.uk exposes structured XML/Atom feeds, unlike Knesset's scanned PDFs — the noise-reconciliation assumptions in CLAUDE.md's LAYER1-3 design may not apply | — Pending |
| UK starter batch scope, not full corpus | Mirrors the Israel Basic-Laws-first approach: validate the pipeline end-to-end on a small set before scaling to the full Acts/SI corpus | — Pending |
| Same Docusaurus site, new UK section | Matches the homepage's existing "Pick a country" multi-country pattern; no separate deploy needed | — Pending |
| v1.1 scoped to England only, not the whole UK | UK is four distinct legal jurisdictions (England & Wales courts, Scots law, NI law) with separate devolved legislatures; user explicit call to start with one nation and expand later rather than build UK-wide from day one | — Pending |
| Rebase Docusaurus routes now: `/laws/israel` + `/laws/england`, with redirects for the 111 existing URLs | User chose symmetric structure over leaving Israel's route as-is; cheaper to do now while the corpus and search-index footprint are small than to retrofit later. Requires `@docusaurus/plugin-client-redirects` so the 111 already-SEO-indexed URLs 301 instead of breaking | — Pending |
| v1.1 initial England fetch capped at 10 Acts or fewer | User constraint given at roadmap approval — even smaller than the 13-Act Tier A batch the Features research proposed. Keeps the first real run of the UK pipeline small and easy to review before scaling up | — Pending |

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
*Last updated: 2026-08-09 after scoping milestone v1.1 to England only*
