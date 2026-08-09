# Feature Research — UK Legislation (Codex Civica v1.1)

**Domain:** Public legal-text publishing — UK primary legislation from a structured official XML source
**Researched:** 2026-08-09
**Confidence:** HIGH (all structural claims verified against live CLML XML fetched from legislation.gov.uk and against the published XSD source in `github.com/legislation/clml-schema`)

---

## Headline Finding

**The UK is not a reconstruction problem. It is a rendering problem.**

legislation.gov.uk publishes every Act as **CLML** (Crown Legislation Markup Language) — schema name verified, namespace `http://www.legislation.gov.uk/namespaces/legislation`, XSD at `https://www.legislation.gov.uk/schema/legislation.xsd`. The hierarchy is fully and explicitly encoded. Every provision carries a stable machine ID and a canonical URI. Cross-references are already marked up with resolved target URIs.

This means the LAYER 1–3 architecture in `CLAUDE.md` (native extraction → OCR → Gemini reconciliation) **does not apply to the UK at all**. There is no noise to reconcile. The five conservative-fidelity rules still bind, but they become *cheap and provable* rather than expensive and probabilistic: with CLML you can validate that the Markdown is a lossless projection of the source, which the Israel pipeline can never do.

The feature work therefore shifts from *recovering* legal structure to *deciding what to publish* about a text that is (a) constantly amended, (b) territorially variable, and (c) knowingly incomplete relative to the statute book.

---

## Answers to the Five Questions

### Q1. Structural hierarchy — is it consistent, and does CLML encode it?

**Yes, explicitly. Verified.** Element vocabulary is uniform across the entire corpus; only the *depth used* varies per Act.

Verified structure (from live XML of the Human Rights Act 1998, `ukpga/1998/42/data.xml`):

```
Legislation
├── ukm:Metadata            (Dublin Core + ukm: legislative metadata)
├── Primary | Secondary
│   ├── PrimaryPrelims      Number, LongTitle, DateOfEnactment, PrimaryPreamble/EnactingText
│   ├── Body
│   │   └── Part → Chapter → Pblock → P1group → P1 → P1para → P2 → P2para → P3 → P4
│   └── Schedules
│       └── Schedule → Number, TitleBlock/Title, Reference, ScheduleBody → Part/Chapter/P1
└── Commentaries            Commentary blocks (amendment/commencement/extent annotations)
```

| CLML element | Legal meaning | Codex Civica Markdown target |
|---|---|---|
| `Part` / `Chapter` | Part / Chapter | `#` / `##` grouping heading |
| `Pblock` + `Title` | **Cross-heading** (italic grouping heading over several sections) | grouping heading — *not* section-level |
| `P1group` + `Title` | **Section grouping; the `Title` is the section's side note** | section heading text |
| `P1` + `Pnumber` | Section (or Article, in an SI) | `## Section N` |
| `P2` + `Pnumber` | Subsection `(1)` | `###` |
| `P3` + `Pnumber` | Paragraph `(a)` | `####` |
| `P4` + `Pnumber` | Sub-paragraph `(i)` | `#####` |
| `Schedule` / `Reference` | Schedule + its enabling section | separate section; `Reference` = provenance line |

Every node carries `id` (`section-1-1-a`), `DocumentURI`, `IdURI`. Numbering comes verbatim from `<Pnumber>` — nothing is inferred, so "preserve numbering exactly" is satisfied by construction.

**Depth is not uniform — the renderer must map elements to heading levels, never assume a fixed depth.** Measured counterexamples:
- Magna Carta (1297): `Part=0 Chapter=0 Pblock=0 P1group=27 P1=26`, Roman-numeral `Pnumber`s, no subsections at all.
- Union with Scotland Act 1706: `Part=18` — the *Articles of Union* are modelled as `Part`s.
- Human Rights Act 1998: `Part` and `Chapter` appear only *inside* Schedule 1 (they carry the ECHR Articles), never in the Body.
- Constitutional Reform Act 2005: `Part=38 Chapter=6 Pblock=473 P1group=205 P1=1115`.

**Bonus, and it is a big one:** cross-references are pre-resolved in the source.

```xml
<Citation URI="http://www.legislation.gov.uk/id/uksi/2001/3500" Class="UnitedKingdomStatutoryInstrument" Year="2001" Number="3500">S.I. 2001/3500</Citation>
<CitationSubRef CitationRef="c00002" URI=".../uksi/2001/3500/article/3" SectionRef="article-3">arts. 3</CitationSubRef>
```

