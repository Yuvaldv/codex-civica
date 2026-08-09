# Project Research Summary

**Project:** Codex Civica — Milestone v1.1 (UK Laws — England only)
**Domain:** Public legal-text publishing — structured-XML ingestion (legislation.gov.uk / CLML) into a deterministic Markdown pipeline, added as a second jurisdiction to an existing Docusaurus site
**Researched:** 2026-08-09
**Confidence:** HIGH

## Executive Summary

The UK milestone is architecturally the opposite of the Israel milestone, and every research file independently reaches the same conclusion: **legislation.gov.uk is not a reconstruction problem, it is a rendering problem.** UK primary legislation is published as CLML (Crown Legislation Markup Language), an XSD-validated XML dialect that already encodes hierarchy (`Part`→`Chapter`→`P1group`→`P1`→`P2`→`P3`→`P4`), verbatim numbering (`<Pnumber>`), resolved cross-reference targets (`Citation/@URI`), and structurally-attached section headings (`P1group/Title`). The LAYER1–3 architecture in `CLAUDE.md` (native extraction → OCR → Gemini reconciliation) exists specifically because Knesset PDFs are a *noisy witness*; CLML is a single authoritative witness with nothing to reconcile, so introducing an LLM into the UK text path would violate `CLAUDE.md`'s own fidelity rules rather than serve them. All four researchers converge: no Tesseract, no Gemini/Claude in the conversion path, `pipeline/uk/clml.py` → IR → `render.py` is a deterministic tree walk, and the existing Israel pipeline (`fetch_laws.py`, `extract_native.py`, `extract_ocr.py`, `reconcile.py`, `link_resolver.py`) is left untouched as a sibling, not a shared codepath.

