# Requirements — Codex Civica

**Defined:** 2026-08-09
**Core Value:** Anyone — lawyer, student, or citizen — can find and read any Israeli law in plain, readable form in under 30 seconds.

> Scope: Milestone v1.1 — UK Laws (England only): pipeline + law directory.
> v1.0 (Israeli Basic Laws) requirements are tracked separately in PROJECT.md's carried-over Active section; this file is scoped to v1.1.

---

## v1.1 Requirements

### UK — Acquisition (Fetch)

- [ ] **UKFETCH-01**: User can run a fetch script that downloads England-extent Acts (`ukpga`/`aep`, extent including `E`) as CLML XML from legislation.gov.uk into `data/raw/uk/xml/`, respecting the mandatory 5s crawl-delay and User-Agent requirement
- [ ] **UKFETCH-02**: Fetch gates on `NumberOfProvisions > 0` and presence of `<Body>`/`<Schedules>`, skipping PDF-only stub documents with a logged reason instead of writing an empty law file
- [ ] **UKFETCH-03**: Fetch records the resolved `DocumentURI` and derived version for each item, restricting the starter batch to `ukpga` items with a genuine revised version (never silently mixing `/enacted` and `/revised` content)

### UK — Conversion (CLML → Markdown)

- [x] **UKCONV-01**: User can run a convert script that parses CLML into Markdown preserving exact hierarchy (Part → Chapter → section → subsection → paragraph) and verbatim `<Pnumber>` numbering, including Roman numerals and inserted (`19A`-style) numbers
- [x] **UKCONV-02**: `P1group/Title` renders as the section heading directly (not as a floated Israel-style margin-note block)
- [x] **UKCONV-03**: Every converted law's frontmatter includes rich metadata from `ukm:Metadata` (title, long title, year, chapter number, enactment date, `DocumentMainType`, `DocumentStatus`, `dct:valid`), an "as at {date}" field, and an unapplied-amendment-count disclosure banner rendered whenever `ukm:UnappliedEffects` is non-empty
- [x] **UKCONV-04**: Territorial extent (`RestrictExtent`) is shown at the provision level whenever an Act carries mixed extents, even within the England-only starter batch
- [x] **UKCONV-05**: Repealed and prospective provisions (`@Status="Repealed"/"Prospective"`) are retained in the output and explicitly marked — never silently deleted or rendered as current law
- [x] **UKCONV-06**: Amendment markup (`Addition`/`Substitution`/`Repeal`) renders bracket-and-footnote style — exact inserted/repealed text shown inline with a footnote citing the amending instrument
- [x] **UKCONV-07**: `BlockAmendment` quoted text (text quoted from another Act) renders as clearly-marked quoted content — never as this document's own operative provisions or headings
- [x] **UKCONV-08**: Schedules render with their enabling-section back-link preserved as an explicit annotation
- [x] **UKCONV-09**: Stable per-provision anchors match legislation.gov.uk's own id scheme (e.g. `section-1-1-a`)
- [x] **UKCONV-10**: A defined-term index is generated per law from CLML's `<Term>` elements

### UK — Validation

- [x] **UKVALID-01**: User can run a validator that proves round-trip losslessness — every source `<Text>` node appears verbatim in the rendered output — as a hard phase-exit gate
- [x] **UKVALID-02**: Validator checks UK-specific numbering continuity that tolerates legitimate gaps (repealed sections) and alphanumeric suffixes, rather than reusing Israel's inference-based validator

### UK — Linking

- [ ] **UKLINK-01**: `Citation`/`CitationSubRef` elements resolve to a local slug when the target is in the converted batch, or an explicit external legislation.gov.uk link otherwise — never a silent broken reference
- [ ] **UKLINK-02**: Every amendment affecting a given document is listed at the end of that original document
- [ ] **UKLINK-03**: Each amendment document links inline, at the specific point in its own text, back to the original provision it amends

### UK — Site Integration