Israel needed a 4-pass Gemini extractor + link resolver for this. The UK gives target URI, target provision, and citation class for free.

### Q2. Margin notes — does the existing convention transfer?

**No, and it should not be reused. This is the most important "don't copy Israel" call in the milestone.**

CLML *does* define `MarginNotes` / `MarginNote` / `MarginNoteRef` (`schemaModules/schemaMarginnote.xsd`), but the schema's own documentation disqualifies them:

> "Margin notes were only used in old primary legislation (pre-2001) where the layout of the documents was different to that currently used. This also entailed a difference in structure from modern primary legislation where **the margin notes are part of the text**."
>
> "The anchor point for the margin note is somewhat arbitrary as there is nothing in the printed copy to reference the note."

Empirically confirmed: **zero `<MarginNote>` elements** across six deliberately old/diverse documents — Habeas Corpus Act 1679, Parliament Act 1911, Theft Act 1968, Interpretation Act 1978, Scotland Act 1998, and a 1998 SI. The revised database has normalised historical side notes into structure.

**What the UK side note actually is:** the mandatory `<Title>` child of `<P1group>`. XSD annotation: *"Groups together provisions or paragraphs that have a common title."* It is structurally bound to its section — the exact property Codex Civica's `> [Margin Note — Section 3(א)(1)]` convention was invented to *recover*.

**Decision:** render `P1group/Title` as the section heading. Emitting it as a margin-note block would be a **fidelity regression** — it would assert marginal metadata where the source has a first-class heading.

**Where the existing attachment machinery *should* be repurposed:** CLML `Commentary` blocks, referenced from the exact provision by `CommentaryRef`. These are typed annotations (`F` textual amendment, `C` modification, `E` extent, `I` commencement, `M` marginal citation, `X` editorial) — genuine metadata attached to specific hierarchy nodes. Measured density: Computer Misuse Act 1990 = 93 commentaries over 21 sections; Constitutional Reform Act 2005 = 456. Israel's "attach metadata to the right node, never float it globally" rule transfers here verbatim.

Also transferring directly: `SignedSection` / `Signatory` / `Signee` / `DateSigned` / `LSseal` (verified present in SIs) → the existing signatures block convention.

Not transferring at all: `[UNCERTAIN TEXT]`. There is no uncertainty in the source. If the UK renderer ever emits it, that is a bug in the renderer, not a property of the document.

### Q3. Point in time / versioning — capture or defer?

**Three independent version axes, all encoded, all real:**

1. **As-enacted vs revised.** `/enacted/data.xml` is immutable and annotation-free (HRA 1998 as-enacted: `Commentary=0`). `/data.xml` is the current revised text (`ukm:DocumentStatus="revised"`, HRA 1998: `Commentary=96`).
2. **Point in time.** `/{uri}/YYYY-MM-DD/data.xml` works — verified: `ukpga/1998/42/2010-01-01/data.xml` returns `<dct:valid>2009-10-31</dct:valid>`.
3. **Territorial extent.** `RestrictExtent` on every node (`E+W+S+N.I.`, `E+W`, `S`). Verified: Scotland Act 1998 carries both `E+W+S+N.I.` and `S` extents; Defamation Act 2013 is `E+W+S` only. Plus `Status="Repealed" | "Prospective"` on provisions, and a `Concurrent` attribute for concurrent extent-specific versions of the same provision.

**The honesty problem — this is the finding that matters.** The published revised text is knowingly *not* up to date. `ukm:UnappliedEffect` with `RequiresApplied="true"` enumerates amendments Parliament has passed that the editorial team has not yet applied to the text. Measured counts on the current revised XML:

| Act | Unapplied effects |
|---|---|
| Human Rights Act 1998 | 5 |
| Equality Act 2010 | 24 |
| Scotland Act 1998 | 28 |
| Government of Wales Act 2006 | 36 |
| Online Safety Act 2023 | 38 |
| Constitutional Reform Act 2005 | 39 |
| Freedom of Information Act 2000 | 112 |
| **Data Protection Act 2018** | **309** |

Publishing "the Data Protection Act 2018" with 309 known-pending amendments and no disclosure is exactly the failure mode `CLAUDE.md` prohibits: *"prefer explicit uncertainty over incorrect confidence."*

**Coverage floor.** Revised versions exist only for UK primary legislation at least partly in force on the base date **1 February 1991**; anything wholly repealed before then is simply absent. As-enacted is complete from 1988 (UK Local Acts from 1991, NI Statutory Rules from 1996). Verified consequence: `/enacted` returns **404** for Magna Carta (1297) and the Habeas Corpus Act 1679, but **200** for the Bill of Rights 1688 and the Act of Settlement 1700. The pipeline cannot assume `/enacted` exists.

