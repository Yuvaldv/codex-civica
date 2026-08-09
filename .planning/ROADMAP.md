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

# Milestone v1.1 — UK Laws (England only)

> Goal: Stand up a legislation.gov.uk (CLML XML) pipeline and an England law directory alongside Israel, on the same Docusaurus site, with a small high-value starter batch.
> Structure: Dependency-ordered — shared core → acquisition → conversion → site (route rebase, then second country) → linking → batch + deploy. Fine granularity.
> Scope note: v1.0 (Phases 1–6) is still open — Phase 4 (Content, 111/718) is paused by user request and Phase 6 (Search) has not started. v1.1 runs in parallel by explicit user choice; v1.0 phases are untouched here.
> Numbering: v1.1 continues from v1.0's last phase — starts at Phase 7.

## Phases — v1.1

- [ ] **Phase 7: Shared Pipeline Core** — Extract the ~150 country-blind lines (frontmatter, progress, deploy) into `pipeline/common/` with zero behavior change to Israel
- [ ] **Phase 8: UK Acquisition** — England-extent `ukpga`/`aep` CLML XML fetched, stub- and version-gated, into `data/raw/uk/xml/`
- [ ] **Phase 9: CLML → Markdown Conversion** — The core: CLML → typed IR → deterministic Markdown + frontmatter, with amendment/extent/status fidelity and a round-trip validator
- [ ] **Phase 10: Site — Route Rebase** — Israel moves `/laws` → `/laws/israel` with redirects covering all 111 already-indexed URLs
- [ ] **Phase 11: Site — England Instance** — Second docs instance at `/laws/england` (`laws/uk/england/` on disk), country discriminator, homepage + navbar entry
- [ ] **Phase 12: Cross-Reference + Amendment Linking** — Citation resolution, end-of-document amendment lists, inline back-links from amending provisions
- [ ] **Phase 13: Starter Batch + Deploy** — Full England starter batch converted, validated, linked, built, and live

## Phase Details — v1.1

### Phase 7: Shared Pipeline Core
**Goal**: The pipeline has a country-blind core that a second country can build on, with Israel's output provably unchanged
**Mode:** mvp
**Depends on**: Nothing (independent; v1.0 phases unaffected)
**Requirements**: None — enabling refactor, carries no new v1.1 requirement scope (see Coverage note)
**Success Criteria** (what must be TRUE):
  1. `pipeline/common/` exists with frontmatter split/render, progress-file handling (`{done, failed, total_deployed, priority}`), and deploy helpers, and the Israel modules import them instead of holding their own copies
  2. Re-running the Israel pipeline over already-converted laws produces byte-identical files — `git diff --stat laws/israel/` is empty
  3. `python pipeline/batch_import.py --status` still reports the true import state (111/718 converted, 0 failed) through the shared progress module
  4. A new country package can read/write law frontmatter and progress without copying a single line of Israel-specific code
**Plans**: TBD

### Phase 8: UK Acquisition
**Goal**: England-applicable Acts are on disk as trustworthy CLML XML, with empty stubs and wrong-version documents rejected before they can reach conversion
**Mode:** mvp
**Depends on**: Phase 7
**Requirements**: UKFETCH-01, UKFETCH-02, UKFETCH-03
**Success Criteria** (what must be TRUE):
  1. Running the UK fetch script downloads England-extent `ukpga`/`aep` Acts as CLML XML into `data/raw/uk/xml/` and writes one manifest entry per item
  2. Fetching respects legislation.gov.uk's fair-use rules — mandatory identifying User-Agent, 5s crawl-delay between requests, cache-first on re-runs (verifiable in the run log)
  3. A PDF-only document (`NumberOfProvisions="0"`, no `<Body>`/`<Schedules>`) is skipped with a logged reason and produces no law file
  4. Every manifest entry records the resolved `DocumentURI` and derived version, and the starter batch contains only items with a genuine revised version — no `/enacted` content silently mixed in
  5. **The initial fetch is capped at 10 Acts or fewer** (user constraint, 2026-08-09) — selected from FEATURES.md's structurally-diverse Tier A candidates; the fetcher must not pull the full 13-Act list or beyond without an explicit later go-ahead
**Plans**: TBD