- [x] **UKSITE-01**: Israel's Docusaurus route is rebased from `/laws` to `/laws/israel`, with `@docusaurus/plugin-client-redirects` covering all 111 existing indexed URLs (verified via build + redirect check, zero 404s)
- [ ] **UKSITE-02**: A second Docusaurus docs instance serves England content at `/laws/england`, stored on disk at `laws/uk/england/` — leaving room for `laws/uk/scotland/` etc. later without a reshuffle
- [ ] **UKSITE-03**: `DocItem/Content`, `generate-law-meta.js`, and `lawSort.js` read a country/jurisdiction discriminator instead of hardcoding Hebrew/RTL/Israel — England pages render `lang="en" dir="ltr"` with correct JSON-LD, and non-numeric UK law IDs are not dropped from sidebar grouping
- [ ] **UKSITE-04**: Homepage "Pick a country" grid and navbar both gain an England entry (flag/label matching the existing Israel pattern)
- [ ] **UKSITE-05**: OGL v3 attribution (including the conditional EU/Westlaw variant where `dc:publisher` requires it) is displayed on every England law page

---

## v1.2+ Requirements (deferred)

### Additional UK Coverage

- Statutory Instruments (`uksi`) — not revised on the source site (as-made text only); mixing with Acts would silently conflate two meanings of "current"
- Scotland, Wales, Northern Ireland legislation (`asp`/`asc`/`anaw`/`mwa`/`nia`) — same CLML dialect, zero parser cost, but a different legal system/devolved body per nation; deliberately deferred
- Welsh bilingual Senedd Acts — both English and Welsh texts are equally authoritative; publishing English-only would be a fidelity failure, moot until Wales is in scope
- Point-in-time version browsing (date picker, as-enacted/as-amended toggle) — git history covers most of this value at a fraction of the cost
- Explanatory Notes
- Tier B / large documents (>1MB XML, e.g. Companies Act 2006) — blocked on a page-splitting strategy decision
- Git-versioned amendment history via scheduled re-fetch (user deferred this differentiator for v1.1)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| OCR / Tesseract for UK content | legislation.gov.uk provides structured CLML XML — no scanned/noisy source exists for the in-scope batch |
| Gemini/LLM reconciliation in the UK text path | CLML is a single authoritative witness with nothing to reconcile; introducing an LLM here would risk paraphrasing text CLAUDE.md requires be preserved verbatim |
| Shared pipeline framework/interface across Israel and UK | Two data sources is not evidence for an abstraction (CLAUDE.md: "do not over-abstract"); only the ~150 lines that are genuinely country-blind (frontmatter split, progress tracking, deploy) are extracted to `pipeline/common/` |
| LLM use beyond metadata-only category classification | UK data lacks a subject-taxonomy field (unlike Israel's ministry/category tables); classification never touches law body text |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UKFETCH-01 | Phase 8 — UK Acquisition | Pending |
| UKFETCH-02 | Phase 8 — UK Acquisition | Pending |
| UKFETCH-03 | Phase 8 — UK Acquisition | Pending |
| UKCONV-01 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKCONV-02 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKCONV-03 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKCONV-04 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKCONV-05 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKCONV-06 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKCONV-07 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKCONV-08 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKCONV-09 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKCONV-10 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKVALID-01 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKVALID-02 | Phase 9 — CLML → Markdown Conversion | Complete |
| UKSITE-01 | Phase 10 — Site: Route Rebase | Complete |
| UKSITE-02 | Phase 11 — Site: England Instance | Pending |
| UKSITE-03 | Phase 11 — Site: England Instance | Pending |
| UKSITE-04 | Phase 11 — Site: England Instance | Pending |
| UKSITE-05 | Phase 11 — Site: England Instance | Pending |
| UKLINK-01 | Phase 12 — Cross-Reference + Amendment Linking | Pending |
| UKLINK-02 | Phase 12 — Cross-Reference + Amendment Linking | Pending |
| UKLINK-03 | Phase 12 — Cross-Reference + Amendment Linking | Pending |

**Coverage:**
- v1.1 requirements: 23 total
- Mapped to phases: 23 ✓
- Unmapped: 0
- Phases 7 (Shared Pipeline Core) and 13 (Starter Batch + Deploy) carry no requirement of their own — Phase 7 is a zero-behavior-change enabling refactor, Phase 13 is the integration/deploy phase that proves Phases 8–12 at batch scale. Both have their own observable exit criteria in ROADMAP.md.

---
*Requirements defined: 2026-08-09*
*Last updated: 2026-08-09 — traceability populated from milestone v1.1 roadmap (Phases 7–13)*