**Call:**
- **IN SCOPE (table stakes):** capture *one* snapshot — the current revised text — and record the version metadata (`dct:valid`, `dc:modified`, `ukm:DocumentStatus`, retrieval date, `RestrictExtent`, unapplied-effect count) in frontmatter. Surface an "as at {date}; N amendments not yet applied" banner with a link to the official page.
- **DEFERRED:** point-in-time *browsing* (date picker, version-diff UI, as-enacted/as-amended toggle). Git already gives a free amendment history the moment the pipeline is re-run on a schedule — that is 90% of the value for 5% of the work.
- **Cheap insurance:** the fetcher should support a `?as_at=` parameter from day one even if the site never exposes it, so historical backfill is a re-run rather than a re-architecture.

### Q4. Starter batch — concrete Acts

Selection principle, and it differs from Israel's: **choose for structural diversity, not only for fame.** Israel's 14 Basic Laws are structurally homogeneous. The UK canon should be picked so that each Act exercises a different CLML feature, so the renderer is proven before scaling.

All identifiers below were fetched live and the sizes/counts are measured, not estimated.

#### Tier A — recommended v1.1 batch (13 Acts, ~1.1 MB of XML total)

| # | Act | URI | XML | Structure | Why this one |
|---|---|---|---|---|---|
| 1 | **Parliament Act 1949** | `ukpga/Geo6/12-13-14/103` | 9 KB | 2 sections | Smallest real Act — the smoke test |
| 2 | **Parliament Act 1911** | `ukpga/Geo5/1-2/13` | 20 KB | 8 sections | Constitutional; pairs with #1 as an amend/amended pair |
| 3 | **Fixed-term Parliaments Act 2011** | `ukpga/2011/14` | 26 KB | 29 P1, 1 Sch | Title is literally *"(repealed)"* — proves repealed-Act status rendering |
| 4 | **Bill of Rights [1688]** | `aep/WillandMarSess2/1/2` | 36 KB | 2 P1group | Archaic prose; `/enacted` exists (200) |
| 5 | **Magna Carta (1297)** | `aep/Edw1cc1929/25/9` | 38 KB | 27 P1group, Roman numerals, no Part/Chapter | Mostly repealed → dot-leader provisions; `/enacted` **404**. Best hard case in the batch |
| 6 | **Act of Settlement (1700)** | `aep/Will3/12-13/2` | 41 KB | 4 P1group, 42 citations | High citation density on a tiny Act |
| 7 | **Union with Scotland Act 1706** | `aep/Ann/6/11` | 56 KB | **Part=18** (Articles as Parts) | Proves the Part→heading mapping is not hardcoded |
| 8 | **Habeas Corpus Act 1679** | `aep/Cha2/31/2` | 57 KB | 18 P1group | `/enacted` **404** — forces the revised-only path |
| 9 | **Defamation Act 2013** | `ukpga/2013/26` | 111 KB | 23 sections, extent **E+W+S** | Proves territorial-extent display (not UK-wide) |
| 10 | **Bribery Act 2010** | `ukpga/2010/23` | 132 KB | 36 P1, 2 Sch | Clean modern Act with Schedules; zero unapplied effects |
| 11 | **Computer Misuse Act 1990** | `ukpga/1990/18` | 262 KB | 21 sections, **93 commentaries** | Extreme annotation-to-text ratio — stresses the Commentary renderer |
| 12 | **Human Rights Act 1998** | `ukpga/1998/42` | 298 KB | 57 P1, 4 Sch, Part+Chapter inside Sch 1, 5 unapplied | The single best all-round test case; also the highest-traffic constitutional Act |
| 13 | **Interpretation Act 1978** | `ukpga/1978/30` | 483 KB | 41 P1, 3 Sch, 380 citations | The Act that tells you how to read every other Act — highest cross-reference density per byte |

Together these cover: flat vs deeply nested; Roman vs Arabic numbering; Part-as-Article; Schedules with internal Parts/Chapters; repealed Acts, repealed provisions, and prospective provisions; sub-UK extents; heavy Commentary; heavy Citation; and both the `/enacted`-available and `/enacted`-404 paths.

#### Tier B — v1.2, once the renderer holds

Deliberately excluded from v1.1 on size grounds alone. Each is constitutionally essential but 5–100× the batch's per-file size, and none teaches the renderer anything Tier A doesn't.

