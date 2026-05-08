# Requirements — Codex Civica

> Scope: Milestone 1 — Israeli Basic Laws on a live, searchable site.
> Structure: Vertical MVP slices. Fine granularity.

---

## v1 Requirements

### Pipeline

- [ ] **PIPE-01**: User can run `convert.py` to transform a `.docx` file into a Markdown file with complete, valid frontmatter (title, title_he, law_id, category, enacted, status, source_url)
- [ ] **PIPE-02**: User can run `validate.py` to get a report of frontmatter completeness and internal link integrity across all laws in `laws/israel/`
- [ ] **PIPE-03**: `pipeline/README.md` documents the manual download workflow (Windows browser → Knesset site → save to `data/raw/israel/`) and the full pipeline command sequence

### Content — Basic Laws

- [ ] **CONT-01**: All 14 Israeli Basic Laws are present in `laws/israel/` as correctly formatted Markdown files
- [ ] **CONT-02**: Every Basic Law file has complete frontmatter with no blank mandatory fields (title, title_he, law_id, category, enacted, status)
- [ ] **CONT-03**: Every Basic Law filename follows the naming convention: slugified English, lowercase, hyphens only (e.g. `basic-law-human-dignity-and-liberty.md`)
- [ ] **CONT-04**: `validate.py` runs clean on the Basic Laws batch (zero errors, zero missing mandatory fields)

### Site — Configuration

- [ ] **SITE-01**: Docusaurus boilerplate removed (`blog/`, `tutorial-*` docs, default pages); `laws/israel/` wired as the primary docs source
- [ ] **SITE-02**: Hebrew RTL rendering configured in Docusaurus i18n for law text display
- [ ] **SITE-03**: Docusaurus local search plugin installed, indexed, and functional (user can search by law name or keyword)
- [ ] **SITE-04**: Sidebar auto-generated from law frontmatter categories; Basic Laws appear under "Basic Laws" group

### Site — Custom UI

- [ ] **UI-01**: Homepage displays project mission statement, category browse grid, and a clear call to action (e.g. "Browse laws")
- [ ] **UI-02**: Individual law pages render Hebrew text clearly with frontmatter metadata visible (enacted date, status, category)
- [ ] **UI-03**: Site is mobile-responsive and meets WCAG AA contrast ratios
- [ ] **UI-04**: Visual aesthetic is public-first / accessible — warm, readable, not bureaucratic

### Deployment

- [ ] **DEPLOY-01**: `npm run build` in `site/` succeeds with no errors when `laws/israel/` contains the Basic Laws batch
- [ ] **DEPLOY-02**: Pushing to `main` triggers GitHub Actions deploy and the site is live on GitHub Pages within 5 minutes

---

## v2 Requirements (deferred)

- Cross-reference resolver (`link.py`) — needs volume to be meaningful
- OData API ingestion (`fetch.py`) — manual workflow sufficient for Phase 1 volume
- Algolia DocSearch — local search sufficient for Basic Laws volume
- English full-text translations — translation quality risk
- Additional law categories beyond Basic Laws
- Mermaid.js law relationship graph
- Amendment history tables populated from source data

---

## Out of Scope

- English full translations — source truth is Hebrew; translation quality unverified
- `pipeline/fetch.py` / OData ingestion — Knesset API adds complexity; manual download is the workflow
- `pipeline/link.py` — cross-references need volume (100+ laws) to be worth resolving
- Algolia DocSearch — requires application + approval; local search ships faster
- Non-Israeli jurisdictions — future milestone, not Milestone 1
- User accounts / login — open read-only site only
- Comments or annotations — out of scope indefinitely

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| PIPE-01 | Phase 1 | Pending |
| PIPE-02 | Phase 1 | Pending |
| PIPE-03 | Phase 1 | Pending |
| CONT-01 | Phase 2 | Pending |
| CONT-02 | Phase 2 | Pending |
| CONT-03 | Phase 2 | Pending |
| CONT-04 | Phase 2 | Pending |
| SITE-01 | Phase 3 | Pending |
| SITE-02 | Phase 3 | Pending |
| SITE-04 | Phase 3 | Pending |
| SITE-03 | Phase 4 | Pending |
| UI-01 | Phase 5 | Pending |
| UI-02 | Phase 5 | Pending |
| UI-03 | Phase 5 | Pending |
| UI-04 | Phase 5 | Pending |
| DEPLOY-01 | Phase 6 | Pending |
| DEPLOY-02 | Phase 6 | Pending |