### Phase 9: CLML → Markdown Conversion
**Goal**: Any Act in the batch converts to a Markdown file a lawyer can rely on — complete, verbatim, correctly numbered, and honest about what is repealed, prospective, quoted, or not yet applied
**Mode:** mvp
**Depends on**: Phase 8
**Requirements**: UKCONV-01, UKCONV-02, UKCONV-03, UKCONV-04, UKCONV-05, UKCONV-06, UKCONV-07, UKCONV-08, UKCONV-09, UKCONV-10, UKVALID-01, UKVALID-02
**Success Criteria** (what must be TRUE):
  1. Converting an Act produces Markdown whose hierarchy and numbering match the source exactly (Part → Chapter → section → subsection → paragraph, verbatim `<Pnumber>` including Roman numerals and `19A`-style inserted numbers), with `P1group/Title` rendered as the section heading and every provision reachable by a stable legislation.gov.uk-style anchor (`section-1-1-a`)
  2. Frontmatter carries the `ukm:Metadata` fields (title, long title, year, chapter, enactment date, `DocumentMainType`, `DocumentStatus`, `dct:valid`) plus an explicit "as at {date}", and an Act with pending effects renders a visible unapplied-amendment banner with a count
  3. Repealed and prospective provisions are present and explicitly labeled — never deleted, never shown as current law — mixed territorial extent (`RestrictExtent`) is shown at provision level, and `BlockAmendment` quoted text is unmistakably marked as text quoted from another Act rather than as this Act's own provisions or headings
  4. Amendment markup (`Addition`/`Substitution`/`Repeal`) renders bracket-and-footnote style with the amending instrument cited, Schedules show their enabling-section back-link, and each law carries a defined-term index built from `<Term>` elements
  5. `validate.py` proves round-trip losslessness — every source `<Text>` node appears verbatim in the output — and reports UK numbering continuity that tolerates repealed-section gaps and alphanumeric suffixes; golden fixtures for a short Act, an Act with Schedules, and an amendment-heavy Act all pass as the phase-exit gate
**Plans**: TBD

### Phase 10: Site — Route Rebase
**Goal**: Israel content lives at `/laws/israel`, making room for a symmetric second country, and every previously indexed URL still resolves
**Mode:** mvp
**Depends on**: Nothing (independent of pipeline work; must land before Phase 11)
**Requirements**: UKSITE-01
**Success Criteria** (what must be TRUE):
  1. Israel docs serve from `/laws/israel/...` and `npm run build` succeeds with zero errors and zero broken-link warnings
  2. All 111 previously deployed `/laws/<id>` URLs redirect to their `/laws/israel/<id>` equivalent via `@docusaurus/plugin-client-redirects`, verified against the deployed URL list — zero 404s
  3. `sitemap.xml`, JSON-LD `url`, and `og:url` on Israel law pages all emit the new path
  4. Navbar, homepage country grid, and footer links that pointed at `/laws` still land on working pages
**Plans**: TBD
**UI hint**: yes

### Phase 11: Site — England Instance
**Goal**: England laws are browsable on the same site, correctly presented as English-language UK law, with Israel's pages untouched
**Mode:** mvp
**Depends on**: Phase 9, Phase 10
**Requirements**: UKSITE-02, UKSITE-03, UKSITE-04, UKSITE-05
**Success Criteria** (what must be TRUE):
  1. England laws stored at `laws/uk/england/` render at `/laws/england/...` from a second Docusaurus docs instance with its own sidebar — adding `laws/uk/scotland/` later requires no restructure of paths or config shape
  2. An England law page serves `lang="en" dir="ltr"` with UK-correct JSON-LD and no Hebrew/RTL styling, Hebrew status fallbacks, or Israeli jurisdiction metadata leaking onto it; Israel pages render exactly as before
  3. Non-numeric UK law IDs sort and group correctly in the sidebar and appear in generated law metadata — nothing silently dropped by the numeric-ID assumption
  4. The homepage "Pick a country" grid and the navbar both offer an England entry (flag/label matching the Israel pattern) that reaches the England law index
  5. Every England law page displays the OGL v3 attribution, using the alternate wording where `dc:publisher` requires it
**Plans**: TBD
**UI hint**: yes
**Design note (added 2026-08-09, not new scope):** `laws/uk/england/` and its site hierarchy should be designed as one instance of a general **country → subdivision → law** pattern — the same shape will eventually be needed for USA (federal + state), the EU (supranational + member state), and other UK nations — rather than UK-specific special-casing. Countries with no subdivision (Israel, most others) must degrade cleanly to the existing flat structure, not be forced through a redundant empty subdivision layer. USA/EU are not being built now; this only affects how Phase 11's country/subdivision plumbing is shaped.