| Act | URI | XML | Note |
|---|---|---|---|
| Freedom of Information Act 2000 | `ukpga/2000/36` | 2.0 MB | 112 unapplied effects |
| European Union (Withdrawal) Act 2018 | `ukpga/2018/16` | 1.8 MB | |
| Scotland Act 1998 | `ukpga/1998/46` | 2.3 MB | mixed `S` / UK-wide extents |
| Northern Ireland Act 1998 | `ukpga/1998/47` | 2.8 MB | 23 Schedules |
| Constitutional Reform Act 2005 | `ukpga/2005/4` | 3.1 MB | 1,115 sections |
| Online Safety Act 2023 | `ukpga/2023/50` | 3.2 MB | |
| Equality Act 2010 | `ukpga/2010/15` | 3.5 MB | 28 Schedules |
| Government of Wales Act 2006 | `ukpga/2006/32` | 4.1 MB | |
| Data Protection Act 2018 | `ukpga/2018/12` | 5.8 MB | 309 unapplied effects |

**Note:** a single Docusaurus page from the Data Protection Act 2018 would be enormous. Tier B is gated on a page-splitting decision (per-Part pages, or per-section anchors), which is precisely why it should not be in v1.1.

### Q5. Devolution — in scope or deferred?

**Deferred. Westminster-only (`ukpga`) is the correct v1.1 boundary — but for content-model reasons, not technical ones.**

Verified: devolved legislation uses **the same CLML, the same `/data.xml`, the same `P1group`/`P1`/`P2` structure**. Zero parser changes required.

| Legislature | URI prefix | `ukm:DocumentMainType` | Verified |
|---|---|---|---|
| Scottish Parliament | `asp/` | `ScottishAct` | ✓ (`asp/2009/12`, 1.0 MB) |
| Senedd Cymru (post-2020) | `asc/` | `WelshParliamentAct` | ✓ |
| National Assembly for Wales | `anaw/` | `WelshNationalAssemblyAct` | ✓ (`anaw/2015/2`) |
| Welsh Assembly Measures | `mwa/` | `WelshAssemblyMeasure` | ✓ (`mwa/2011/2`) |
| NI Assembly | `nia/` | `NorthernIrelandAct` | ✓ |

**The actual blocker is Welsh bilingualism.** Senedd legislation is enacted in English *and* Welsh, and **both texts are of equal standing**. legislation.gov.uk serves them as two parallel authoritative documents:

- `https://www.legislation.gov.uk/anaw/2015/2/data.xml` → English, 528 KB
- `https://www.legislation.gov.uk/anaw/2015/2/welsh/data.xml` → fully Welsh CLML, 591 KB, `xml:lang="cy"`, `<dc:title>Deddf Llesiant Cenedlaethau'r Dyfodol (Cymru) 2015</dc:title>`

Publishing only the English text of a Senedd Act is a **fidelity problem, not a cosmetic one** — it silently drops half of an equally authoritative enactment. The metadata even flags it: `RequiresWelshApplied="true"` appears on unapplied effects. Solving this means a bilingual content model and a language-pairing UI — a second i18n axis on top of the existing Hebrew RTL work, for zero renderer learning.

**Statutory Instruments: also deferred.** Verified trivially parseable (`Secondary` instead of `Primary`; `P1group`/`P1` with article/regulation numbering; `SignedSection` present). But the SI corpus is enormous and an SI is largely meaningless detached from its parent Act. Zero SIs in v1.1 — *but* keep the external-link fallback whenever a `Citation` points at one, exactly as Israel falls back to Knesset PDF links.

**Cheap insurance to take now (do not skip):** do not bake a Westminster assumption into paths or frontmatter. `ukm:DocumentMainType` and `ukm:DocumentClassification` are free in every document — write them into frontmatter (`class: UnitedKingdomPublicGeneralAct`, `legislature: uk-parliament`) from the first Act. Adding `asp`/`asc`/`nia` in v1.2 then becomes a content job, not a migration.

Note that **extent is unavoidable even in a Westminster-only v1.1**: `RestrictExtent` is on every node, and Defamation Act 2013 (E+W+S) is in the Tier A batch specifically to force that.

---

## Feature Landscape

### Table Stakes (users expect these)

