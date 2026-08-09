# Architecture Research

**Domain:** Multi-jurisdiction legal-document pipeline + static site (adding UK/legislation.gov.uk to an existing Israel/Knesset system)
**Researched:** 2026-08-09
**Confidence:** HIGH for UK data source and CLML structure (verified against live API responses); HIGH for existing-codebase integration points (read directly from source); MEDIUM for the URL-rebase recommendation (judgement call, see Decision D-1)

---

## Executive Answer (the four questions, short form)

1. **Sibling package, thin shared core.** `pipeline/uk/` alongside the existing (Israel) modules, plus a new `pipeline/common/` holding exactly three things that are already literally duplicated or country-blind: frontmatter split/render, progress-file handling, deploy. Everything else in `pipeline/` is Hebrew/Knesset/OCR-specific and must **not** be reused.
2. **LAYER 1 becomes `CLML XML → typed IR → deterministic Markdown`.** There is **no LLM in the UK render path** — CLML is an authoritative single witness, not a noisy one, so reconciliation has nothing to reconcile. The one legitimate LLM use is *metadata-only* category classification (UK data has no subject taxonomy), written once into the manifest, never into the law body.
3. **Docusaurus multi-instance** (`@docusaurus/plugin-content-docs` with `id: 'uk'`). This forces a decision on the Israel route base (`/laws` → `/laws/israel`); recommend rebasing **now** plus `@docusaurus/plugin-client-redirects`, because the cost is near-zero today and grows monotonically.
4. **`data/raw/uk/` mirrors `data/raw/israel/` in shape but not in cost.** `manifest_uk.json` is built from per-year `data.csv` (1 HTTP request per type-year, ~41 rows/yr), raw CLML is cached under `data/raw/uk/xml/`, and `import_progress.json` keeps the identical `{done, failed, total_deployed, priority}` schema so `batch_import`'s proven loop shape carries over.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          ACQUISITION (per jurisdiction)                   │
├────────────────────────────────────┬─────────────────────────────────────┤
│  ISRAEL (existing)                 │  UK (new)                           │
│  fetch_laws.py                     │  pipeline/uk/fetch_uk.py            │
│  Knesset OData → manifest_laws     │  {type}/{year}/data.csv → manifest  │
│  + PDF download                    │  + {uri}/data.xml download          │
└────────────────┬───────────────────┴──────────────┬──────────────────────┘
                 │                                  │
┌────────────────▼───────────────────┐ ┌────────────▼──────────────────────┐
│  EXTRACT — noisy witnesses         │ │  PARSE — authoritative single src │
│  extract_native.py  (pdftotext)    │ │  pipeline/uk/clml.py              │
│  extract_ocr.py     (tesseract heb)│ │  lxml → LegalDoc IR (dataclasses) │
│  → native.txt + ocr.txt + layout   │ │  → in-memory tree, no LLM         │
└────────────────┬───────────────────┘ └────────────┬──────────────────────┘
                 │                                  │
┌────────────────▼───────────────────┐              │
│  RECONCILE — Gemini 2.5 Flash      │              │
│  reconcile.py + prompts/           │              │  (no equivalent —
│  two witnesses → one markdown body │              │   nothing to reconcile)
└────────────────┬───────────────────┘              │
                 │                                  │
┌────────────────▼──────────────────────────────────▼──────────────────────┐
│                     RENDER — deterministic Markdown                       │
│  IL: markdown emitted by the model, frontmatter by reconcile.py           │
│  UK: pipeline/uk/render.py — IR → Markdown, 100% deterministic            │
│  SHARED: pipeline/common/frontmatter.py  render_frontmatter(dict) -> str  │
└────────────────┬──────────────────────────────────┬──────────────────────┘
                 │                                  │
┌────────────────▼───────────────────┐ ┌────────────▼──────────────────────┐
│  VALIDATE + LINK (Israel)          │ │  VALIDATE + LINK (UK)             │
│  link_resolver.py passes 1–4       │ │  pipeline/uk/validate.py (on IR)  │
│  cross_linker.py (Gemini extract)  │ │  pipeline/uk/link_uk.py           │
│                                    │ │  Citation/@URI → local slug       │
└────────────────┬───────────────────┘ └────────────┬──────────────────────┘
                 │                                  │
┌────────────────▼──────────────────────────────────▼──────────────────────┐
│                    ORCHESTRATION (shared loop shape)                       │
│  pipeline/common/progress.py   load/save/get_next_batch/print_status      │
│  pipeline/common/deploy.py     npm run deploy, DEPLOY_EVERY threshold     │
│  batch_import.py (IL)   |   pipeline/uk/batch_import_uk.py (UK)           │
└────────────────┬──────────────────────────────────┬──────────────────────┘
                 │ writes .md                       │ writes .md