### Phase 12: Cross-Reference + Amendment Linking
**Goal**: A reader can follow any citation and can see, from both directions, how a law has been amended
**Mode:** mvp
**Depends on**: Phase 9, Phase 10
**Requirements**: UKLINK-01, UKLINK-02, UKLINK-03
**Success Criteria** (what must be TRUE):
  1. `Citation`/`CitationSubRef` targets inside the converted batch render as working internal links, and targets outside it render as explicit legislation.gov.uk links — the validator reports zero silent or broken references
  2. Every converted law ends with a list of the amendments affecting it, each linked where the amending instrument is in the batch
  3. In an amending Act, each amending provision links inline, at that exact point in its own text, back to the specific provision it amends
  4. Re-running the linker is idempotent — no duplicated links and no churn in `git diff`
**Plans**: TBD

### Phase 13: Starter Batch + Deploy
**Goal**: The England starter batch is live on the public site next to Israel, and a reader can go from the homepage to a specific England provision in a few clicks
**Mode:** mvp
**Depends on**: Phase 8, Phase 9, Phase 11, Phase 12
**Requirements**: None — integration phase; verifies Phases 8–12 requirements at batch scale (see Coverage note)
**Success Criteria** (what must be TRUE):
  1. The England starter batch (10 Acts or fewer, per the Phase 8 fetch cap) is converted, validated (round-trip, numbering, and link checks all clean), linked, and committed under `laws/uk/england/`
  2. `npm run build` succeeds on the combined Israel + England corpus with zero broken links
  3. The deployed site (`USE_SSH=true GIT_USER=Yuvaldv npm run deploy`) serves England laws at `/laws/england` while Israel's pre-rebase URLs still redirect correctly
  4. A reader landing on the homepage can pick England, browse to a specific Act, and reach a specific section anchor without a dead end
**Plans**: TBD

---

## Progress — v1.1

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 7. Shared Pipeline Core | 0/? | Not started | - |
| 8. UK Acquisition | 0/? | Not started | - |
| 9. CLML → Markdown Conversion | 0/? | Not started | - |
| 10. Site — Route Rebase | 0/? | Not started | - |
| 11. Site — England Instance | 0/? | Not started | - |
| 12. Cross-Reference + Amendment Linking | 0/? | Not started | - |
| 13. Starter Batch + Deploy | 0/? | Not started | - |

---

## Coverage — v1.1

| REQ-ID | Phase |
|--------|-------|
| UKFETCH-01 | Phase 8 |
| UKFETCH-02 | Phase 8 |
| UKFETCH-03 | Phase 8 |
| UKCONV-01 | Phase 9 |
| UKCONV-02 | Phase 9 |
| UKCONV-03 | Phase 9 |
| UKCONV-04 | Phase 9 |
| UKCONV-05 | Phase 9 |
| UKCONV-06 | Phase 9 |
| UKCONV-07 | Phase 9 |
| UKCONV-08 | Phase 9 |
| UKCONV-09 | Phase 9 |
| UKCONV-10 | Phase 9 |
| UKVALID-01 | Phase 9 |
| UKVALID-02 | Phase 9 |
| UKLINK-01 | Phase 12 |
| UKLINK-02 | Phase 12 |
| UKLINK-03 | Phase 12 |
| UKSITE-01 | Phase 10 |
| UKSITE-02 | Phase 11 |
| UKSITE-03 | Phase 11 |
| UKSITE-04 | Phase 11 |
| UKSITE-05 | Phase 11 |

**Coverage: 23/23 v1.1 requirements mapped, each to exactly one phase.**

**Note on requirement-free phases:** Phase 7 (enabling refactor — zero behavior change, no user-visible delivery) and Phase 13 (integration + deploy — proves Phases 8–12 at batch scale) carry no v1.1 requirement of their own. Both are dependency-driven, not requirement-driven, and both have their own observable exit criteria. All 23 v1.1 requirements map to Phases 8–12.

---

*Created: 2026-05-08*
*Updated: 2026-05-08 — Phase 1 plans finalized (3 plans, wave structure 1→2→3)*
*Updated: 2026-08-09 — Milestone v1.1 (UK Laws, England only) added as Phases 7–13; v1.0 Phases 1–6 unchanged*
*Updated: 2026-08-09 — Roadmap approved; Phase 8/13 capped at 10 Acts or fewer for the initial fetch (user constraint)*