| Feature | Why Expected | Complexity | Notes |
|---|---|---|---|
| Full statutory text, verbatim | The entire product | LOW | Deterministic CLML tree-walk. No LLM in the path |
| Exact hierarchy Part→Chapter→cross-heading→section→subsection→paragraph | A statute you can't navigate is unusable | LOW | Element→heading-level map; must not assume fixed depth |
| Numbering preserved verbatim | `CLAUDE.md` core rule; also how lawyers cite | LOW | Copy `<Pnumber>` literally, incl. Roman numerals and `4A`-style inserted numbers |
| Section side notes as headings | Every UK reader navigates by side note | LOW | `P1group/Title` — **not** the margin-note block |
| Cross-headings rendered as grouping headings | Structural in the source, meaningful to readers | LOW | `Pblock/Title`; distinct level from sections |
| Schedules, with their enabling-section reference | Half the operative content of modern Acts lives in Schedules | MEDIUM | `Schedule` + `TitleBlock` + `Reference`; Schedules can nest Part/Chapter |
| Long title, chapter number, enactment date | Standard citation furniture (`1998 c. 42`) | LOW | `Number`, `LongTitle`, `DateOfEnactment` from Prelims |
| Rich frontmatter from `ukm:Metadata` | Site already displays per-law metadata for Israel | LOW | `dc:title`, `dc:description` (long title), `ukm:Year`, `ukm:Number`, `ukm:EnactmentDate`, `ukm:ISBN`, `DocumentMainType`, `DocumentStatus`, `dct:valid` — all free |
| Internal cross-reference links | Core Codex Civica value; interlinking is the differentiator | LOW–MEDIUM | `Citation`/`CitationSubRef` already carry target URIs. Resolve to local file if converted, else link to legislation.gov.uk |
| **"As at {date}" + unapplied-amendment disclosure** | Source is knowingly stale (DPA 2018: 309 pending). Silence here is a correctness failure | LOW | `dct:valid` + count of `ukm:UnappliedEffect[@RequiresApplied='true']` |
| Repealed / prospective provisions marked, not deleted | Deleting them breaks numbering continuity | LOW | `Status="Repealed"`/`"Prospective"`; dot-leader text retained |
| Territorial extent shown | An E+W-only Act shown as "UK law" is wrong | LOW | `RestrictExtent`; needed even in Westminster-only v1.1 |
| Link back to the official page | Provenance; users must be able to check | LOW | `DocumentURI` is in the root element |
| OGL v3 attribution | Licence condition of reuse | LOW | Content is Open Government Licence v3.0 |

### Differentiators (competitive advantage)

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| **Git-versioned amendment history** | Nobody else offers `git log` on a statute. Re-run the fetch on a schedule and every amendment becomes a reviewable diff — 90% of point-in-time value, ~0% of the UI cost | MEDIUM | Requires byte-stable rendering: sort attributes, fixed whitespace, no timestamps in body |
| **Provable losslessness** | Israel can never prove its Markdown matches the PDF. UK can: assert every `P1/P2/P3/P4` and every text node round-trips | MEDIUM | Turns the validation layer from heuristics into a completeness proof |
| Amendment annotations attached to the exact provision | Commentary is where practitioners actually live; competitors bury it in footers | MEDIUM | `CommentaryRef` → typed `Commentary`; reuse Israel's "never float metadata" discipline |
| Cross-law link graph across jurisdictions | Israel ↔ UK in one site with one linking convention | MEDIUM | UK half is nearly free thanks to pre-resolved `Citation` URIs |
| Defined-term index | `<Term id="term-the-convention-rights">` is already marked up in the source — a statutory glossary for free | LOW | Verified present in HRA 1998 |
| Deep-linkable stable anchors | `id="section-1-1-a"` maps to a permanent anchor matching the official URI scheme | LOW | Anchor parity with legislation.gov.uk is a genuine usability edge |
| Plain-language *reading aids* (never rewrites) | Serves the "citizen, not just lawyer" goal without touching legal text | MEDIUM | Only ever adjacent to the text, never replacing it. Defer past v1.1 |

### Anti-Features (commonly requested, actively harmful here)

