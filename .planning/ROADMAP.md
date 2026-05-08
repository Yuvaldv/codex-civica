# Roadmap — Codex Civica

> Milestone 1: Israeli Basic Laws on a live, searchable site.
> Structure: Vertical MVP slices. Fine granularity.
> Mode: MVP

---

## Phases

- [ ] **Phase 1: Pipeline** — Build convert.py and validate.py; document the manual download workflow
- [ ] **Phase 2: Content** — Download, convert, and validate all 14 Israeli Basic Laws
- [ ] **Phase 3: Site Foundation** — Wire laws into Docusaurus; configure RTL, sidebar, and remove boilerplate
- [ ] **Phase 4: Search** — Install and configure Docusaurus local search plugin
- [ ] **Phase 5: Custom UI** — Homepage, law page rendering, mobile responsiveness, and accessible aesthetic
- [ ] **Phase 6: Deployment** — Verify build and GitHub Pages end-to-end delivery

---

## Phase Details

### Phase 1: Pipeline
**Goal**: A working pipeline that converts .docx files to correctly structured Markdown and validates the output
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: PIPE-01, PIPE-02, PIPE-03
**Success Criteria** (what must be TRUE):
  1. Running `python pipeline/convert.py --input data/raw/israel/ --output laws/israel/` on a .docx file produces a .md file with all mandatory frontmatter fields populated
  2. Running `python pipeline/validate.py --laws laws/israel/ --report` produces a machine-readable report listing completeness and link integrity results per file
  3. `pipeline/README.md` exists and a developer can follow it step-by-step to download a law from the Knesset site and run the full pipeline without needing to ask anyone
**Plans**: TBD

### Phase 2: Content
**Goal**: All 14 Israeli Basic Laws are in the repository as correctly formatted, validated Markdown files
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: CONT-01, CONT-02, CONT-03, CONT-04
**Success Criteria** (what must be TRUE):
  1. `laws/israel/` contains exactly 14 .md files — one per Basic Law — with no extra or missing files
  2. Every Basic Law filename is slugified English, lowercase, hyphens only (e.g. `basic-law-human-dignity-and-liberty.md`)
  3. Every Basic Law file has all mandatory frontmatter fields filled: title, title_he, law_id, category, enacted, status
  4. `python pipeline/validate.py --laws laws/israel/ --report` exits with zero errors and zero missing mandatory fields
**Plans**: TBD

### Phase 3: Site Foundation
**Goal**: Docusaurus serves the Basic Laws as navigable docs with Hebrew RTL rendering and auto-generated category sidebar
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: SITE-01, SITE-02, SITE-04
**Success Criteria** (what must be TRUE):
  1. `npm run build` in `site/` succeeds with no errors when pointed at `laws/israel/`
  2. All Docusaurus boilerplate is removed (no blog/, no tutorial-* docs, no default homepage placeholder content)
  3. Hebrew law text renders right-to-left in the browser without character garbling or direction artifacts
  4. The sidebar groups Basic Laws under a "Basic Laws" label, drawn automatically from frontmatter category without manual sidebar editing
**Plans**: TBD
**UI hint**: yes

### Phase 4: Search
**Goal**: Users can search laws by name or keyword and reach the relevant law page in one step
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: SITE-03
**Success Criteria** (what must be TRUE):
  1. A search box is visible and functional on the live site
  2. Searching a Basic Law by its Hebrew or English name returns that law as a result
  3. Searching a keyword that appears in law body text returns the relevant law(s)
**Plans**: TBD
**UI hint**: yes

### Phase 5: Custom UI
**Goal**: The site looks and feels like a public civic resource — warm, readable, accessible — not a government form or developer tool
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. The homepage displays the project mission, a category browse grid, and a clear "Browse laws" call to action visible without scrolling on desktop
  2. An individual law page shows the law's enacted date, status, and category as visible metadata alongside the law text
  3. The site passes WCAG AA contrast ratio checks on all text elements in both light and dark modes
  4. The site layout is usable on a 375px-wide mobile screen (no horizontal scroll, readable font size, reachable nav)
  5. A non-lawyer viewing the site for the first time would describe it as clear and approachable rather than dense or bureaucratic
**Plans**: TBD
**UI hint**: yes

### Phase 6: Deployment
**Goal**: Pushing to main publishes the site to GitHub Pages and anyone can read Israeli Basic Laws online
**Mode:** mvp
**Depends on**: Phase 4, Phase 5
**Requirements**: DEPLOY-01, DEPLOY-02
**Success Criteria** (what must be TRUE):
  1. `npm run build` in `site/` completes with zero errors when the full Basic Laws batch is present
  2. Pushing a commit to `main` triggers the GitHub Actions workflow and the site is live on GitHub Pages within 5 minutes
  3. The live GitHub Pages URL loads the Codex Civica homepage and all 14 Basic Laws are reachable and render correctly
**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pipeline | 0/? | Not started | - |
| 2. Content | 0/? | Not started | - |
| 3. Site Foundation | 0/? | Not started | - |
| 4. Search | 0/? | Not started | - |
| 5. Custom UI | 0/? | Not started | - |
| 6. Deployment | 0/? | Not started | - |

---

## Coverage

| REQ-ID | Phase |
|--------|-------|
| PIPE-01 | Phase 1 |
| PIPE-02 | Phase 1 |
| PIPE-03 | Phase 1 |
| CONT-01 | Phase 2 |
| CONT-02 | Phase 2 |
| CONT-03 | Phase 2 |
| CONT-04 | Phase 2 |
| SITE-01 | Phase 3 |
| SITE-02 | Phase 3 |
| SITE-04 | Phase 3 |
| SITE-03 | Phase 4 |
| UI-01 | Phase 5 |
| UI-02 | Phase 5 |
| UI-03 | Phase 5 |
| UI-04 | Phase 5 |
| DEPLOY-01 | Phase 6 |
| DEPLOY-02 | Phase 6 |

**Coverage: 17/17 requirements mapped.**

---

*Created: 2026-05-08*
