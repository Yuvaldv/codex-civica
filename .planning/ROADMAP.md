# Roadmap — Codex Civica

> Milestone 1: Israeli Basic Laws on a live, searchable site.
> Structure: Vertical MVP slices. Fine granularity.
> Mode: MVP

---

## Phases

- [x] **Phase 1: Pipeline** — Build fetch.py, convert.py, and validate.py; fully automated from WSL2 using OData API + fs.knesset.gov.il
- [x] **Phase 2: Site Foundation** — Wire laws into Docusaurus; configure RTL, sidebar, and remove boilerplate
- [x] **Phase 3: Custom UI** — Homepage, law page rendering, mobile responsiveness, and accessible aesthetic
- [ ] **Phase 4: Content** — Download, convert, and validate all 718 Israeli laws with PDFs
- [x] **Phase 5: Deployment** — Verify build and GitHub Pages end-to-end delivery
- [ ] **Phase 6: Search** — Install and configure Docusaurus local search plugin

---

## Phase Details

### Phase 1: Pipeline
**Goal**: A working pipeline that fetches laws from the Knesset OData API, converts PDFs to structured Markdown, and validates the output — fully automated from WSL2
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: PIPE-01, PIPE-02, PIPE-03
**Success Criteria** (what must be TRUE):
  1. Running `python pipeline/fetch.py` downloads PDFs and writes `data/raw/israel/manifest.json`
  2. Running `python pipeline/convert.py --input data/raw/israel/ --output laws/israel/` produces .md files with all mandatory frontmatter fields populated
  3. Running `python pipeline/validate.py --laws laws/israel/ --report` produces a machine-readable report listing completeness and link integrity results per file
  4. `pipeline/README.md` exists and a developer can follow it step-by-step to run the full pipeline without needing to ask anyone
**Plans**: 3 plans

**Wave 1** — 01-PLAN-01-fetch.md *(no dependencies)*
- [ ] 01-PLAN-01-fetch.md — fetch.py + requirements.txt: OData metadata fetch and PDF download

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 01-PLAN-02-convert.md — convert.py: PDF-to-Markdown conversion with frontmatter generation

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 01-PLAN-03-validate-readme.md — validate.py + README.md: schema validation and pipeline documentation

**Cross-cutting constraints:**
- All commands: `source ~/.venv-codex/bin/activate` (Linux-side venv, not repo .venv)
- All file writes are crash-safe (manifest written every 100 laws; convert skips already-done files)

### Phase 2: Site Foundation
**Goal**: Docusaurus serves the laws as navigable docs with Hebrew RTL rendering and auto-generated category sidebar
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: SITE-01, SITE-02, SITE-04
**Success Criteria** (what must be TRUE):
  1. `npm run build` in `site/` succeeds with no errors when pointed at `laws/israel/`
  2. All Docusaurus boilerplate is removed (no blog/, no tutorial-* docs, no default homepage placeholder content)
  3. Hebrew law text renders right-to-left in the browser without character garbling or direction artifacts
  4. The sidebar groups laws under category labels, drawn automatically from frontmatter without manual sidebar editing
**Status**: Complete
**UI hint**: yes

### Phase 3: Custom UI
**Goal**: The site looks and feels like a public civic resource — warm, readable, accessible — not a government form or developer tool
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. The homepage displays the project mission, a category browse grid, and a clear "Browse laws" call to action visible without scrolling on desktop
  2. An individual law page shows the law's enacted date, status, and category as visible metadata alongside the law text
  3. The site passes WCAG AA contrast ratio checks on all text elements in both light and dark modes
  4. The site layout is usable on a 375px-wide mobile screen (no horizontal scroll, readable font size, reachable nav)
  5. A non-lawyer viewing the site for the first time would describe it as clear and approachable rather than dense or bureaucratic
**Status**: Complete
**UI hint**: yes

### Phase 4: Content
**Goal**: All 718 Israeli laws with available PDFs are in the repository as correctly formatted, validated Markdown files
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: CONT-01, CONT-02, CONT-03, CONT-04
**Success Criteria** (what must be TRUE):
  1. `laws/israel/` contains one .md file per converted law with no extra or missing files
  2. Every law file has all mandatory frontmatter fields filled: law_id, title_he, publication_date, law_validity, category, ministry_ids
  3. Cross-reference links (intra-law and inter-law) are resolved for all converted laws
  4. `python pipeline/batch_import.py --status` shows 718/718 converted with 0 failed
**Status**: In progress (10/718)
**Plans**: TBD

### Phase 5: Deployment
**Goal**: Pushing to main publishes the site to GitHub Pages and anyone can read Israeli laws online
**Mode:** mvp
**Depends on**: Phase 3, Phase 4
**Requirements**: DEPLOY-01, DEPLOY-02
**Success Criteria** (what must be TRUE):
  1. `npm run build` in `site/` completes with zero errors when the full law batch is present
  2. Pushing a commit to `main` triggers the GitHub Actions workflow and the site is live on GitHub Pages within 5 minutes
  3. The live GitHub Pages URL loads the Codex Civica homepage and all converted laws are reachable and render correctly
**Status**: Complete (GitHub Pages live; auto-deploy via USE_SSH=true)
**Plans**: TBD

### Phase 6: Search
**Goal**: Users can search laws by name or keyword and reach the relevant law page in one step
**Mode:** mvp
**Depends on**: Phase 5
**Requirements**: SITE-03
**Success Criteria** (what must be TRUE):
  1. A search box is visible and functional on the live site
  2. Searching a law by its Hebrew name returns that law as a result
  3. Searching a keyword that appears in law body text returns the relevant law(s)
**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pipeline | 3/3 | Done | 2026-05-08 |
| 2. Site Foundation | -/- | Done | 2026-05-15 |
| 3. Custom UI | -/- | Done | 2026-05-15 |
| 4. Content | -/- | In progress (10/718) | - |
| 5. Deployment | -/- | Done | 2026-05-15 |
| 6. Search | 0/? | Not started | - |

---

## Coverage

| REQ-ID | Phase |
|--------|-------|
| PIPE-01 | Phase 1 |
| PIPE-02 | Phase 1 |
| PIPE-03 | Phase 1 |
| SITE-01 | Phase 2 |
| SITE-02 | Phase 2 |
| SITE-04 | Phase 2 |
| UI-01 | Phase 3 |
| UI-02 | Phase 3 |
| UI-03 | Phase 3 |
| UI-04 | Phase 3 |
| CONT-01 | Phase 4 |
| CONT-02 | Phase 4 |
| CONT-03 | Phase 4 |
| CONT-04 | Phase 4 |
| DEPLOY-01 | Phase 5 |
| DEPLOY-02 | Phase 5 |
| SITE-03 | Phase 6 |

**Coverage: 17/17 requirements mapped.**

---

*Created: 2026-05-08*
*Updated: 2026-05-08 — Phase 1 plans finalized (3 plans, wave structure 1→2→3)*