| Feature | Surface Appeal | Why Problematic | Instead |
|---|---|---|---|
| **Reuse the Israel OCR + Gemini LAYER 1–3 pipeline** | "We already built it" | legislation.gov.uk PDFs are *generated from* the CLML. OCRing them is strictly lossier than the source, and injects hallucination risk where the source is authoritative | Parse CLML directly. No OCR, no LLM in the text path |
| **Use Gemini to extract cross-references** | Mirrors Israel's 4-pass link resolver | The XML already contains resolved target URIs *and* target provisions. An LLM can only degrade this | Read `Citation` / `CitationSubRef` |
| **Full point-in-time version browser** | "The site has it, so should we" | Whole product's worth of UI; multiplies the request budget (3,000 req / 5 min / IP); nobody has asked | One current snapshot + dated frontmatter + git history |
| **Mirror the whole corpus** | "Completeness" | Hundreds of thousands of items with SIs; the rate limit makes it a multi-day crawl and a maintenance liability | Curated Tier A → Tier B. If bulk ever becomes necessary, use the research bulk dataset, not the API |
| **Drop dot-leader repealed provisions for readability** | Magna Carta looks cleaner without `. . . . . .` | Destroys numbering continuity — the Act would appear to have unexplained gaps. Violates "preserve numbering exactly" | Keep, style as repealed, show the repealing Commentary |
| **Plain-English rewrites of sections** | Serves the "readable for citizens" goal | Direct violation of "never paraphrase legal language" | Contextual reading aids beside the text, later |
| **Publish Explanatory Notes as if they were law** | They're right there and easier to read | Different document, different schema (`en.xsd`), explicitly not authoritative and not endorsed by Parliament | Defer; if ever added, render in a visually distinct non-authoritative zone |
| **Publish Senedd Acts English-only** | "It's the same CLML, just add `asc/`" | Both language texts are of equal standing; publishing one silently drops half an enactment | Defer Wales until the bilingual content model exists |
| **Infer "still in force?" from the text** | Users always ask it | Requires applying every unapplied effect — i.e. re-deriving the statute book | Report `ukm:DocumentStatus` and the title `(repealed)` suffix only; link out for the rest |
| **Reuse the `[Margin Note — ...]` block for `P1group/Title`** | Convention already exists | Asserts marginal metadata where the source has a structural heading — a fidelity regression | Render as the section heading; reuse the attachment discipline for `Commentary` instead |
| **Port Israel's inference validators unchanged** | "Validation is validation" | Israel's validators exist because structure was *guessed*. Orphan-subsection and malformed-nesting checks on CLML would only ever fire on genuine source data, i.e. false alarms | Replace with round-trip completeness validators (below) |

---

## Validation Layer — inverted for the UK

Israel validates *inferred* structure. The UK should validate *projection fidelity*, which is strictly stronger.

| Validator | Assertion |
|---|---|
| Provision completeness | Every `P1`/`P2`/`P3`/`P4` in the source appears exactly once in the Markdown |
| Numbering verbatim | Every emitted number is byte-identical to its `<Pnumber>` |
| Text conservation | Concatenated `<Text>` content ≈ Markdown body (character-count reconciliation within a tight tolerance for markup) |
| Commentary resolution | Every `CommentaryRef` resolves to a `Commentary`; no orphan commentaries |
| Citation resolution | Every `Citation`/`CitationSubRef` becomes either an internal link or an explicit external legislation.gov.uk link — never a dead reference |
| Anchor uniqueness | Every source `id` yields a unique, stable Markdown anchor |
| Schedule attachment | Every `Schedule` retains its `Reference` (enabling provision) |
| Staleness disclosure | Frontmatter carries `dct:valid` and the unapplied-effect count; build fails if absent |
| Extent present | `RestrictExtent` captured; build fails if absent |

Retained from Israel unchanged: numbering-continuity checks — but as a *warning* only, because genuine statutory gaps (repealed sections) are expected and correct.

---

## Feature Dependencies

```
CLML fetcher (URI resolution, /data.xml, rate-limit budget)
    └──requires──> Batch manifest (13 verified Tier A URIs)

CLML → Markdown renderer
    └──requires──> CLML fetcher
    └──requires──> Element→heading-level map (variable depth)

Frontmatter generator ──requires──> ukm:Metadata parser
    └──enables──> "As at {date}" staleness banner
    └──enables──> Territorial extent display
    └──enables──> laws/uk/ wired into Docusaurus

Cross-reference linker ──requires──> Renderer + a corpus manifest
    └──enhances──> Israel↔UK cross-jurisdiction link graph
    (NOTE: needs volume; a 13-Act batch yields mostly external links)

Round-trip validators ──requires──> Renderer (they compare source ↔ output)

Git amendment history ──requires──> Byte-stable deterministic rendering
    (deterministic output is a HARD prerequisite; retrofitting it invalidates all prior diffs)

Point-in-time browsing ──requires──> Version-axis data model
    ──conflicts with──> "one snapshot per law" file layout  [DEFERRED]

Devolved legislation ──requires──> Bilingual content model (Welsh)
    ──requires──> legislature/jurisdiction taxonomy in frontmatter  [DEFERRED, reserve the field now]

Tier B large Acts ──requires──> Page-splitting decision (per-Part or per-section)
    (DPA 2018 = 5.8 MB XML; single-page rendering is not viable)
```