┌────────────────▼──────────────────────────────────▼──────────────────────┐
│  CONTENT STORE      laws/israel/*.md      laws/uk/*.md                    │
├──────────────────────────────────────────────────────────────────────────┤
│  SITE (single Docusaurus instance, two docs plugin instances)             │
│   preset docs  id=default  path=../laws/israel  routeBasePath=laws/israel │
│   plugin docs  id=uk       path=../laws/uk      routeBasePath=laws/uk     │
│   scripts/generate-law-meta.js  → src/generatedLawMeta.js (namespaced)    │
│   clientModules/lawSort.js      → country-aware grouping                  │
│   theme/DocItem/Content         → country-aware lang/dir/JSON-LD          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `pipeline/common/` | The only genuinely shared code. Frontmatter I/O, progress file, deploy. | 3 small modules, ~150 LOC total, extracted from existing duplication |
| `pipeline/uk/fetch_uk.py` | Enumerate legislation, build `manifest_uk.json`, cache CLML XML | `requests` + `csv` on `data.csv`; `data.xml` per item |
| `pipeline/uk/clml.py` | CLML → `LegalDoc` IR. Only module that knows the XML dialect. | `lxml.etree`, namespace-aware, dataclass tree |
| `pipeline/uk/render.py` | IR → Markdown per CLAUDE.md rules. Only module that knows Markdown. | Pure function `render(doc) -> str`; golden-file testable |
| `pipeline/uk/validate.py` | Numbering continuity, orphan subsections, malformed nesting, duplicate headings, unattached marginal notes | Runs on the **IR**, not on the rendered Markdown |
| `pipeline/uk/link_uk.py` | `Citation/@URI` → `./slug.md` upgrade; intra-doc section refs; priority queue emission | Deterministic; mirrors `link_resolver.py`'s *contract*, none of its regexes |
| `site/` docs instance `uk` | Renders `laws/uk/` at `/laws/uk/*` | `@docusaurus/plugin-content-docs`, `id: 'uk'` |

---

## Q1 — What is actually shared vs genuinely country-specific

I read every Python module in `pipeline/` and every custom file in `site/src`. Verdict:

### Genuinely shared (extract to `pipeline/common/`)

| Current location | Function | Why shared | Action |
|---|---|---|---|
| `pipeline/link_resolver.py:27` `split_frontmatter()` **and** `pipeline/cross_linker.py:202` `_split_frontmatter()` | Split `---\n…\n---` from body | **Byte-identical duplicate already in the repo.** Pure text, no language | → `pipeline/common/frontmatter.py: split_frontmatter()`; both callers import it |
| `pipeline/reconcile.py:120` `build_frontmatter()` — the YAML *serialisation* half (quoting, `~` for null, list rendering) | dict → YAML block | The **shape** of the frontmatter (`title`, `sidebar_label`, `description`, `hide_table_of_contents`, `generated_by`, `model`, `generated_at`) is the site's contract, not Israel's | → `pipeline/common/frontmatter.py: render_frontmatter(fields: dict) -> str`. Each country builds its own `fields` dict. **Do not** share `_strip_year()` (line 104) or `build_seo_description()` (line 109) — both are Hebrew-specific |
| `pipeline/batch_import.py:47–56` `load_progress` / `save_progress` | JSON `{done, failed, total_deployed, priority}` | Zero country content; only `PROGRESS_PATH` differs | → `pipeline/common/progress.py`, parameterised by data dir |
| `pipeline/batch_import.py:255` `get_next_batch()` | Priority-queue-first batch selection | The priority-queue-drain-then-manifest-order algorithm is the project's core scheduling idea and is fully generic once `pdf_path` is generalised to `source_path` | → `pipeline/common/progress.py: get_next_batch(manifest, progress, count, id_key, source_key)` |
| `pipeline/batch_import.py:296` `print_status()` | Progress summary | Generic | → `pipeline/common/progress.py` |
| `pipeline/batch_import.py:229` `deploy()` | `npm run deploy` with `USE_SSH=true GIT_USER=Yuvaldv` | Site-level, not country-level | → `pipeline/common/deploy.py` |

That is the **entire** shared surface. ~150 lines. Anything beyond this is premature abstraction (CLAUDE.md: *"Do not redesign architecture prematurely / Do not over-abstract"*).

### Genuinely Israel-specific — do NOT reuse

| File | Why it cannot be reused for UK |
|---|---|
| `pipeline/fetch_laws.py` | Knesset OData endpoints, `CLASSIFICATION_SLUGS` (line 38), `LAW_VALIDITY_VALID = 6079`, `BINDING_ORIGINAL = 6012`, ministry ID tables |
| `pipeline/extract_native.py`, `pipeline/extract_ocr.py` | PDF-only. UK primary path has no PDF. (`extract_ocr` hardcodes `-l heb` at `batch_import.py:133,137`) |
| `pipeline/reconcile.py` (except the frontmatter serialiser) | Gemini reconciliation of two noisy witnesses; `prompts/track2_gemini.md` is a Hebrew-legal prompt |
| `pipeline/cross_linker.py` | `_EXTRACT_PROMPT` (line 26) is a Hebrew prompt; `_STRIP_YEAR` (line 55) matches `תש…`; `_STRIP_KNESSET` matches `fs.knesset.gov.il` |
| `pipeline/link_resolver.py` passes 1–4 | `_SEC_HEADING` (line 42) `[א-ת]`; `_SEC_REF` (line 69) matches `סעיף/סעיפים`; `_KNESSET_PDF_LINK` (line 159); `_YEAR_SUFFIX` Hebrew |
| `pipeline/backfill_seo_meta.py`, `backfill_source_links.py`, `fix_2000595_tail.py` | One-off Israel content repairs |

### Concept-shared, implementation-specific

`link_resolver.py`'s four passes define a **contract** the UK linker should honour, but every implementation is replaced by data the CLML already carries:

| `link_resolver.py` pass | Israel implementation | UK equivalent | Cost |
|---|---|---|---|
| Pass 1 — section anchors | Regex over `# N.` headings, inject `<span id="section-N" />` | CLML gives `<P1 id="section-1">`, `<P2 id="section-1-1">`, `<P3 id="section-1-1-a">` **already** | Free — emit the source's own id |
| Pass 2 — intra-law refs | `_SEC_REF` Hebrew regex → `#section-N` | **Still needed.** Verified: HRA 1998 renders *"as to which see sections 14 and 15"* as plain `<Text>` with no markup. But it's an easy English regex (`section(s) N`, `subsection (N)`, `Schedule N`) against a **known-complete anchor set** | Low |
| Pass 3 — marginal-note index | Collect `>` blockquotes, associate with preceding anchor | CLML gives `<P1group><Title>The Convention Rights.</Title><P1 id="section-1">` — the association is **structural, not inferred**. Schema doc: *"Groups together provisions or paragraphs that have a common title"* | Free — and strictly more reliable than Israel's |
| Pass 4 — PDF→internal upgrade | Match `fs.knesset.gov.il` URL against manifest `pdf_url` | `<Citation URI="http://www.legislation.gov.uk/id/uksi/2001/3500" Year="2001" Number="3500">` and `<CitationSubRef URI=".../article/3" SectionRef="article-3">` — **exact machine-readable target URIs** | Free, and **replaces `cross_linker.py` entirely (no Gemini call, no name normalisation, no fuzzy matching)** |

**This is the single biggest architectural win of the UK milestone:** `cross_linker.py`'s Gemini-based reference extraction — the most expensive and least deterministic stage in the Israel pipeline — has a zero-cost, zero-error deterministic equivalent in UK data.

---

## Q2 — LAYER 1 for structured XML, and where (if anywhere) an LLM belongs

### Verified facts about the source (all checked against live responses, 2026-08-09)

| Fact | Evidence |
|---|---|
| Any content URI + `/data.xml` returns CLML | `GET /ukpga/1998/42/data.xml` → 200, 306 KB, root `<Legislation>` |
| Structure: `Body → Pblock(crossheading) → P1group → Title → P1[@id] → Pnumber → P1para → P2 → …` | Element census of HRA 1998: 57 `P1`, 146 `P2`, 155 `P3`, 29 `P1group`, 20 `Pblock`, 83 `Title` |
| `P1group/Title` **is** the marginal note / section heading | CLML schema `schemaLegislationNumberedSections.xsd`: *"Groups together provisions or paragraphs that have a common title"* |
| Every provision carries a stable `id` and `DocumentURI`/`IdURI` | `<P2 id="section-1-1" IdURI="…/id/ukpga/1998/42/section/1/1">` |
| Cross-references to other legislation are machine-resolvable | `<Citation URI="…/id/uksi/2001/3500" Class="UnitedKingdomStatutoryInstrument" Year="2001" Number="3500">` |
| Footnote/annotation equivalent exists | `<CommentaryRef Ref="c11199551"/>` → `<Commentaries><Commentary id="…" Type="E|M|F">` |
| Amendment markup is inline | `<Substitution ChangeId="d29p89" CommentaryRef="c18836901">`, `<Addition>`, `<Repeal>` |
| Defined terms are marked | `<Term id="term-the-convention-rights">` (57 in HRA) |
| Metadata: Dublin Core + `ukm:PrimaryMetadata` | `dc:title`, `dc:description` (= long title), `dc:date`, `dc:language`, `dc:modified`, `dct:valid`, `ukm:Year`, `ukm:Number`, `ukm:EnactmentDate`, `ukm:ISBN`, `DocumentMainType`, `DocumentStatus` |
| Rate limit | 3,000 req / 5 min / IP; 403 on exceed; **User-Agent required** by Fair Use Policy |
| Enumeration | `GET /{type}/{year}/data.csv?results-count=200` → one row per Act with title, summary, XML link, ISBN, dates. Default page size 20 — **must pass `results-count`** |
| Whole-corpus CSV does **not** work | `GET /ukpga/data.csv?results-count=1000` → **504 Gateway Time-out**. Per-year is the correct granularity |
| Pre-1963 Acts use regnal URIs | `/ukpga/1900/12/data.xml` → 301 → `/ukpga/Vict/63-64/12/…`; `ukm:AlternativeNumber Category="Regnal" Value="63_and_64_Vict"`, but `ukm:Year=1900`, `ukm:Number=63` |
| Some historic items are **PDF-only** | `/ukpga/Vict/63-64/63/data.xml` → 307 → `/enacted/data.xml`, 2.4 KB, **no `<Primary>`/`<Body>` element at all** — only `<ukm:Alternatives><ukm:Alternative … Print="true"/>` |
| Welsh bilingual exists | `/asc/2023/2/welsh/data.xml` → `<dc:language>cy` |

### LAYER 1 architecture: XML → IR → Markdown

```python
# pipeline/uk/ir.py — the intermediate representation
@dataclass
class Run:                      # inline content
    text: str
    kind: str                   # 'plain'|'term'|'citation'|'citation_subref'|'addition'|'substitution'|'repeal'|'emphasis'
    uri: str | None = None      # Citation/@URI, CitationSubRef/@URI
    section_ref: str | None = None
    commentary_refs: list[str] = field(default_factory=list)

@dataclass
class Provision:
    kind: str                   # 'part'|'chapter'|'crossheading'|'section'|'subsection'|'para'|'subpara'|'schedule'
    id: str | None              # CLML @id, e.g. 'section-1-1-a'  → the Markdown anchor
    number: str | None          # Pnumber text
    heading: str | None         # P1group/Title  → the MARGINAL NOTE
    runs: list[Run]
    children: list[Provision]
    extent: str | None          # RestrictExtent, e.g. 'E+W+S+N.I.'
    start_date: str | None      # RestrictStartDate

@dataclass
class LegalDoc:
    meta: DocMeta               # dc:* + ukm:* + point-in-time
    body: list[Provision]
    schedules: list[Provision]
    commentaries: dict[str, list[Run]]   # id → content
```

**Why an IR rather than a direct XSLT or streaming transform?**
- The validators, the linker and the renderer all need the *same* tree. Three independent XPath walks would drift.
- CLAUDE.md mandates golden-output comparison. The IR is the artifact you snapshot and diff; a change in the renderer that leaves the IR intact is provably text-only.
- XSLT is a legitimate alternative (legislation.gov.uk publishes its own stylesheets), but it puts the validation logic in a second language and makes the "compare outputs before updating pipeline logic" rule harder to honour.

**Markdown mapping (satisfies CLAUDE.md's format rules exactly):**

| IR | Markdown |
|---|---|
| `Provision(kind='crossheading')` | `## {heading}` (no anchor — Pblock is a grouping, not a provision) |
| `Provision(kind='section', number='1', heading='The Convention Rights.')` | `# 1. <span id="section-1" />` followed by `> [Marginal Note — Section 1]`<br>`> The Convention Rights.` |
| `Provision(kind='subsection', number='1')` | `## (1) <span id="section-1-1" />` |
| `Provision(kind='para', number='a')` | `### (a) <span id="section-1-1-a" />` |
| `Run(kind='citation', uri=…)` | `[S.I. 2001/3500](./uksi-2001-3500.md)` if converted, else `[S.I. 2001/3500](https://www.legislation.gov.uk/id/uksi/2001/3500)` |
| `commentaries` | `[^c11199551]: For the extent of this Act outside the U.K., see s. 22(6)(7)` |
| `Provision(kind='schedule')` | `# SCHEDULE 1 — The Articles <span id="schedule-1" />` |

Note the anchor style: use `<span id="…" />`, **not** `{#id}`. `link_resolver.py:50` documents the reason from hard experience — *"Uses HTML spans instead of `{#id}` to avoid MDX/acorn parse errors."* Inherit that decision, don't rediscover it.

`[UNCERTAIN TEXT]` markers: for UK, the only legitimate emitter is `pipeline/uk/clml.py` encountering an element it does not know how to render (`<Figure>`, `<Form>`, `<IncludedDocument>`, `<Tabular>` beyond simple tables). **Fail loudly rather than silently dropping**: unknown elements must either be rendered or recorded as a validation error — never skipped.

### Where does an LLM add value for UK content?

**Not in the conversion path. At all.** CLML is not a noisy witness — it is *the* published record, editorially maintained by The National Archives, with structure that is more explicit than anything Gemini could infer. Putting a model between CLML and Markdown would:
- violate CLAUDE.md's *"never invent text / never normalize legal wording"*,
- make output non-reproducible, destroying golden-file regression testing,
- add cost and latency to an operation that is a pure tree walk,
- and discard machine-readable structure (`@id`, `Citation/@URI`) in favour of re-inferring it.

There is exactly **one** place where an LLM genuinely earns its place, and it is metadata-only:

**UK has no subject taxonomy in the data.** I checked: the `ukpga` Atom feed declares an `xmlns:theme` namespace but emits **zero `theme:` elements**. `data.csv` has no category column. The Israel site's "Group by → Category" and "Ministry" dimensions have no UK source. Options:

| Option | Verdict |
|---|---|
| Drop category grouping for UK; group by Year / Type / Status only | Cheapest. Loses UI parity. Acceptable for the starter batch |
| Gemini classifies `dc:title` + `dc:description` into the existing 39-slug taxonomy in `generate-law-meta.js:13` | **Recommended once the corpus grows.** Metadata only, never touches the law body. Run once per law, persist `category` into `manifest_uk.json`, never re-derive at render time so output stays reproducible |
| Hand-maintain a mapping | Doesn't scale past a few dozen |

Two other LLM uses that Israel needs and **UK does not**:
- **SEO description:** `reconcile.py:109 build_seo_description()` templates a description because Knesset PDFs carry no abstract. UK's `dc:description` **is** the long title — a human-written, authoritative one-sentence summary. Verified present on every Act sampled. Use it verbatim; no generation of any kind.
- **Reference extraction:** replaced by `Citation/@URI` (see Q1 Pass 4).

**Fallback path for PDF-only historic Acts:** when `clml.py` finds no `<Primary>`/`<Secondary>` body element, the item is a scanned-PDF-only record. The correct handling is to route it to the **existing** Israel LAYER 1–3 pipeline with `-l eng` instead of `-l heb`. This is the one place the OCR/Gemini machinery has a UK role — and it should be **out of scope for the starter batch**, marked `status: "pdf_only"` in the manifest and skipped.

---

## Q3 — Docusaurus integration

### Decision D-1: route base paths (the one decision with a real cost)

Currently `site/docusaurus.config.ts:42–44` has the single preset docs instance at `path: '../laws/israel'`, `routeBasePath: 'laws'` → 111 live URLs at `/codex-civica/laws/<law_id>`.

| Option | Result | Cost |
|---|---|---|
| **A. Asymmetric** — Israel stays `laws`, UK gets `laws/uk` | `/laws/2000001` and `/laws/uk/ukpga-1998-42` | Zero URL breakage. But every downstream consumer needs a special case for "Israel has no country segment", and this asymmetry is permanent |
| **B. Symmetric (recommended)** — Israel → `laws/israel`, UK → `laws/uk`, add `@docusaurus/plugin-client-redirects` mapping `/laws/:id` → `/laws/israel/:id` | `/laws/israel/2000001`, `/laws/uk/ukpga-1998-42` | 111 URLs change. Mitigated by generated redirect pages. Every consumer (`lawSort.js`, `generate-law-meta.js`, `DocItem/Content`, homepage) gets one uniform rule |

**Recommend B, now.** Rationale: the SEO pass shipped 2026-08-09 (this week), the corpus is 111/718, there is no search feature yet, and inbound link equity is effectively nil. The cost of rebasing is monotonically increasing — it is cheaper today than it will ever be again. Flag it explicitly to the user as a deliberate one-time URL change; if they refuse, Option A works and the rest of this document is unchanged except that `lawSort.js`/`generate-law-meta.js` treat a missing country segment as `israel`.

### Config shape (verified against Docusaurus 3.10.1 docs)

Preset-classic's docs instance **is** the default instance (`id: 'default'`); additional instances go in `plugins[]`.

```ts
// site/docusaurus.config.ts
presets: [
  ['classic', {
    docs: {
      path: '../laws/israel',
      routeBasePath: 'laws/israel',      // ← changed from 'laws'
      sidebarPath: './sidebars.ts',
      showLastUpdateTime: false,
    },
    blog: false,
    theme: { customCss: './src/css/custom.css' },
  }],
],
plugins: [
  ['@docusaurus/plugin-content-docs', {
    id: 'uk',
    path: '../laws/uk',
    routeBasePath: 'laws/uk',
    sidebarPath: './sidebarsUk.ts',
    showLastUpdateTime: false,
  }],
  ['@docusaurus/plugin-client-redirects', {
    createRedirects(existingPath) {
      if (existingPath.startsWith('/laws/israel/')) {
        return [existingPath.replace('/laws/israel/', '/laws/')];
      }
      return undefined;
    },
  }],
],
```

`@docusaurus/plugin-client-redirects` must be installed at the matching version (`3.10.1`) — it is not in `site/package.json` today.

### Site files: exactly what changes and why

| File | Current Israel hardcoding (line refs) | Required change |
|---|---|---|
| `site/docusaurus.config.ts` | `docs.path: '../laws/israel'`, `routeBasePath: 'laws'` (42–44); navbar HTML flag `<a href="/codex-civica/laws" …>🇮🇱</a>` (66); navbar group-by `<select>` with hardcoded Year/Category/Ministry/Status options (72); footer copyright *"public legislation of the State of Israel"* (98) | Rebase docs; add `uk` plugin instance + redirects; replace single flag with two flag items (or a country dropdown); make the group-by select country-aware (see `lawSort.js` below); generalise footer copyright |
| `site/sidebars.ts` | `lawsSidebar` autogenerated from `.` — country-neutral | **No change.** Add new `site/sidebarsUk.ts` with the same `{type:'autogenerated', dirName:'.'}` shape |
| `site/src/pages/index.tsx` | Single hardcoded `<Link to="/laws">🇮🇱 Israel</Link>` (19–22) | Extract `const COUNTRIES = [{code:'israel', flag:'🇮🇱', name:'Israel', to:'/laws/israel'}, {code:'uk', flag:'🇬🇧', name:'United Kingdom', to:'/laws/uk'}]` and `.map()` over it. Optionally show law counts from `generatedLawMeta` |
| `site/scripts/generate-law-meta.js` | `LAWS_DIR = '../../laws/israel'` (9); `CATEGORY_EN`/`CATEGORY_HE` (13,37); `MINISTRY_EN`/`MINISTRY_HE` (61,79); `law_validity` Hebrew mapping (151–155); flat key `meta[String(lawId)]` (160) | Loop over `[{country:'israel', dir:…}, {country:'uk', dir:…}]`. **Namespace the keys**: `meta['israel:2000001']`, `meta['uk:ukpga-1998-42']` — required, since UK slugs and Israel numeric ids share one object. Emit a second export `GROUPINGS = {israel:['year','category','minister','status'], uk:['year','type','status']}` so the navbar select can adapt |
| `site/src/clientModules/lawSort.js` | `lawIdFromHref` regex `/\/laws\/(\d+)/` (24) — **numeric-only, silently drops UK docs from grouping**; `groupKey()` returns Hebrew fallbacks `'אחר'` (14–18); sort `localeCompare(a,b,'he')` (83); `_showGroupBy = pathname.includes('/laws')` (155,166) | Regex → `/\/laws\/(israel|uk)\/([^\/#?]+)/`, key = `` `${country}:${id}` ``; derive country from the path once per route and use it to pick label language, sort locale (`'he'` vs `'en'`), and which `<option>`s to show |
| `site/src/theme/DocItem/Content/index.jsx` | **`<html lang="he" dir="rtl" />` applied to every doc page** (32); `og:locale he_IL` (33); `legislationJurisdiction: {name:'Israel'}` (25); `inLanguage:'he'` (27); `law_validity === 'תקף'` (26); `LawMetaBubbles` reads `categoryLabelHe`/`ministerHe`/`statusHe` and defaults `statusHe = 'תקף'` (52) | **Highest-priority fix.** Without it, every UK page ships as `lang="he" dir="rtl"` with Israeli JSON-LD. Add `site/src/lib/jurisdiction.ts` → `jurisdictionFromPermalink(permalink)`; prefer a `jurisdiction:` frontmatter field when present, fall back to the path. Drive `lang`/`dir`/`og:locale`/`legislationJurisdiction`/`inLanguage` and the meta bubbles from it |
| `site/src/css/custom.css` | `.markdown { direction: rtl; text-align: right; }` (~line 60) plus further `.markdown h*` rules I did not read past line 80 | Scope every RTL rule to `html[dir='rtl'] .markdown { … }`. **Audit the whole file** — I only reviewed the first 80 lines; assume more RTL assumptions below |
| `site/package.json` | `prebuild`/`predeploy` already run `generate-law-meta.js` — country-neutral | Add `@docusaurus/plugin-client-redirects@3.10.1` dependency. No script changes |
| `site/static/img/` | `flag-il.svg` exists | Add `flag-gb.svg` if the navbar moves from emoji to SVG |

**Avoiding a frontmatter backfill:** deriving jurisdiction from `metadata.permalink` means the 111 existing Israel files need **no** migration. Write `jurisdiction: uk` into new UK frontmatter anyway (cheap, explicit, future-proof) and have the helper prefer frontmatter when present. This removes the only hard ordering dependency between the site work and a content-rewrite pass.

---

## Q4 — `data/raw/uk/` layout and manifests

`.gitignore` already excludes `data/raw/` and `*.pdf`, so everything below is free to cache aggressively.

```
data/raw/uk/
├── manifest_uk.json          # canonical item list + metadata + local paths
├── import_progress.json      # {done, failed, total_deployed, priority}  ← same schema as Israel
├── listings/                 # raw per-year CSV, cached so manifest rebuild needs no network
│   ├── ukpga-2024.csv
│   └── ukpga-1998.csv
└── xml/                      # cached CLML, keyed by local slug
    ├── ukpga-1998-42.xml
    └── ukpga-2010-15.xml
```

**Slug scheme:** `{type}-{ukm:Year}-{ukm:Number}` → `ukpga-1998-42.md`. Derived from metadata, **not** from the URI path, so pre-1963 regnal URIs (`/ukpga/Vict/63-64/63`) still produce a clean `ukpga-1900-63`. The manifest stores both the canonical `uri` (for fetching, and for `Citation/@URI` matching) and the `slug` (for the filename and the Docusaurus doc id).

**`manifest_uk.json` entry** (parallel to `manifest_laws.json`, same `status`/local-path idiom):

```json
{
  "slug": "ukpga-1998-42",
  "uri": "http://www.legislation.gov.uk/id/ukpga/1998/42",
  "content_uri": "https://www.legislation.gov.uk/ukpga/1998/42",
  "type": "ukpga",
  "main_type": "UnitedKingdomPublicGeneralAct",
  "doc_status": "revised",
  "year": 1998,
  "number": 42,
  "title": "Human Rights Act 1998",
  "long_title": "An Act to give further effect to rights and freedoms guaranteed under the European Convention on Human Rights; …",
  "enactment_date": "1998-11-09",
  "valid_date": "2026-04-06",
  "modified_date": "2026-04-09",
  "isbn": "0105442984",
  "extent": "E+W+S+N.I.",
  "xml_url": "https://www.legislation.gov.uk/ukpga/1998/42/data.xml",
  "xml_path": "/mnt/c/Dev/codex-civica/data/raw/uk/xml/ukpga-1998-42.xml",
  "has_body": true,
  "pdf_only_url": null,
  "category": null,
  "status": "pending"
}
```

**Key differences from the Israel data flow, and what they buy:**

| | Israel | UK |
|---|---|---|
| Enumeration | OData paginated, several lookup tables joined (`fetch_laws.py` fetches 4 full tables) | 1 CSV request per `(type, year)` — `?results-count=200` returns all 41 Acts of 2010 in one call. Whole-type CSV **504s**, so per-year is mandatory |
| Acquisition | PDF download (Knesset WAF blocks WSL2 for some paths) | Plain HTTPS GET, no WAF, but **User-Agent is mandatory** and 3,000 req / 5 min / IP applies. A starter batch of 10–20 is far inside the limit; a full-corpus crawl needs throttling |
| Re-render cost | Requires a fresh Gemini call (non-deterministic, costs money) | **Free and byte-identical** — re-parse the cached XML. This makes golden-file regression tests (CLAUDE.md's *"Keep fixtures and golden outputs / Compare outputs before updating pipeline logic"*) actually practical for the first time in this project |
| Priority queue | Fed by Gemini-extracted refs that failed manifest lookup | Fed by `Citation/@URI` values not yet in `laws/uk/` — exact, no fuzzy matching, no false positives |
| Freshness | Static once published | **`data.xml` returns the latest revised text and changes over time.** `dct:valid` + `dc:modified` must go into frontmatter or the repo silently mixes vintages |

**Bulk download:** none usable. There is no public whole-corpus XML dump; the per-year CSV + per-item `data.xml` approach is the supported path. (`research.legislation.gov.uk`'s "Legislation Text Bulk Dataset" exists but the data-availability page returned **401 Unauthorized** — treat as gated / unavailable. LOW confidence on what it contains.)

---

## New vs Modified vs Shared — complete file list

### New — pipeline

| Path | Purpose |
|---|---|
| `pipeline/common/__init__.py` | — |
| `pipeline/common/frontmatter.py` | `split_frontmatter()`, `render_frontmatter(dict) -> str` |
| `pipeline/common/progress.py` | `load_progress`, `save_progress`, `get_next_batch`, `print_status` |
| `pipeline/common/deploy.py` | `deploy()` |
| `pipeline/uk/__init__.py` | — |
| `pipeline/uk/fetch_uk.py` | per-year `data.csv` → `manifest_uk.json`; download + cache `data.xml` |
| `pipeline/uk/ir.py` | `Run`, `Provision`, `LegalDoc`, `DocMeta` dataclasses |
| `pipeline/uk/clml.py` | CLML → IR (the only namespace-aware module) |
| `pipeline/uk/render.py` | IR → Markdown body + frontmatter dict |
| `pipeline/uk/validate.py` | IR validators: numbering continuity, orphans, malformed nesting, duplicate headings, unattached marginal notes, unknown-element coverage |
| `pipeline/uk/link_uk.py` | `Citation/@URI` → `./slug.md`; intra-doc section refs; priority-queue emission |
| `pipeline/uk/batch_import_uk.py` | Orchestrator: fetch → parse → validate → render → link → deploy-every-N |
| `pipeline/uk/fixtures/` | Golden inputs + expected Markdown (start with 3: short Act, Act with Schedules, Act with heavy amendment markup) |
| `pipeline/UK_PIPELINE.md` | Doc, mirroring the existing `pipeline/PIPELINE.md` |

### New — site

| Path | Purpose |
|---|---|
| `site/sidebarsUk.ts` | Autogenerated sidebar for the `uk` docs instance |
| `site/src/lib/jurisdiction.ts` | `jurisdictionFromPermalink()`, `JURISDICTIONS` config (flag, name, lang, dir, locale, groupings) |
| `site/static/img/flag-gb.svg` | Optional, if navbar moves off emoji |

### Modified

| Path | Nature of change |
|---|---|
| `site/docusaurus.config.ts` | routeBasePath rebase; `uk` docs plugin; client-redirects; navbar flags; footer copyright |
| `site/package.json` | `+ @docusaurus/plugin-client-redirects@3.10.1` |
| `site/src/pages/index.tsx` | Country grid from a config array |
| `site/scripts/generate-law-meta.js` | Two source dirs; namespaced keys; per-country label maps; export groupings |
| `site/src/clientModules/lawSort.js` | Country-aware id parsing, labels, sort locale, visible group-by options |
| `site/src/theme/DocItem/Content/index.jsx` | Country-aware `lang`/`dir`/`og:locale`/JSON-LD/meta bubbles |
| `site/src/css/custom.css` | Scope all RTL rules under `html[dir='rtl']` |
| `pipeline/link_resolver.py` | Import `split_frontmatter` from `common` (delete local copy) |
| `pipeline/cross_linker.py` | Import `split_frontmatter` from `common` (delete `_split_frontmatter`) |
| `pipeline/reconcile.py` | `build_frontmatter()` delegates YAML serialisation to `common.frontmatter.render_frontmatter` |
| `pipeline/batch_import.py` | Import progress/deploy helpers from `common` |
| `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md` | **Both are stale** (dated 2026-05-08, still claim `pipeline/` has no `.py` files and Docusaurus has template defaults). Refresh as part of this milestone |

### Unchanged

`site/sidebars.ts`, `.github/workflows/deploy.yml`, `.gitignore` (`data/raw/` already covers `data/raw/uk/`), all `laws/israel/*.md` content, `pipeline/extract_*.py`, `pipeline/prompts/`.

---

## Recommended Build Order

Dependencies are real here: the site cannot be wired until the UK frontmatter *schema* is fixed, and the linker cannot emit correct relative paths until the route bases are settled.

**Phase 1 — Shared-core extraction (pipeline only, zero behaviour change)**
1. Create `pipeline/common/{frontmatter,progress,deploy}.py`
2. Repoint `link_resolver.py`, `cross_linker.py`, `reconcile.py`, `batch_import.py`
3. **Proof of no regression:** run `python pipeline/link_resolver.py --all` and `git diff --stat laws/israel/` → must be empty
*Gate: empty diff. Independent of everything else; safe to do first.*

**Phase 2 — UK acquisition**
1. `pipeline/uk/fetch_uk.py` — per-year CSV → `manifest_uk.json`, XML cache, `has_body` / `pdf_only_url` detection, User-Agent + throttling
2. Seed the starter-batch list (see below)
*Gate: `manifest_uk.json` populated, N XML files cached, PDF-only items correctly flagged `has_body: false`.*

**Phase 3 — CLML → Markdown (the core of the milestone)**
1. `ir.py` + `clml.py` — parse to IR; unknown elements raise, never silently drop
2. `render.py` — IR → Markdown + frontmatter dict. **Freeze the frontmatter field list here** — Phase 5 depends on it
3. `validate.py` — IR validators
4. `fixtures/` — golden outputs for 3 representative Acts
*Gate: 3 goldens byte-stable across two runs; validators clean or explicitly-accepted failures.*

**Phase 4 — Site: route rebase + redirects (Israel only, no UK content yet)**
1. `routeBasePath: 'laws'` → `'laws/israel'`; install and configure `plugin-client-redirects`
2. Update `lawSort.js` id regex and `generate-law-meta.js` key namespacing for the new path (Israel-only at this point — one country, new shape)
3. Build + serve; verify `/laws/2000001` redirects and grouping still works
*Gate: existing site fully functional at new URLs; old URLs redirect. **Do this before any UK docs land** so exactly one variable changes.*

**Phase 5 — Site: second country**
1. `uk` docs plugin instance + `sidebarsUk.ts` (needs ≥1 real `.md` from Phase 3)
2. `site/src/lib/jurisdiction.ts`; rewire `DocItem/Content/index.jsx` (lang/dir/JSON-LD — **the correctness-critical one**)
3. Scope RTL CSS under `html[dir='rtl']`; audit the rest of `custom.css`
4. `index.tsx` country grid; navbar flags; country-aware group-by options
*Gate: a UK page serves `lang="en" dir="ltr"` with UK JSON-LD; an Israel page is unchanged from Phase 4.*

**Phase 6 — Linking**
1. `link_uk.py` — `Citation/@URI` → `./slug.md` for converted targets, `legislation.gov.uk` URL otherwise; intra-doc section refs; priority-queue emission
2. Re-run across the batch (idempotent, like `link_resolver`)
*Gate: internal links resolve with `onBrokenLinks: 'warn'` producing no new warnings.*

**Phase 7 — Starter batch + deploy**
1. `batch_import_uk.py` over the starter list
2. Deploy via `USE_SSH=true GIT_USER=Yuvaldv npm run deploy`

**Why this order:** Phase 4 before Phase 5 isolates the riskiest site change (URL rebase, 111 live pages) from the additive change (second country). Phase 3 before Phase 5 because `generate-law-meta.js` must know the real UK frontmatter fields. Phase 6 after Phase 4 because relative-link correctness depends on the final route base. Phase 1 is fully independent and can be parallelised or skipped if the roadmapper prefers to defer the refactor — but deferring it means `batch_import_uk.py` will copy-paste `batch_import.py`, and the two will drift (see Anti-Pattern 2).

**Starter batch candidates** — all verified 2026-08-09 as `DocumentStatus="revised"` with a full `<Body>`:

| URI | Title | XML size | Note |
|---|---|---|---|
| `aep/WillandMarSess2/1/2` | Bill of Rights [1688] | 37 KB | Smallest; constitutional-tier — the UK analogue of Israel's Basic Laws |
| `ukpga/1990/18` | Computer Misuse Act 1990 | 269 KB | Small, well-known |
| `ukpga/1998/42` | Human Rights Act 1998 | 306 KB | Schedules, heavy `Substitution` markup, `UnappliedEffects` |
| `ukpga/1998/29` | Data Protection Act 1998 | 274 KB | Repealed-in-part → tests status rendering |
| `ukpga/2000/36` | Freedom of Information Act 2000 | 2.1 MB | Mid-size stress test |
| `ukpga/2005/4` | Constitutional Reform Act 2005 | 3.1 MB | Parts + Chapters + Schedules |
| `ukpga/2010/15` | Equality Act 2010 | 3.6 MB | Large, heavily cross-referenced |
| `ukpga/2018/16` | European Union (Withdrawal) Act 2018 | 1.8 MB | Dense citation graph |

Exclude `ukpga/2006/46` (Companies Act 2006, **15 MB** XML) from the starter batch — see Scaling.

---

## Scaling Considerations

Reframed from "users" to corpus size, which is the actual constraint for a static site.

| Corpus | Adjustments |
|---|---|
| 10–50 UK laws (starter batch) | Nothing. Full re-parse of every cached XML on each run takes seconds |
| 50–500 | Add per-item incremental skip keyed on `dc:modified`. `generate-law-meta.js` still fine (it is a linear frontmatter scan) |
| 500–5,000 | Docusaurus build time and memory become the bottleneck well before the pipeline does. Consider `docusaurus build --locale` splitting or the `@docusaurus/faster` Rust bundler (already a dependency). `lawSort.js` builds its group map in the browser on every route change — at ~2k sidebar entries that becomes visible; move grouping into build-time sidebar generation |
| Full UK corpus (17,560 `ukpga` alone, plus SIs) | Out of scope. Would require sharding the site or moving off flat-file-per-law |

**Scaling priorities — what breaks first:**
1. **Single-document size, not document count.** Companies Act 2006 is 15 MB of XML → on the order of 5–8 MB of Markdown in one MDX file. Docusaurus/MDX will be slow or fail. Israel already hit the analogue (law 2000595, 546 sections). Mitigation: set a size threshold in `render.py`; above it either split by Part into `<slug>-part-N.md` with an index page, or exclude from the batch and record the reason in the manifest. **Decide this before the starter batch, not after.**
2. **Docusaurus build memory** at a few thousand docs.
3. **API rate limit** only if a full-corpus crawl is attempted (3,000 / 5 min ≈ 10 req/s sustained — comfortable, but needs an explicit throttle rather than relying on luck).

---

## Anti-Patterns

### AP-1: Sending CLML through Gemini "for consistency with the Israel pipeline"
**What people do:** Reuse `reconcile.py`'s shape by feeding CLML-derived text to a model to "clean it up".
**Why it's wrong:** Directly violates CLAUDE.md (*never invent text, never normalize legal wording*). Destroys reproducibility, which is the single largest advantage UK data has. Discards `@id` and `Citation/@URI` in order to re-infer them worse. Costs money for a tree walk.
**Do this instead:** Deterministic parse. Confine any LLM to manifest metadata (category classification), computed once and persisted.

### AP-2: Copy-pasting `batch_import.py` into `pipeline/uk/`
**What people do:** Duplicate the 440-line orchestrator because "the stages are different anyway".
**Why it's wrong:** Two implementations of progress tracking, priority queueing and deploy thresholds will diverge on the first bug fix. The stages differ; the *loop* does not.
**Do this instead:** Extract `common/progress.py` + `common/deploy.py` first (Phase 1). `batch_import_uk.py` should be ~100 lines of stage wiring.

### AP-3: Building a "jurisdiction plugin framework" before country #2 works
**What people do:** Abstract `LawSource`/`Extractor`/`Renderer` base classes covering hypothetical Jordan and beyond.
**Why it's wrong:** CLAUDE.md: *"Do not redesign architecture prematurely. Do not over-abstract. Do not refactor without evidence."* Two countries is not enough evidence for an interface — and the two are maximally different (noisy PDF vs authoritative XML), so any shared interface would be an empty abstraction.
**Do this instead:** Extract only the three things that are *already literally duplicated*. Revisit after country #3.

### AP-4: Leaving `.markdown { direction: rtl }` global
**What people do:** Add UK content and only notice the RTL bleed at review time.
**Why it's wrong:** `site/src/css/custom.css` applies RTL to `.markdown` unconditionally, and `DocItem/Content/index.jsx:32` sets `<html lang="he" dir="rtl">` on **every** doc page. Every UK Act would render right-aligned with Hebrew locale metadata and Israeli JSON-LD.
**Do this instead:** Scope under `html[dir='rtl']` and derive `lang`/`dir` from jurisdiction. Treat this as a correctness bug, not styling polish.

### AP-5: Assuming numeric law IDs
**What people do:** Reuse `lawSort.js:24`'s `/\/laws\/(\d+)/`.
**Why it's wrong:** UK ids are slugs (`ukpga-1998-42`). The regex returns `null`, the item is skipped by `if (!id) continue;`, and UK laws silently vanish from sidebar grouping with no error.
**Do this instead:** `/\/laws\/(israel|uk)\/([^\/#?]+)/`, and namespace the meta keys as `country:id`.

### AP-6: Flattening `P1group/Title` into a plain heading
**What people do:** Emit `## The Convention Rights.` and move on.
**Why it's wrong:** Loses the marginal-note-to-provision relationship that CLAUDE.md explicitly requires be preserved (*"Margin notes are metadata attached to legal hierarchy nodes… Do NOT float margin notes globally without structural attachment"*). Ironically the UK source states this relationship explicitly where Israel's must be inferred — throwing it away is a pure regression.
**Do this instead:** `> [Marginal Note — Section 1]` attached to the `section-1` anchor, matching the Israel convention, plus the `## Sidenotes` index if parity is wanted.

### AP-7: Ignoring point-in-time drift
**What people do:** Fetch `/data.xml`, convert, commit, never revisit.
**Why it's wrong:** `/data.xml` serves the *latest revised* text. HRA 1998 currently reports `dct:valid 2026-04-06`, `dc:modified 2026-04-09`. Re-running the pipeline months later silently produces different text for the same law, and the repo ends up a mix of vintages with no record of which is which.
**Do this instead:** Write `valid_date` and `modified_date` into frontmatter and the manifest. Detect drift by comparing manifest `modified_date` against a fresh `resources/data.xml` HEAD before deciding to re-convert. Optionally pin to a dated URI (`/ukpga/1998/42/2026-04-06/data.xml`) for reproducibility.

### AP-8: Treating a 200 response as "we have the text"
**What people do:** Check the HTTP status and assume a body.
**Why it's wrong:** PDF-only historic items return **200** with a well-formed `<Legislation>` that contains only `<ukm:Metadata>` — no `<Primary>`, no `<Body>`. Verified on `/ukpga/Vict/63-64/63` (Local Government (Ireland) Act 1900): 2,388 bytes, `DocumentStatus="final"`, `<ukm:Alternative … Print="true"/>`. A naive renderer would emit an empty law page.
**Do this instead:** Assert `<Body>` (or `<ScheduleBody>`) exists. Absent → `has_body: false`, `status: "pdf_only"`, skip and record the PDF URL for the future OCR fallback path.

---

## Integration Points

### External Services

| Service | Integration Pattern | Gotchas |
|---|---|---|
| legislation.gov.uk `data.csv` | `GET /{type}/{year}/data.csv?results-count=200` | **Default page size is 20** — omitting `results-count` silently truncates. Whole-type CSV **504s** |
| legislation.gov.uk `data.xml` | `GET {content_uri}/data.xml`, follow redirects | 301 for calendar→regnal URIs; 307 for revised→`/enacted` on unrevised items; 200-with-no-body for PDF-only |
| Fair Use Policy | Set a descriptive `User-Agent` on every request | Required by policy; 3,000 req / 5 min / IP → 403 |
| Gemini (`GEMINI_API_KEY` in `pipeline/.env`) | **Only** for optional category classification | Must never touch the law body. Cache results in the manifest |
| GitHub Pages | Unchanged — `.github/workflows/deploy.yml` + `npm run deploy` | Deploy still needs `USE_SSH=true GIT_USER=Yuvaldv` in WSL2 |

### Internal Boundaries

| Boundary | Communication | Notes |
|---|---|---|
| `pipeline/uk/` ↔ `pipeline/common/` | Direct import | One-way only. `common` must never import from `uk/` or from Israel modules |
| `pipeline/uk/` ↔ Israel modules | **None**, except the future PDF-only OCR fallback | Enforce by review; a UK module importing `reconcile` is a smell |
| `clml.py` ↔ `render.py` | The IR dataclasses | The IR is the contract. `render.py` must never see `lxml` elements; `clml.py` must never emit Markdown |
| `pipeline/*` ↔ `site/*` | Filesystem only — `laws/{country}/*.md` frontmatter | The frontmatter field list is the API. Changing it requires a matching `generate-law-meta.js` change |
| `generate-law-meta.js` → `lawSort.js` / `DocItem/Content` | `site/src/generatedLawMeta.js` (build artifact) | Namespaced keys `country:id` are the contract |
| `link_uk.py` → `import_progress.json` | `priority` array | Same convention as `cross_linker.py` → `batch_import.py` — reuse the semantics exactly |

---

## Confidence and Gaps

| Claim | Confidence | Basis |
|---|---|---|
| CLML structure, element semantics, ids, citations, marginal notes | **HIGH** | Live API responses parsed directly + official XSD documentation strings |
| Rate limits, User-Agent requirement, `data.csv` pagination, 504 on whole-type | **HIGH** | Official docs + reproduced against the live service |
| PDF-only detection rule (no `<Body>` element) | **HIGH** | Verified on a real 1900 Act |
| Existing-codebase integration points (file/line refs) | **HIGH** | Read from source this session |
| Docusaurus multi-instance config | **HIGH** | Context7 / official Docusaurus 3.x docs |
| `@docusaurus/plugin-client-redirects` at 3.10.1 | **MEDIUM** | First-party plugin, versioned in lockstep; not verified installed |
| URL-rebase recommendation (D-1) | **MEDIUM** | Judgement call weighing near-zero current traffic against permanent asymmetry. Needs user sign-off |
| "No subject taxonomy in UK data" | **MEDIUM** | `theme:` namespace declared but zero elements in the `ukpga` feed; `data.csv` has no category column. Did not exhaustively check every endpoint |
| `research.legislation.gov.uk` bulk dataset | **LOW** | Data-availability page returned 401. Unknown contents/licence. Treat as unavailable |

**Open questions for phase-level research:**
- Exact rendering rules for `<Tabular>`, `<Figure>`, `<Form>`, `<BlockAmendment>` in Markdown — not encountered in the sampled Acts' hot path, but Equality Act 2010 and Companies Act 2006 will contain them.
- Whether Welsh-language versions (`/welsh/data.xml`, `dc:language=cy`) are in scope — the site's i18n config has `locales: ['en']` only.
- Large-document splitting threshold and strategy (see Scaling priority 1) — needs a measurement pass on Equality Act 2010 before the starter batch is finalised.

---

## Sources

- [Legislation API overview — legislation.gov.uk data reuse documentation](https://legislation.github.io/data-documentation/api/overview.html) — endpoints, `/data.xml`, rate limit 3,000/5min, User-Agent requirement (HIGH)
- [Atom feeds — legislation.gov.uk data reuse documentation](https://legislation.github.io/data-documentation/formats/atom.html) — feed types, pagination, `leg:page`/`leg:morePages` (HIGH)
- [CLML schema repository](https://github.com/legislation/clml-schema) — `schemaLegislationNumberedSections.xsd` (`P1group` = "Groups together provisions or paragraphs that have a common title"), `schemaLegislationStructure.xsd` (HIGH)
- [Crown Legislation Markup Language Reference Guide](https://legislation.github.io/clml-schema/) (HIGH)
- [legislation.gov.uk XML formats](https://legislation.gov.uk/developer/formats/xml) (HIGH)
- Live API responses fetched 2026-08-09: `ukpga/1998/42`, `ukpga/2010/15`, `ukpga/2018/16`, `ukpga/1998/29`, `ukpga/2000/36`, `ukpga/2018/12`, `ukpga/2005/4`, `ukpga/1990/18`, `ukpga/2006/46`, `aep/WillandMarSess2/1/2`, `asc/2023/2` (+ `/welsh`), `uksi/2020/350`, `ukpga/Vict/63-64/63`, `ukpga/{1900,1960,1988,2010,2024}/data.csv`, `ukpga/2024/data.feed` (HIGH — primary evidence)
- [Legislation Text Bulk Dataset — Data Completeness](https://research.legislation.gov.uk/data-available) — returned 401, contents unverified (LOW)
- [Docusaurus — Docs multi-instance](https://docusaurus.io/docs/docs-multi-instance) via Context7 `/websites/docusaurus_io` (HIGH)
- Codex Civica source read this session: `pipeline/{batch_import,reconcile,link_resolver,cross_linker,fetch_laws}.py`, `site/{docusaurus.config.ts,sidebars.ts,package.json}`, `site/src/{pages/index.tsx,clientModules/lawSort.js,theme/DocItem/Content/index.jsx,css/custom.css}`, `site/scripts/generate-law-meta.js`, `data/raw/israel/{manifest_laws,import_progress}.json`, `CLAUDE.md`, `.planning/PROJECT.md` (HIGH)

---
*Architecture research for: UK legislation pipeline integration into Codex Civica (milestone v1.1)*
*Researched: 2026-08-09*