The recommended approach is: fetch a hand-picked Tier A starter batch of Westminster `ukpga`/`aep` Acts via `data.xml` (rate-limited at the mandatory 5s crawl-delay, no bulk download exists), parse to a typed intermediate representation with `lxml`, render deterministically to Markdown, and validate via *round-trip fidelity checks* (does every source `<Text>` node appear verbatim in the output?) rather than the Israel-style *inference* validators (numbering-continuity, orphan-subsection), which would false-positive-flood on CLML's legitimate structural gaps (repealed sections, `19A`-style inserted numbers, `BlockAmendment` quoted text). PITFALLS.md and FEATURES.md both stress that CLML's near-total structural clarity does not mean "no editorial risk" — it relocates the risk from *garbled text* (Israel's problem) to *silently dropped legal meaning*: unapplied amendments (`ukm:UnappliedEffects`, up to 309 on Data Protection Act 2018), prospective/repealed provisions embedded in the "current" XML, territorial extent varying mid-sentence (`RestrictExtent`), and quoted `<BlockAmendment>` text that looks like a real provision but isn't. A second, independent risk cluster is site-integration correctness: the existing Docusaurus site hardcodes Hebrew/RTL (`lang="he" dir="rtl"`, `og:locale he_IL`, JSON-LD `legislationJurisdiction: Israel`) globally and unconditionally, and its sidebar/meta-generation scripts assume numeric Israeli law IDs — without deliberate country-discriminator work, the first UK page ships mislabeled as Hebrew/Israeli law. Because v1.1 is explicitly scoped to **England only** (per `PROJECT.md`, added after this research was launched), the UK-wide framing in all four files should be read narrowly: Westminster `ukpga` Acts extending to England (via `E`, `E+W`, `E+W+S`, `E+W+S+N.I.` extents), with devolved-nation content (`asp`/`asc`/`anaw`/`mwa`/`nia`) and Welsh bilingual text explicitly out of scope — which happens to align cleanly with what all four researchers already recommended deferring to v1.2+ on independent technical grounds.

**One open decision was not resolved by research and must go to the user before roadmapping**: ARCHITECTURE.md recommends rebasing the existing Israel Docusaurus `routeBasePath` from `laws` to `laws/israel` *now*, to make room for a clean, symmetric second-country instance (`laws/uk`). PITFALLS.md recommends the opposite — leave Israel at `/laws` and give UK an asymmetric route (e.g. `laws/uk`), specifically to avoid breaking the 111 already-deployed, freshly-SEO-indexed Israel URLs and their JSON-LD `url` fields. Both are internally coherent and well-argued; this is a judgement call about SEO risk tolerance, not a research gap. See "Open Decision" below.

## Key Findings

### Recommended Stack

Net new hard dependencies are effectively zero. Everything required — `requests`, `lxml`, `python-frontmatter`, `PyYAML`, `tqdm`, `tenacity` — is already installed in `~/.venv-codex` and already used by the Israel pipeline. The single genuinely new, recommended-but-optional package is `requests-cache` (for free, fast local re-runs during development). `lxml.etree` (not `xml.etree.ElementTree`, not `beautifulsoup4`) is required for namespace-aware XPath and offline XSD validation against the published `legislation.xsd`.

**Core technologies:**
- **legislation.gov.uk API** (`/data.xml`) — sole data source; no auth, no API key; official National Archives service — chosen because it is the *native*, most-accurate representation (verified live against 15+ real Acts)
- **CLML** (Crown Legislation Markup Language) — the XML dialect to parse; hierarchy, numbering, and cross-references are all explicit, eliminating the single hardest problem in the Israel pipeline (hierarchy inference) entirely
- **lxml 6.1.0** (already installed) — XPath tree walking + XSD validation; C-backed, handles the 3.5 MB Equality Act 2010 case and CLML's multi-namespace documents (`legislation`, `ukm`, `dc`, `dct`, `atom`, `xhtml`, `mathml`)
- **requests + tenacity** (already installed) — sequential HTTP fetch with retry/backoff on `403`/`202`; concurrency is explicitly disallowed by the mandatory 5s `Crawl-delay`
- **python-frontmatter + PyYAML** (already installed) — reused verbatim from the Israel pipeline so both countries share one frontmatter contract

**Explicitly rejected for the UK path:** Tesseract/`pytesseract`, `pymupdf`/`pdfplumber`/`pdftotext`, Gemini Flash/`anthropic` reconciliation, `xmlschema` (redundant with `lxml`), `saxonche`/XSLT (unnecessary complexity for this milestone).

### Expected Features

**Must have (table stakes) — England-filtered from FEATURES.md's UK-wide list:**
- Full statutory text of Westminster `ukpga` Acts extending to England, verbatim, with exact hierarchy (Part→Chapter→cross-heading→section→subsection→paragraph) and verbatim `<Pnumber>` numbering, including Roman numerals and `19A`-style inserted numbers
- `P1group/Title` rendered as the section heading (**not** as an Israel-style margin-note block — this is the most important "don't blindly copy Israel" call across all four files)
- Schedules with their enabling-section `<Reference>` preserved as an explicit back-link annotation
- Rich frontmatter from `ukm:Metadata` (title, long title, year, chapter number, enactment date, `DocumentMainType`, `DocumentStatus`, `dct:valid`)
- **"As at {date}" + unapplied-amendment disclosure** — a correctness requirement, not a nice-to-have, given the source itself discloses staleness (HRA 1998: 5 pending; Equality Act 2010: 24)
- Territorial extent shown (`RestrictExtent`) — required even in an England-only v1.1, because Westminster Acts commonly carry mixed extents (e.g. a provision that is Scotland-only inside an otherwise UK-wide Act) and England-only scoping is a *selection* filter on the batch, not a reason to drop extent display
- Repealed/prospective provisions retained and explicitly marked, never silently deleted or silently rendered as current law
- Cross-reference links resolved from `Citation`/`CitationSubRef` (already carry target URIs — no Gemini-style extraction needed)
- OGL v3 attribution (exact wording specified by TNA; conditional on `dc:publisher` for the EU/Westlaw exceptions)

**Should have (differentiators):**
- Git-versioned amendment history (re-run the fetch on a schedule; requires byte-stable deterministic rendering as a hard prerequisite)
- Provable losslessness — a round-trip validator asserting every source `<Text>` node appears verbatim in the output, which is achievable for UK and was never achievable for Israel's OCR pipeline
- Deep-linkable stable anchors matching legislation.gov.uk's own `id` scheme (`section-1-1-a`)
- Defined-term index from `<Term>` elements (already marked up in source)

**Defer past v1.1 (aligns with England-only scope):**
- Statutory Instruments (`uksi`) — not revised on the site (as-made text only); would silently mix two meanings of "current" if combined with Acts
- Devolved legislation (`asp` Scotland, `asc`/`anaw`/`mwa` Wales, `nia` Northern Ireland) — same CLML dialect, zero parser cost, but explicitly out of scope for England-only v1.1 per `PROJECT.md`
- Welsh bilingual Senedd Acts — both texts are equally authoritative in law; publishing English-only would be a fidelity failure, and it's moot for an England-only milestone
- Point-in-time version browsing (date picker, as-enacted/as-amended toggle) — git history covers ~90% of this value for ~5% of the cost
- Explanatory Notes, large Tier B Acts (>1MB) pending a page-splitting decision

### Architecture Approach

Sibling-package integration with a thin shared core: `pipeline/uk/` (or `pipeline_uk/` — naming detail, `PROJECT.md` explicitly allows "or equivalent") holds `fetch_uk.py`, `clml.py` (XML→IR), `render.py` (IR→Markdown), `validate.py`, and `link_uk.py`; `pipeline/common/` extracts exactly three things already duplicated or country-blind in the Israel codebase — frontmatter split/render, progress-file handling (`{done, failed, total_deployed, priority}`), and deploy — roughly 150 lines total. Everything else in `pipeline/` (Knesset OData, PDF extraction, OCR, Gemini reconciliation, Hebrew-regex link resolution) is genuinely Israel-specific and must not be reused or abstracted over prematurely (`CLAUDE.md`: "do not over-abstract," "two data sources is not evidence for an interface").

**Major components:**
1. **`clml.py` → IR (`ir.py`)** — the only namespace-aware module; parses CLML into typed dataclasses (`Provision`, `Run`, `LegalDoc`, `DocMeta`); unknown elements fail loudly rather than silently drop
2. **`render.py`** — pure function `IR → Markdown + frontmatter dict`; the IR is the golden-file snapshot artifact, satisfying `CLAUDE.md`'s "compare outputs before updating pipeline logic" rule for the first time in a mechanically checkable way
3. **`validate.py`** — round-trip fidelity checks (provision completeness, verbatim numbering, text conservation, citation resolution) plus a from-scratch UK numbering validator that tolerates legitimate gaps (repealed sections) and alphanumeric suffixes, replacing rather than parameterizing Israel's inference-based validator
4. **`link_uk.py`** — `Citation/@URI` → local slug or external legislation.gov.uk link; deterministic, zero-fuzzy-matching replacement for Israel's 4-pass Gemini-assisted `link_resolver.py`/`cross_linker.py`
5. **Docusaurus second docs instance** (`@docusaurus/plugin-content-docs`, `id: 'uk'`) — requires a country discriminator threaded through `DocItem/Content/index.jsx` (lang/dir/JSON-LD), `generate-law-meta.js` (namespaced `country:id` keys, no Hebrew fallback), and `lawSort.js` (non-numeric ID regex) — all three currently hardcode Israel/Hebrew and would silently mislabel or drop UK content without this work

The one legitimate LLM use case identified (consistently, across STACK/ARCHITECTURE/FEATURES) is metadata-only category classification — UK data has no subject-taxonomy field, unlike Israel's ministry/category tables — run once, persisted to the manifest, never touching law body text.

### Critical Pitfalls

1. **The 200-OK empty law** — PDF-only historic/local Acts return valid CLML with `NumberOfProvisions="0"` and no `<Body>`; a naive fetcher emits an empty Markdown file with perfect frontmatter and no error. Gate on `NumberOfProvisions > 0` and presence of `<Body>`/`<Schedules>` before writing anything.
2. **Silently getting the wrong version** — bare `/data.xml` can 301-redirect to `/enacted` for items with no revised text, and Statutory Instruments are never revised at all. Always record the *resolved* `DocumentURI` and derived `version` field; restrict the England v1.1 batch to `ukpga` items with a genuine revised version.
3. **Publishing text the source itself declares stale** — `ukm:UnappliedEffects` (up to 309 pending amendments on some Acts) lives in metadata, not body text, and is invisible to body-only extraction. This is the single worst fidelity failure available in the UK source relative to `CLAUDE.md`'s "prefer explicit uncertainty over incorrect confidence" — must surface as a frontmatter count + rendered banner.
4. **Prospective/repealed provisions and mid-sentence extent splits inside the "current" XML** — `@Status="Repealed"/"Prospective"`, `@Match="false"`, and `<Repeal Extent="S" RetainText="true">` all live in attributes that a naive `.itertext()` walk discards, producing substantively wrong law, not a formatting bug.
5. **`<BlockAmendment>` quoted text mistaken for operative provisions** — Acts routinely quote replacement text from *other* Acts using structurally identical markup (real `<P3>`/`<Pnumber>` inside the quote); rendering it as a heading invents hierarchy and breaks numbering validation.
6. **Every UK page rendering RTL and claiming to be Hebrew/Israeli** — verified as the *current* unconditional behavior of `site/src/css/custom.css` and `DocItem/Content/index.jsx`; this is a correctness bug that must land before the first UK deploy, not a post-launch polish item.

## Open Decision — Must Go to the User Before Roadmapping

**ARCHITECTURE.md and PITFALLS.md give opposite recommendations on the Israel `routeBasePath`, and this synthesis does not pick a winner.**

| | Recommends | Rationale |
|---|---|---|
| **ARCHITECTURE.md** | Rebase Israel now: `laws` → `laws/israel`, add UK at `laws/uk`, use `@docusaurus/plugin-client-redirects` for the 111 old URLs | Symmetric structure for every downstream consumer (`lawSort.js`, `generate-law-meta.js`, `DocItem/Content`, homepage); cost is "near-zero today and grows monotonically" — corpus is only 111/718, no search feature yet, "inbound link equity is effectively nil" |
| **PITFALLS.md** | Leave Israel at `/laws` (unchanged); give UK an asymmetric route (e.g. `laws/uk` or `laws-uk`) | The SEO pass (JSON-LD `url`, sitemap.xml, `og:url`) shipped *this week*; the 111 pages are "already-SEO-indexed"; rebasing "breaks every indexed URL and every JSON-LD `url`"; recovery cost is rated MEDIUM–HIGH ("expect weeks of degraded search visibility") |

Both files agree redirects (`@docusaurus/plugin-client-redirects`) would be needed if rebasing happens, and both agree this is a judgement call, not a technical gap — ARCHITECTURE.md itself rates its own recommendation MEDIUM confidence and says explicitly "needs user sign-off." **The orchestrator should present both options to the user (with the trade-off framed as "urls-change-now-while-cheap" vs. "no-seo-risk-but-permanent-asymmetry") before the roadmap commits to a Docusaurus config shape**, since this decision gates Phase 4/5-equivalent work in any resulting roadmap (see below) and reversing it later is the more expensive direction.

## Implications for Roadmap

All four files, independently, converge on a build order that resolves real dependencies (frontmatter schema must exist before the site can render it; the URL-base decision must be made before the linker can emit correct relative paths). ARCHITECTURE.md's "Recommended Build Order" is the most load-bearing artifact here — it should seed the roadmap directly, filtered to England-only scope:

### Phase 1: Shared-core extraction (pipeline only, zero behavior change)
**Rationale:** Fully independent of every other phase; a proof-of-no-regression gate (`git diff --stat laws/israel/` must be empty) makes it safe to do first and cheap to skip/defer if the roadmapper prefers.
**Delivers:** `pipeline/common/{frontmatter,progress,deploy}.py`; Israel modules repointed to import from it.
**Addresses:** Prevents the "copy-paste `batch_import.py`" anti-pattern from ARCHITECTURE.md (AP-2) that would let the UK and Israel orchestrators drift.
**Avoids:** N/A directly, but sets up the codebase so later phases don't duplicate logic.

### Phase 2: UK acquisition (fetch)
**Rationale:** Must exist before anything can be parsed; establishes the England-filtered starter-batch manifest.
**Delivers:** `pipeline/uk/fetch_uk.py`, per-year `data.csv` enumeration → `manifest_uk.json`, cached CLML XML under `data/raw/uk/xml/`.
**Addresses:** FEATURES.md's Tier A starter-batch selection (structural diversity, not just fame) — filtered to Acts whose `RestrictExtent` includes England (`E`, `E+W`, `E+W+S`, `E+W+S+N.I.`), excluding `asp`/`asc`/`anaw`/`mwa`/`nia` outright.
**Avoids:** Pitfall 1 (bodyless 200-OK stubs — hard gate on `NumberOfProvisions > 0`), Pitfall 15 (rate-limit/fair-use violations — mandatory User-Agent, 5s crawl-delay, cache-first), Pitfall 16 (Atom/CSV pagination truncation), Pitfall 17 (regnal-year URI identity collisions).

### Phase 3: CLML → Markdown (the core of the milestone)
**Rationale:** The renderer must exist and its frontmatter schema must be frozen before the site or linker can depend on it.
**Delivers:** `pipeline/uk/ir.py`, `clml.py`, `render.py`, `validate.py`, and 3+ golden fixtures (short Act, Act with Schedules, Act with heavy amendment markup).
**Uses:** `lxml` tree walk into the typed IR described in ARCHITECTURE.md.
**Implements:** The deterministic-render architecture component; explicit policy decisions required here per PITFALLS.md — how to render `Addition`/`Substitution`/`Repeal` (bracket-and-footnote vs. clean-with-disclosure), how to handle `Status="Prospective"/"Repealed"`, how to render `BlockAmendment` as clearly-marked quoted content.
**Avoids:** Pitfalls 3–7 (unapplied effects, prospective/repealed provisions, extent, BlockAmendment, stripped amendment markup) and Pitfall 8 (no LLM in this path — enforced by a verbatim round-trip check as the phase exit criterion).

### Phase 4: Site — route decision + Israel-side implementation
**Rationale:** ARCHITECTURE.md is explicit that this must land *before* any UK docs exist, so exactly one variable changes at a time; it is also gated on the open routeBasePath decision above.
**Delivers:** Whichever route-base option the user selects, implemented and verified against the existing 111 Israel pages (redirects + regenerated sitemap if rebasing; unchanged config if not).
**Implements:** The Docusaurus multi-instance groundwork (`plugin-content-docs` id/path/routeBasePath uniqueness rules).
**Avoids:** Pitfall 13 (URL/SEO trap from editing the preset in place or rebasing carelessly).

### Phase 5: Site — second country (UK/England)
**Rationale:** Needs at least one real converted Markdown file from Phase 3 to prove `generate-law-meta.js` against real UK frontmatter fields; needs Phase 4's route base settled.
**Delivers:** `uk` docs plugin instance, `sidebarsUk.ts`, country-discriminator plumbing (`jurisdiction.ts` or equivalent), scoped RTL CSS, country-aware `lawSort.js`/`generate-law-meta.js`, homepage country grid entry, navbar 🇬🇧 flag.
**Addresses:** The `PROJECT.md` requirement that the directory structure "leave room for" Scotland/Wales/NI later without a reshuffle — this is the point in the roadmap where the `laws/uk/england/`-style nation subfolder (rather than the flat `laws/uk/` some research files describe) should be decided and locked in, since it is cheaper to establish now than to retrofit once content exists.
**Avoids:** Pitfall 10 (RTL/Hebrew leakage — the single highest-consequence, must-land-before-deploy item across all four files), Pitfall 11 (Israel-shaped metadata pipeline / Hebrew status-badge fallback), Pitfall 12 (numeric-ID-regex silently dropping UK entries from the sidebar).

### Phase 6: Cross-reference linking
**Rationale:** Depends on the final route base (Phase 4) for correct relative link generation, and on the batch existing (Phase 2/3) to know what's internal vs. external.
**Delivers:** `link_uk.py` — `Citation/@URI` → local slug for in-batch targets, outbound legislation.gov.uk link otherwise; priority-queue emission mirroring the Israel `import_progress.json` contract.
**Uses:** The pre-resolved `Citation`/`CitationSubRef` URIs — described in all four files as the single biggest architectural win of this milestone, since it eliminates the need for anything resembling `cross_linker.py`'s Gemini extraction.
**Avoids:** Broken/dead internal links (FEATURES.md UX pitfall) — resolve or fall back to an explicit external link, never a silent broken reference.

### Phase 7: Starter batch conversion + deploy
**Rationale:** Final integration phase; everything upstream must be proven on fixtures before running across the full batch.
**Delivers:** England-filtered starter batch (Tier A candidates, England-extent-only) converted, validated, linked, and deployed via the existing `USE_SSH=true GIT_USER=Yuvaldv npm run deploy` workflow.
**Addresses:** The `PROJECT.md` v1.1 target features directly — pipeline built, starter batch converted, directory wired into Docusaurus, 🇬🇧 entry live.

### Phase Ordering Rationale

- Phase 1 is fully independent and could be reordered or dropped without blocking anything else, but deferring it risks the `batch_import.py` duplication anti-pattern (ARCHITECTURE.md AP-2).
- Phases 2 and 3 must precede any site work because the frontmatter schema — the "API" between pipeline and site per ARCHITECTURE.md's Internal Boundaries table — must be real before `generate-law-meta.js` can be updated to read it.
- Phase 4 must precede Phase 5 specifically to isolate the highest-risk, highest-blast-radius site change (whichever way the routeBasePath decision goes) from the purely additive change of adding a second country — this is ARCHITECTURE.md's explicit reasoning and it holds regardless of which routeBasePath option is chosen.
- Phase 6 depends on Phase 4's final route shape for relative-link correctness.
- The England-only scope constraint is enforced primarily in Phase 2 (batch filtering by extent + type code) and Phase 5 (directory structure choice) — it does not require a structurally different pipeline, since Westminster `ukpga` legislation is the correct source regardless of which UK nation is in scope; England-only is a *selection and directory-layout* decision, not an architecture decision.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (CLML → Markdown):** The amendment-markup rendering policy (bracket-and-footnote vs. clean-with-disclosure) and the `BlockAmendment`/`Tabular`/`Figure` edge cases are design decisions with real fidelity consequences — worth a focused pass before implementation, even though the underlying CLML structure is well-documented.
- **Phase 4/5 (Site routing + second country):** Depends entirely on the user's answer to the open routeBasePath decision; the chosen option's exact Docusaurus config (multi-instance plugin, redirects plugin version pinning) should be re-verified against the installed Docusaurus version at implementation time.

Phases with standard patterns (skip research-phase):
- **Phase 1 (shared-core extraction):** Mechanical refactor of already-read, already-duplicated code; no new information needed.
- **Phase 2 (UK acquisition):** Fetch endpoints, rate limits, and pagination behavior are all verified live and documented in STACK.md/ARCHITECTURE.md/PITFALLS.md with HIGH confidence.
- **Phase 6 (linking):** `Citation/@URI` resolution is a well-specified, verified data contract with no open design questions.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All version numbers and API behavior verified via live `curl`/`lxml` probes against legislation.gov.uk (2026-08-09) plus official TNA/CLML documentation; installed-package versions confirmed via `pip list` |
| Features | HIGH | Structural claims verified against live CLML XML across 30+ Acts spanning 1297–2023; feature landscape corroborated by direct schema-source reading |
| Architecture | HIGH for CLML structure and existing-codebase integration points (read directly from source); MEDIUM specifically for the routeBasePath recommendation, which both ARCHITECTURE.md and this synthesis treat as a judgement call requiring user sign-off, not a research conclusion |
| Pitfalls | HIGH for legislation.gov.uk behavior and Codex Civica integration pitfalls (verified live + read from source); MEDIUM for LLM-reconciliation advice (reasoned from `CLAUDE.md` + `reconcile.py`'s design, not from external post-mortems of similar LLM-in-legal-pipeline projects) |

**Overall confidence:** HIGH

### Gaps to Address

- **routeBasePath decision (open, see above):** Not a research gap — a product decision the orchestrator must take to the user before any Docusaurus config work begins.
- **Directory layout for nation subfolder:** `PROJECT.md` requires structure that "leaves room for" Scotland/Wales/NI without a reshuffle (e.g. `laws/uk/england/`), but STACK.md/ARCHITECTURE.md's suggested layouts (`laws/uk/*.md` flat with a `jurisdiction`/`class` frontmatter field) predate this explicit requirement. Roadmapper should decide whether the nation segment lives in the *path* (`laws/uk/england/ukpga-1998-42.md`) or purely in *frontmatter* with a flat `laws/uk/` directory — both satisfy "no reshuffle later," but they have different Docusaurus sidebar/routing implications and should be settled explicitly in Phase 5, not left implicit.
- **Amendment-markup rendering policy (Pitfall 7):** Two defensible options (faithful bracket-and-footnote vs. clean-with-disclosure) with no clear winner in research — a design call for Phase 3.
- **Large-document page-splitting strategy:** Explicitly out of scope for the Tier A starter batch (all research files agree), but flagged as a hard blocker for any Tier B expansion (Companies Act 2006 at 15 MB XML, Data Protection Act 2018 at 5.8 MB) — not needed for v1.1 roadmap phases but should be logged as a known future constraint.
- **`pipeline/uk/` vs `pipeline_uk/` naming:** STACK.md and ARCHITECTURE.md use different top-level naming for the new pipeline package; `PROJECT.md` itself says "`pipeline_uk/` (or equivalent)," so this is a low-stakes implementation detail for the roadmapper/planner to settle once, not a conflict requiring escalation.

## Sources

### Primary (HIGH confidence)
- Live API calls to `www.legislation.gov.uk` (2026-08-09) — 30+ probes across `aep/1297/9`, `ukpga/1911/13`, `ukpga/1972/68`, `ukpga/1998/42` (+`/enacted`, `/2010-01-01`), `ukpga/2010/15`, `ukpga/2005/4`, `ukpga/1978/30`, `uksi/2020/1500`, `ukla/1988/1`, `ukla/1990/1`, `ukpga/1957/20`, `asp/2009/12`, `asc/2015/2` (+`/welsh`), and others — XML structure, rate limits, redirects, PDF-only detection, pagination
- https://www.legislation.gov.uk/robots.txt (fetched live) — `Crawl-delay: 5`, `Disallow: */data.pdf`
- https://legislation.github.io/data-documentation/ (API overview, fair-use policy, what-we-have coverage matrix, reuse licence) — endpoints, rate limits, OGL v3 attribution requirements
- https://github.com/legislation/clml-schema + https://legislation.github.io/clml-schema/ — authoritative CLML element semantics (`P1group/Title`, `MarginNotes` deprecation rationale, `Repeal`/`Addition`/`Substitution`)
- Codex Civica source read directly: `pipeline/{batch_import,reconcile,link_resolver,cross_linker,fetch_laws}.py`, `site/{docusaurus.config.ts,sidebars.ts,package.json}`, `site/src/{pages/index.tsx,clientModules/lawSort.js,theme/DocItem/Content/index.jsx,css/custom.css}`, `site/scripts/generate-law-meta.js`, `CLAUDE.md`, `.planning/PROJECT.md`
- PyPI JSON API + `~/.venv-codex pip list` — confirmed no third-party UK-legislation Python library exists; confirmed installed dependency versions

### Secondary (MEDIUM confidence)
- i-dot-ai `lex` project README (UK government AI incubator legislation.gov.uk ingestion) — cache-first crawling guidance, real-world crawl-duration data point
- `research.legislation.gov.uk` bulk dataset page — returned 401 Unauthorized; contents/licence unverified, treated as unavailable

---
*Research completed: 2026-08-09*
*Ready for roadmap: yes, pending user decision on the routeBasePath open question above*