---

## MVP Definition

### Launch with (v1.1)

- [ ] **CLML fetcher** for a hardcoded 13-URI Tier A manifest — no crawling, no discovery, respect 3,000 req / 5 min
- [ ] **Deterministic CLML → Markdown renderer** — full hierarchy, verbatim numbering, `P1group/Title` as section heading, `Pblock/Title` as cross-heading, Schedules with `Reference`
- [ ] **Frontmatter from `ukm:Metadata`** — title, long title, year, chapter number, enactment date, `DocumentMainType`, `DocumentStatus`, `dct:valid`, `RestrictExtent`, unapplied-effect count, official URI, retrieval date
- [ ] **Staleness disclosure** rendered on every page ("as at {date}; N amendments not yet applied", linking to the official page)
- [ ] **Repealed/prospective provisions retained and marked**
- [ ] **Cross-references** from `Citation`/`CitationSubRef` — internal link if the target is in the batch, external legislation.gov.uk link otherwise
- [ ] **Round-trip validators** — provision completeness, verbatim numbering, text conservation, citation resolution
- [ ] `laws/uk/` wired into the existing Docusaurus site; 🇬🇧 added to the country grid and navbar
- [ ] OGL v3 attribution

### Add after validation (v1.2)

- [ ] `Commentary` rendering, attached to its exact provision — *trigger:* Tier A ships and users ask "why does this say F1?"
- [ ] Tier B large Acts — *trigger:* a page-splitting strategy is decided
- [ ] Scheduled re-fetch → git amendment history — *trigger:* renderer output is confirmed byte-stable across two runs
- [ ] Defined-term index from `<Term>` — *trigger:* corpus large enough for a glossary to be useful
- [ ] Devolved legislation (`asp` first — English-only, no bilingual blocker) — *trigger:* jurisdiction taxonomy exists in the UI

### Future consideration (v2+)

- [ ] Welsh bilingual Senedd Acts — needs a second-language content model on top of Hebrew RTL
- [ ] Statutory Instruments — huge corpus, only meaningful relative to parent Acts
- [ ] Point-in-time browsing / as-enacted toggle — whole-product UI; git history covers most of the need first
- [ ] Explanatory Notes (`en.xsd`) — separate, non-authoritative document class
- [ ] Cross-jurisdiction concept linking (UK ↔ Israel by subject) — needs both corpora at volume

---

## Feature Prioritisation Matrix

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| CLML → Markdown renderer | HIGH | MEDIUM | **P1** |
| Hierarchy + verbatim numbering | HIGH | LOW | **P1** |
| `P1group/Title` as section heading | HIGH | LOW | **P1** |
| Schedules with enabling reference | HIGH | MEDIUM | **P1** |
| Frontmatter from `ukm:Metadata` | HIGH | LOW | **P1** |
| Staleness / unapplied-effects disclosure | HIGH | LOW | **P1** |
| Territorial extent display | MEDIUM | LOW | **P1** |
| Repealed/prospective marking | HIGH | LOW | **P1** |
| Round-trip validators | HIGH | MEDIUM | **P1** |
| Cross-reference linking | HIGH | MEDIUM | **P1** (external-link fallback carries it at this volume) |
| Deterministic byte-stable output | MEDIUM (invisible) | LOW *now*, HIGH later | **P1** — retrofitting invalidates git history |
| Commentary rendering | MEDIUM | MEDIUM | P2 |
| Git amendment history | HIGH | MEDIUM | P2 |
| Defined-term index | MEDIUM | LOW | P2 |
| Tier B large Acts | MEDIUM | HIGH (page splitting) | P2 |
| Devolved (`asp`, `nia`) | MEDIUM | MEDIUM | P3 |
| Welsh bilingual (`asc`, `anaw`) | MEDIUM | HIGH | P3 |
| Statutory Instruments | LOW | HIGH | P3 |
| Point-in-time browsing | LOW | HIGH | P3 |
| Explanatory Notes | LOW | MEDIUM | P3 |

---

## Competitor Feature Analysis

| Feature | legislation.gov.uk (official) | Westlaw / LexisNexis | **Codex Civica** |
|---|---|---|---|
| Access | Free, no login | Paywalled | Free, no login, no friction |
| Amendment history | Point-in-time date picker | Full annotated history | `git log` / diffs — reviewable, forkable, citable |
| Text format | HTML + XML + PDF | Proprietary HTML | Markdown in git — greppable, diffable, offline |
| Cross-links | Yes, within legislation.gov.uk | Yes, within their walled garden | Cross-jurisdiction (UK ↔ Israel), one convention |
| Staleness disclosure | Yes ("Changes to legislation" banner) | Editorially resolved | Yes — inherited from source, must not be dropped |
| Readability for non-lawyers | Institutional | Practitioner-only | Explicit design goal |
| Bulk reuse | OGL v3, API + bulk dataset | Prohibited | OGL v3 downstream, cloneable repo |

**Where Codex Civica genuinely wins:** git-native diffable law, cross-jurisdiction linking, and a zero-friction reading experience. **Where it must not pretend to compete:** editorial currency. legislation.gov.uk's own text lags Parliament; Codex Civica's will lag legislation.gov.uk by another increment. That gap must be stated on every page, not hidden.

---

## Open Questions for Roadmapping

1. **Page-splitting strategy** — undecided, and it gates Tier B. Tier A's largest (Interpretation Act 1978, 483 KB) is probably fine as one page; DPA 2018 (5.8 MB) certainly is not.
2. **Anchor scheme** — mirror legislation.gov.uk's `section-1-1-a` ids exactly (best for interoperability) or use Docusaurus-native slugs? Recommend mirroring.
3. **Directory layout** — Israel uses a flat `laws/israel/`. UK will eventually hold multiple legislatures and document classes. Recommend flat `laws/uk/` for v1.1 with `class`/`legislature` in frontmatter, matching the existing convention.
4. **Re-fetch cadence** — needed before git history has value. Weekly is likely ample given editorial lag.
5. **`/enacted` policy** — capture as-enacted where it exists (10 of 13 Tier A Acts) as a second file, or revised-only? Recommend revised-only for v1.1; the 404s on Magna Carta and Habeas Corpus 1679 make a mixed policy inconsistent.

---

## Sources

**Primary (HIGH confidence — live data fetched and parsed 2026-08-09):**
- CLML XML for: `ukpga/1998/42` (+ `/enacted`, `/2010-01-01`), `ukpga/2005/4`, `ukpga/1978/30`, `ukpga/1998/46`, `ukpga/1998/47`, `ukpga/2000/36`, `ukpga/2010/15`, `ukpga/2018/12`, `ukpga/2018/16`, `ukpga/2023/50`, `ukpga/2006/32`, `ukpga/2015/15`, `ukpga/1990/18`, `ukpga/1968/60`, `ukpga/2013/26`, `ukpga/2010/23`, `ukpga/2011/14`, `ukpga/Geo5/1-2/13`, `ukpga/Geo6/12-13-14/103`, `aep/Edw1cc1929/25/9`, `aep/WillandMarSess2/1/2`, `aep/Will3/12-13/2`, `aep/Cha2/31/2`, `aep/Ann/6/11`, `asp/2009/12`, `asp/2006/4`, `anaw/2015/2` (+ `/welsh`), `mwa/2011/2`, `nia/...`, `uksi/2011/1418`, `uksi/2019/419`, `uksi/1998/3132`
- CLML schema source — https://github.com/legislation/clml-schema (`schema/schemaLegislationNumberedSections.xsd`, `schemaModules/schemaMarginnote.xsd`, `schema/schemaLegislationSignature.xsd`, `schema/schemaLegislationCommonAttributes.xsd`, `schema/schemaLegislationAmendments.xsd`)

**Official documentation (HIGH confidence):**
- [CLML Reference Guide](https://legislation.github.io/clml-schema/)
- [legislation.gov.uk developer documentation](https://www.legislation.gov.uk/developer/contents) — formats, licensing (OGL v3)
- [legislation.gov.uk data reuse documentation](https://legislation.github.io/data-documentation/) — API overview, rate limit (3,000 requests / 5 min / IP), data completeness
- [Understanding legislation](https://www.legislation.gov.uk/understanding-legislation) — legislation types, enacted vs revised, 1 Feb 1991 base date
- [Legislation Data Access, Formats & Completeness (The National Archives)](https://cdn.nationalarchives.gov.uk/documents/cas-82049-legislation-date.pdf)
- [Legislation Text Bulk Dataset — Data Completeness](https://research.legislation.gov.uk/data-available)

**MEDIUM confidence:**
- Coverage floors (revised from 1991-02-01; enacted complete from 1988, Local Acts 1991, NI SRs 1996) — from National Archives documentation, corroborated by observed `/enacted` 404s, but not exhaustively tested across the corpus.

---
*Feature research for: UK legislation ingestion (Codex Civica v1.1)*
*Researched: 2026-08-09*
