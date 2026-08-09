# Stack Research — UK Legislation Pipeline (v1.1)

**Domain:** Structured legal-XML ingestion → deterministic Markdown (UK / legislation.gov.uk)
**Researched:** 2026-08-09
**Confidence:** HIGH (all findings verified against official docs *and* live API calls against legislation.gov.uk)

---

## TL;DR — The Headline Answer

**legislation.gov.uk is a clean, authenticated-free, structured-XML API. The Israel LAYER1/LAYER2/LAYER3 architecture (native extract → OCR → Gemini reconciliation) is NOT needed for the UK pipeline and must NOT be ported.**

The Knesset architecture exists because the source is a *scanned image PDF* — a noisy witness requiring probabilistic reconstruction. The UK source is **CLML** (Crown Legislation Markup Language), an XSD-validated XML dialect maintained by The National Archives that already encodes section/subsection/paragraph hierarchy, numbering, citations, amendment commentary, and in-force dates as machine-readable structure. Converting it is a **deterministic tree walk**, not a reconstruction problem.

Net new hard dependencies: **zero.** Everything required (`requests`, `lxml`, `python-frontmatter`, `PyYAML`, `tqdm`, `tenacity`) is already installed in `~/.venv-codex`.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **legislation.gov.uk API** | no versioning; live | Sole data source for UK legislation | Official National Archives service. No auth, no API key, no registration. Serves the *authoritative* CLML XML — TNA states CLML "is the most accurate data held on legislation.gov.uk". Verified live: `GET /ukpga/1998/42/data.xml` → `200`, 306 KB, 557 `<Text>` nodes. |
| **CLML** (Crown Legislation Markup Language) | SchemaVersion `1.0`; XSD at `https://www.legislation.gov.uk/schema/legislation.xsd` | The XML dialect to parse | Native format of the corpus, not a lossy derivative. Schema is open-source at [`legislation/clml-schema`](https://github.com/legislation/clml-schema). Embeds Dublin Core metadata, XHTML tables, MathML. Hierarchy is explicit (`P1group`/`P1`/`P2`/`P3`/`P4`), so **no hierarchy inference is needed** — the single hardest problem in the Israel pipeline is simply absent here. |
| **Python** | 3.12.3 (existing `~/.venv-codex`) | Pipeline runtime | Matches existing `pipeline/`. All recommended libs support 3.12. |
| **lxml** | `6.1.0` installed / `6.1.1` current | XML parse + XPath tree walking | Already a project dependency (used by the Israel pipeline). C-backed libxml2: full XPath 1.0, namespace handling, `iterparse` for the 3.5 MB Equality Act 2010 case, and XSD validation via `etree.XMLSchema` against the published `legislation.xsd`. Bump to 6.1.1 is optional — no relevant changes. |
| **requests** | `2.33.1` installed / `2.34.2` current | HTTP fetch | Already a project dependency. Sync + simple is correct here: the fair-use crawl-delay of 5s dominates, so async buys nothing. Needs a `Session` with a custom `User-Agent` (mandatory — see Fair Use below). |
| **python-frontmatter** | `1.1.0` installed / `1.3.0` current | YAML frontmatter emit | Already used by the Israel pipeline for `laws/israel/*.md`. Reuse verbatim so `laws/uk/*.md` shares one frontmatter contract and one validator. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **tenacity** | `9.1.4` (already installed) | Retry with exponential backoff | **Required.** The API returns `403 Forbidden` on rate-limit breach and `202 Accepted` while a representation is being generated. Retry on `403`/`429`/`503`/`5xx` with jitter; treat `202` as "poll again". |
| **PyYAML** | `6.0.3` (already installed) | Frontmatter serialisation | Transitively used by `python-frontmatter`; pin explicitly since frontmatter field ordering matters for clean git diffs. |
| **tqdm** | `4.67.3` (already installed) | Batch progress | Match existing `batch_import.py` UX. |
| **requests-cache** | `1.3.3` | Transparent on-disk HTTP cache | **Recommended, optional.** Makes re-runs of `convert.py` free and keeps you far under fair-use limits during development iteration. Drop-in: `CachedSession(expire_after=...)`. The only genuinely *new* package worth adding. |
| **xmlschema** | `4.3.2` | Pure-Python XSD validation | **Not needed** — `lxml.etree.XMLSchema` already validates against `legislation.xsd`. Listed only so it's explicitly rejected. |
| **saxonche** | `13.0.0` | XSLT 3.0 processor | **Only if** you choose an XSLT-based conversion strategy (not recommended — see below). `lxml` is XSLT 1.0 only. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `curl` | Manual endpoint probing | Always pass `-A "CodexCivica (https://github.com/Yuvaldv/codex-civica)"`. Anonymous UAs violate the fair-use policy. |
| `legislation.xsd` (cached locally) | Schema validation in `validate.py` | Fetch once into `pipeline_uk/schema/`; validate parsed trees offline. Prevents silent breakage if TNA ships a schema change. |
| CLML schema docs | Element reference | https://legislation.github.io/clml-schema/ — generated reference for every CLML element. Primary reference when writing the tree walker. |
| Golden fixtures | Regression safety | Per project `CLAUDE.md` ("Keep fixtures and golden outputs"): commit 3–5 raw CLML files + expected Markdown under `pipeline_uk/fixtures/`. Suggested spread: `ukpga/1998/42` (modern, commentary-heavy), `aep/1297/9` (Magna Carta — rekeyed medieval), `uksi/2020/1500` (secondary, `article` divisions), `ukpga/2010/15` (3.5 MB stress case), `ukla/1988/1` (metadata-only — must be *rejected* by the pipeline). |

---

## Installation

```bash
# Activate existing venv — do NOT create a new one
source ~/.venv-codex/bin/activate

# Everything below is ALREADY INSTALLED. Verified 2026-08-09:
#   lxml 6.1.0, requests 2.33.1, python-frontmatter 1.1.0,
#   PyYAML 6.0.3, tqdm 4.67.3, tenacity 9.1.4
# No action required for the core stack.

# The single recommended NEW dependency (optional but high value):
pip install "requests-cache==1.3.3"

# Cache the schema locally for offline validation:
mkdir -p pipeline_uk/schema
curl -A "CodexCivica (https://github.com/Yuvaldv/codex-civica)" \
  -o pipeline_uk/schema/legislation.xsd \
  https://www.legislation.gov.uk/schema/legislation.xsd
```

Then append to `pipeline/requirements.txt`:

```
requests-cache==1.3.3
```

---

## The Data Access Surface (verified)

### Endpoints

| Endpoint | Returns | Verified |
|----------|---------|----------|
| `/{type}/{year}/{number}/data.xml` | Latest in-force version as CLML | ✅ `200` |
| `/{type}/{year}/{number}/enacted/data.xml` | As-enacted text | ✅ (rarely available pre-1988) |
| `/{type}/{year}/{number}/{YYYY-MM-DD}/data.xml` | Point-in-time version | Documented; base date 1991-02-01 |
| `/{type}/{year}/{number}/notes/data.xml` | Explanatory Notes (root `<EN>`, schema `en.xsd`) | ✅ `200`, 1.1 MB for Equality Act 2010. **`404` for HRA 1998** — ENs only exist for Acts from ~1999 |
| `/{type}/{year}/{number}/resources/data.xml` | Metadata + list of alternative representations (incl. print PDFs) | ✅ `200` |
| `/{type}/{year}/data.feed` | Atom listing, 20/page, `leg:page` + `leg:morePages` + `openSearch:*` pagination, faceted by year/type | ✅ `200` |
| `/{type}/{year}/data.csv` | Same listing as CSV (`rel="alternate"` in the feed) | ✅ advertised |
| `/update/data.feed`, `/update/{date}/data.feed` | Publication log — new/withdrawn items, for incremental sync | Documented |
| `/search?title=…&type=…&start-year=…&end-year=…` | Search; `301` on single match, `300` on ambiguity | ✅ `300` observed on `aep/1688/2` |
| `/{...}/data.akn` | **Akoma Ntoso 3.0** (OASIS LegalDocML) | ✅ `200`, 244 KB, valid `<akomaNtoso>` with FRBR metadata |
| `/{...}/data.rdf` | RDF/XML (FRBR, Metalex, Dublin Core, FOAF) | Documented |
| `/sparql` | SPARQL endpoint (GET + POST) | Documented |
| `/{...}/data.pdf` | Dynamically generated PDF | ⚠️ **`Disallow: */data.pdf` in robots.txt** |
| `/{...}/data.json` | — | ✅ `404` — **there is no JSON API** |

Base URL `https://www.legislation.gov.uk/`. **No authentication, no API key, no registration.** GET only (except SPARQL). CORS enabled on `/data.{ext}`.

### Legislation type codes

`ukpga` (Public General Acts) · `ukla` (Local) · `ukppa` (Private/Personal) · `asp` (Scotland) · `asc`/`anaw` (Wales) · `nia` (NI) · `ukcm` (Church Measures) · `uksi`/`ssi`/`wsi`/`nisr` (Statutory Instruments/Rules) · `ukdsi` (drafts) · historical: `aep`, `aosp`, `apgb`, `aip`, `apni`, `gbla`, `gbppa` · EU-derived: `eur`, `eudn`, `eudr`, `eut`.

Division names vary by instrument type: Acts use `section`, Orders use `article`, Regulations use `regulation`, Rules use `rule`. Schedules: `/schedule/{n}/paragraph/{n}`. **The converter must switch division vocabulary on `ukm:DocumentMainType` — hardcoding "section" will mislabel every SI.**

Pre-1963 items use **regnal years** (`aep/Edw7/7/...`); calendar-year URIs `301` to the regnal form. Follow redirects (`-L` / `allow_redirects=True`).

### Rate limits & fair use (HARD CONSTRAINT)

| Rule | Value | Source |
|------|-------|--------|
| Rate limit | **3,000 requests / 5 minutes**, tracked *per user* not per IP | Fair Use Policy |
| Breach response | `403 Forbidden`, escalating to temporary/permanent block | Fair Use Policy |
| `robots.txt` `Crawl-delay` | **5 seconds** | ✅ fetched live |
| Recommended conservative rate | 10 requests per 5–10 seconds | Fair Use Policy |
| User-Agent | **Mandatory**, non-anonymous, with contact URL or email. e.g. `CodexCivica (https://github.com/Yuvaldv/codex-civica)` | Fair Use Policy |
| Disallowed paths | `*/data.pdf`, `*/data.docx`, `/defralex` | ✅ robots.txt |
| Large crawls | Contact TNA beforehand | Fair Use Policy |

**Implication for `fetch.py`:** honour the 5s crawl-delay, not the 3,000/5min ceiling. A starter batch of ~15 Acts ≈ 75 seconds. Enough headroom that no concurrency is warranted.

**There is no bulk corpus download.** No tarball, no data dump. TNA directs high-volume users to the Atom feeds and publication log instead of full-site crawling. Plan for incremental feed-driven fetching, not a bulk import.

---

## The OCR / LLM Question — Answered with Evidence

**Verdict: the UK pipeline needs neither Tesseract nor Gemini/Claude reconciliation. Do not add them.**

### Evidence that text is fully present in XML

Live `data.xml` fetches, counting `<Text>` elements:

| Document | Era / type | Result |
|---|---|---|
| `aep/1297/9` (Magna Carta 1297) | Medieval, rekeyed | `200`, **55** `<Text>` |
| `ukpga/1911/13` (Parliament Act 1911) | Pre-1988, revised | `200`, **24** `<Text>` |
| `ukpga/1972/68` (European Communities Act) | Pre-1988, repealed | `200`, **43** `<Text>` |
| `ukpga/1998/42` (Human Rights Act) | Modern | `200`, **557** `<Text>` |
| `ukpga/2010/15` (Equality Act) | Modern, large | `200`, **6,360** `<Text>` |
| `uksi/2020/1500` | Secondary | `200`, **201** `<Text>` |

Hierarchy arrives pre-resolved. Actual CLML for HRA 1998 s.3:

```xml
<P1group RestrictStartDate="2024-04-25">
  <Title> Interpretation of legislation.</Title>
  <P1 id="section-3" IdURI=".../id/ukpga/1998/42/section/3">
    <Pnumber><CommentaryRef Ref="key-e4c8df32…"/>3</Pnumber>
    <P1para>
      <P2 id="section-3-1"><Pnumber>1</Pnumber><P2para>
        <Text>So far as it is possible to do so, primary legislation…</Text>
      </P2para></P2>
      <P2 id="section-3-2"><Pnumber>2</Pnumber><P2para>
        <Text>This section—</Text>
        <P3 id="section-3-2-a"><Pnumber>a</Pnumber><P3para>
          <Text>applies to primary legislation and subordinate legislation whenever enacted;</Text>
```

Every requirement that motivated the Israel LLM layer is satisfied structurally:

| Israel problem (needs Gemini) | UK equivalent (free in CLML) |
|---|---|
| Infer hierarchy from indentation | `P1group` → `P1` → `P2` → `P3` → `P4` nesting is explicit |
| Recover numbering from OCR | `<Pnumber>` is a discrete element |
| Correct OCR character errors | No OCR — text is digital |
| Isolate footnotes | `<Commentary Type="E">` blocks + inline `<CommentaryRef Ref="…">` → maps 1:1 to Markdown `[^ref]` |
| Attach margin notes to nodes | Not applicable — UK marginal notes are already promoted to `<Title>` inside `<P1group>` |
| Mark uncertain regions | Not applicable — no uncertainty. Amendment provenance is explicit via `<Addition>` / `<Substitution>` / `<Repeal>` and `ukm:UnappliedEffects` |
| Cross-reference resolution | `<Citation>` / `<CitationSubRef>` carry resolved `URI` attributes — **better than the Israel `link_resolver.py` 4-pass heuristic** |

Reconstruction is deterministic. Introducing an LLM here would *violate* the project's own `CLAUDE.md` rules ("Never hallucinate text", "Never paraphrase legal language", "deterministic markdown rendering") by injecting nondeterminism into a channel that has none.

### The one genuine PDF-only sub-case — and why it's out of scope

Some material has **metadata-only XML with no text**. Verified live on `ukla/1988/1` (Greater Manchester (Light Rapid Transit System) Act 1988):

```
NumberOfProvisions="0"        ← zero provisions
<Text> element count: 0       ← no text at all
<atom:link rel="alternate" href=".../pdfs/ukla_19880001_en.pdf" type="application/pdf" title="Original PDF"/>
```

Per TNA's "What We Have", the PDF-only classes are:

- UK Public General Acts **pre-1988 not in force at 1991-02-01** — "mostly only available as King's Printer PDF"
- **UK Local Acts pre-1991** and **Private/Personal Acts 1801–1987** — PDF only, unrevised
- **Local / unprinted Statutory Instruments** before 1987 (UK), 2007–2011 (Wales/Scotland), 2011 (NI)
- **UK Ministerial Directions / Orders** — King's Printer PDFs only
- Letters Patent, Royal Charters, Royal Instructions, Royal Proclamations — **metadata only, no text held at all**
- Pre-2004 EU-origin instruments — original PDF

**Recommendation: do not build for this case in v1.1.** Three reasons:
1. `robots.txt` explicitly `Disallow: */data.pdf` — automated PDF harvesting is against site policy.
2. The starter batch is Public General Acts, which are 100% XML-covered from 1988 and largely covered before that.
3. If OCR is ever wanted for Local/Private Acts, the Israel LAYER1–3 code in `pipeline/` (`extract_native.py`, `extract_ocr.py`, `reconcile.py`) already exists and can be pointed at a downloaded PDF — nothing needs to be built now.

**Instead, `fetch.py` must detect and skip these.** Guard: `NumberOfProvisions="0"` on the root `<Legislation>` element, or zero `<Text>` descendants → record as `skipped: pdf_only` with the PDF URL in a manifest, never emit a stub Markdown file. This is a *validator* requirement, not an OCR requirement.

### Known data-quality caveats (feed into `validate.py`)

- `<ukm:UnappliedEffects>` lists amendments **not yet applied** to the text. HRA 1998 carries 5. The Markdown must surface these or it silently misrepresents current law.
- TNA: "over 95% of all primary legislation on the website is up to date" — so ~5% is not.
- No version history before **1991-02-01** (UK) / **2006-01-01** (NI).
- Pre-basedate documents "may have been rekeyed or OCRed" by TNA — accuracy not guaranteed. Relevant to `aep/1297/9`-class material.
- Effects data can lag up to six weeks for large documents.

---

## Integration Points with the Existing Repo

| Existing asset | UK treatment |
|---|---|
| `pipeline/` (Israel: `fetch.py`, `extract_native.py`, `extract_ocr.py`, `reconcile.py`, `link_resolver.py`, `batch_import.py`) | **Leave untouched.** Create a sibling `pipeline_uk/` per PROJECT.md. Zero shared execution path — the source models have nothing in common. |
| `pipeline/requirements.txt` | Append `requests-cache==1.3.3` only. Israel's `pymupdf`, `knesset-data`, `python-hebrew-numbers`, `anthropic`, `pyslet` are all irrelevant to UK and must not be extended. |
| `~/.venv-codex` | Shared. Python 3.12.3, all core deps present. |
| `laws/israel/*.md` (flat, `2000001.md`) | Mirror the flat-directory pattern in `laws/uk/`, but use human-readable slugs: `ukpga-1998-42.md`, `uksi-2020-1500.md`. UK has no numeric law-ID analogue to Knesset's; the type/year/number triple *is* the identifier and round-trips to the source URI. |
| Frontmatter schema (`title`, `title_he`, `law_id`, `category`, `enacted`, `status`) | Reuse the shape; substitute UK-native fields. Direct CLML sources: `dc:title` → `title`; `ukm:Year` + `ukm:Number` + `ukm:DocumentMainType` → `law_id`/`type`; `dc:date` → `enacted`; `dct:valid` → `version_date`; `dc:modified` → `updated`; `RestrictExtent` (e.g. `E+W+S+N.I.`) → `extent`; `dc:description` (long title) → `description` (feeds the existing SEO meta work). `title_he` is Israel-only — omit, don't blank. |
| `pipeline/backfill_seo_meta.py` | UK gets `description` for free from `<dc:description>` (the Act's long title) — no backfill pass needed. |
| `pipeline/link_resolver.py` (4-pass heuristic) | **Do not reuse.** CLML `<Citation URI="…">` gives resolved targets directly. A UK cross-linker is a one-pass attribute read, not a heuristic cascade. |
| `site/` Docusaurus | Add `laws/uk/` as a second docs plugin instance. UK is LTR English — no RTL/i18n work, unlike Hebrew. Per memory note: use **frontmatter** (`hide_table_of_contents`, `sidebar_label`), not CSS. |
| Deploy | Unchanged: `USE_SSH=true GIT_USER=Yuvaldv npm run deploy`. |

### Suggested `pipeline_uk/` shape

```
pipeline_uk/
  fetch.py       # Atom feed discovery → data.xml download → data/raw/uk/*.xml
                 #   UA header, 5s crawl-delay, tenacity retry, requests-cache
                 #   skip + log NumberOfProvisions="0"
  convert.py     # lxml tree walk CLML → Markdown + frontmatter (python-frontmatter)
  validate.py    # XSD validate vs cached legislation.xsd
                 #   + numbering continuity / orphan subsection checks (per CLAUDE.md)
                 #   + UnappliedEffects surfacing
  schema/legislation.xsd
  fixtures/      # golden CLML in + Markdown out
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **CLML** (`/data.xml`) | **Akoma Ntoso** (`/data.akn`) — verified live, valid OASIS LegalDocML 3.0 with FRBR metadata | If you later need interoperability with other national legal corpora (many EU/African/LatAm jurisdictions publish AKN). But CLML is the *native* format and AKN is a downstream transform — pick CLML for fidelity now. Worth revisiting if Codex Civica adds a third jurisdiction that publishes AKN. |
| **CLML** | `/data.htm` HTML → `markdownify` 1.2.3 / `html-to-markdown` 3.10.6 | Never for production. HTML is presentation-transformed and loses `Pnumber`/`Commentary`/`Citation` semantics. Tempting shortcut, structurally lossy. |
| **lxml tree walk in Python** | **XSLT 3.0 via `saxonche` 13.0.0** | If the CLML→Markdown mapping grows past ~600 lines of Python, or if you want to reuse TNA's own XSLT from [`legislation/website-frontend`](https://github.com/legislation/website-frontend). Costs a heavyweight Java-backed dependency and moves logic out of Python. Not worth it for a starter batch. |
| **requests** | **httpx 0.28.1** (async) | Only if a future milestone ingests the full ~500k-item corpus. Pointless at v1.1 scope: the 5s crawl-delay makes concurrency illegal, not just useless. |
| **Atom feed discovery** | **SPARQL endpoint** (`/sparql`) | For complex metadata queries — "all Acts amended by SI X", "all in-force Acts on topic Y". Genuinely powerful for a future cross-reference graph feature. Overkill for fetching a curated starter batch. |
| **Atom feed** | `data.csv` listings | Quick manual batch-list building by hand. Fewer fields than the feed. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Tesseract / `pytesseract`** | Source is digital XML. Zero scanned input in the starter-batch scope. Adds a system-level binary dependency for no gain. | `lxml` parse of `data.xml` |
| **`pymupdf` / `pdfplumber` / `pdftotext`** | Same. Also, `robots.txt` `Disallow: */data.pdf` makes the PDF path policy-non-compliant. | `data.xml` |
| **Gemini Flash / `anthropic` reconciliation layer** | There is nothing to reconcile — one authoritative witness, not multiple noisy ones. Injects nondeterminism and hallucination risk into a deterministic channel, violating project `CLAUDE.md`. | Deterministic tree walk |
| **`beautifulsoup4` for the XML** | `bs4`'s namespace handling is weak and its XPath support absent. CLML is namespace-heavy (`legislation`, `ukm`, `dc`, `dct`, `atom`, `xhtml`, `mathml`). | `lxml.etree` with an explicit nsmap |
| **`xml.etree.ElementTree` (stdlib)** | No XSD validation, limited XPath, no `iterparse` performance for the 3.5 MB Equality Act. | `lxml` |
| **`/data.json`** | Does not exist — verified `404`. | `data.xml` |
| **Anonymous / default `python-requests/2.x` User-Agent** | Explicit fair-use violation; risks a permanent block on the project's IP. | `CodexCivica (https://github.com/Yuvaldv/codex-civica)` |
| **Concurrent/parallel fetching** | Breaches the 5s `Crawl-delay`. Also risks `403` and blocking. | Sequential + `time.sleep(5)` + `tenacity` |
| **Full-site crawling / sitemap harvesting** | TNA explicitly asks re-users to prefer feeds. No bulk download exists by design. | `/update/data.feed` + type/year Atom feeds |
| **Hardcoding "section" as the division name** | SIs use `article`/`regulation`/`rule`. Would mislabel every piece of secondary legislation. | Branch on `ukm:DocumentMainType` |
| **`knesset-data`, `python-hebrew-numbers`, `pyslet`, `python-docx`** | Israel-specific. | n/a |
| **A separate venv or a new Docusaurus site** | PROJECT.md locks one site with a country grid; venv is shared. | `~/.venv-codex`, `laws/uk/` in the same `site/` |

---

## Stack Patterns by Variant

**If the starter batch = UK Public General Acts (recommended — the natural analogue to Israel's 14 Basic Laws):**
- Candidates: Magna Carta 1297 (`aep/1297/9`), Bill of Rights 1689, Parliament Acts 1911/1949, European Communities Act 1972, Human Rights Act 1998, Scotland Act 1998, Government of Wales Act 1998/2006, Northern Ireland Act 1998, Equality Act 2010, Constitutional Reform Act 2005, Freedom of Information Act 2000
- 100% XML coverage — verified for the 1297/1911/1972/1998/2010 samples above
- No OCR, no LLM, no PDF handling
- `fetch.py` + `convert.py` + `validate.py` only

**If the batch extends to Statutory Instruments (`uksi`):**
- Still pure XML for printed SIs from 1987
- Add division-name mapping (`article` / `regulation` / `rule`)
- Note: **secondary legislation is generally NOT revised** — the text is as-made, with amendments listed only in `<ukm:UnappliedEffects>`. `validate.py` must emit a prominent "as made, not consolidated" warning in frontmatter or the site will misinform readers.

**If the batch ever extends to Local / Private / pre-1988 unrevised Acts:**
- Expect metadata-only XML (`NumberOfProvisions="0"`)
- *Then and only then* consider the PDF path — and first check TNA's policy on `data.pdf`, plus prefer the static `…/pdfs/{type}_{year}{number}_en.pdf` URL exposed via `<ukm:Alternative Print="true">` in `/resources/data.xml`
- Reuse `pipeline/extract_native.py` + `extract_ocr.py` + `reconcile.py` as-is; build nothing new
- **Out of scope for v1.1**

**If Explanatory Notes are wanted:**
- Separate fetch: `/notes/data.xml`, root `<EN>`, schema `en.xsd` (not `legislation.xsd`) — needs its own walker
- Coverage gap: ENs exist only for Acts from ~1999. Verified `404` on HRA 1998; `200` (1.1 MB) on Equality Act 2010
- Recommend deferring past the starter batch

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Python 3.12.3 | all recommended libs | `requests` 2.34.x requires ≥3.10; `python-frontmatter` 1.3.0 requires ≥3.10; `tenacity` 9.1.4 requires ≥3.10 — all satisfied |
| `lxml` 6.1.0 (installed) | `legislation.xsd` SchemaVersion 1.0 | Full XSD 1.0 support via `etree.XMLSchema`. 6.1.1 available; no relevant delta — upgrade is optional |
| `requests` 2.33.1 (installed) | `requests-cache` 1.3.3 | `requests-cache` supports `requests` ≥2.22. No conflict |
| `python-frontmatter` 1.1.0 (installed) | `PyYAML` 6.0.3 | Already the Israel-pipeline pairing; keep both pipelines on one version to guarantee identical frontmatter serialisation across `laws/israel/` and `laws/uk/` |
| `requests-cache` 1.3.3 | Python ≥3.8 | Pulls `attrs`, `cattrs`, `url-normalize`, `platformdirs`. All pure-Python, no conflicts with the existing tree |
| CLML `SchemaVersion="1.0"` | stable | Same value on 1297, 1911, 1972, 1998, 2010, 2020 documents — one walker handles all eras |

---

## Licensing & Attribution (REQUIRED)

**Licence: [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).** Permits copying, publishing, distributing, adapting, and both commercial and non-commercial exploitation. Derivative works and redistribution are **explicitly allowed** — Markdown conversion and republication via Docusaurus is squarely within the licence.

**Required attribution (exact wording from TNA):**

> © Crown and database right. Derived from content available under the Open Government Licence v3.0 from legislation.gov.uk

**Two exceptions requiring different attribution:**

1. **EU-derived content** (`eur`, `eudn`, `eudr`, `eut`, and retained EU law) — dual-licensed under OGLv3.0 *and* Commission Decision 2011/833/EU:
   > Crown © and database right material re-used under the Open Government Licence. Material derived from the European Institutions © European Union, 1998-2020 and re-used under the terms of the Commission Decision 2011/833/EU.

2. **Westlaw-contributed content** — pre-1987 Statutory Instruments. Detect via `<dc:publisher>Westlaw</dc:publisher>` in the CLML metadata:
   > Westlaw UK derived from Crown Copyright material and contributed to legislation.gov.uk

**Implementation requirements for the roadmap:**
- `convert.py` must read `<dc:publisher>` and select the correct attribution string — this is a **conditional**, not a constant. (Observed values so far: `Statute Law Database`, `King's Printer of Acts of Parliament`.)
- Emit attribution into each `laws/uk/*.md` (frontmatter field + a rendered footer), **and** a site-wide notice.
- Add `LICENSE-UK-CONTENT.md` or a `laws/uk/README.md` carrying the OGL statement.
- Note asymmetry: Israeli law text is Knesset-sourced with different terms; do not apply one blanket site-wide licence statement across both countries.
- Record the source URI (`dc:identifier`) per law — good practice and consistent with the existing `backfill_source_links.py` pattern.

---

## Sources

| Source | Confidence | What it established |
|---|---|---|
| Live API calls to `www.legislation.gov.uk` (2026-08-09) — 15+ `curl`/`lxml` probes across `aep/1297/9`, `ukpga/1911/13`, `ukpga/1972/68`, `ukpga/1998/42`, `ukpga/2010/15`, `uksi/2020/1500`, `ukla/1988/1` | **HIGH** | XML availability, `<Text>` counts, CLML element structure, metadata-only stub detection, AKN availability, `data.json` 404, Atom pagination |
| https://www.legislation.gov.uk/robots.txt (fetched live) | **HIGH** | `Crawl-delay: 5`; `Disallow: */data.pdf`, `*/data.docx`, `/defralex`; full sitemap list |
| https://legislation.github.io/data-documentation/api/overview.html | **HIGH** | Endpoints, no-auth, mandatory UA, 3,000/5min, HTTP codes, CORS |
| https://legislation.github.io/data-documentation/fair-use.html | **HIGH** | Rate limit semantics (per-user), UA format, crawl guidance, enforcement |
| https://legislation.github.io/data-documentation/what-we-have.html | **HIGH** | Per-type coverage matrix, XML-vs-PDF-only classes, revised/unrevised status, base dates, "95% up to date" |
| https://legislation.github.io/data-documentation/reuse-licence.html | **HIGH** | OGL v3.0, exact attribution strings, EU + Westlaw exceptions |
| https://legislation.github.io/data-documentation/formats/pdf.html | **HIGH** | Dynamic vs static PDFs; no OCR statement |
| https://legislation.github.io/data-documentation/api/publication-log.html | **HIGH** | `/update/data.feed`, date filters, 20/page pagination |
| https://www.legislation.gov.uk/developer/uris | **HIGH** | Full URI scheme, type codes, regnal years, extents, versions, division names |
| https://www.legislation.gov.uk/developer/limitations | **HIGH** | Base dates, unapplied effects, unrevised secondary legislation |
| https://github.com/legislation/clml-schema + https://legislation.github.io/clml-schema/ | **HIGH** | CLML is the authoritative format; `legislation.xsd`, `en.xsd`, `impactAssessment.xsd`, `publicationLog.xsd` |
| https://github.com/legislation (org listing via `gh api`) | **HIGH** | 9 repos; XSLT/TypeScript only — **no Python library published by TNA** |
| PyPI JSON API (direct queries, 2026-08-09) | **HIGH** | All version numbers; confirmed `uk-legislation`, `legislation`, `clml`, `ukleg`, `legislation-uk` all return 404 — **no third-party Python library exists** |
| `~/.venv-codex` `pip list` | **HIGH** | Installed versions; Python 3.12.3 |

**Gaps / open questions for the roadmapper:**
- Exact starter-batch list is a product decision, not a research one. Suggested 10–15 constitutionally-significant Public General Acts (list under "Stack Patterns" above).
- How `<ukm:UnappliedEffects>` should render in Markdown (frontmatter warning flag vs. an inline admonition block) — a design call for the convert phase.
- Whether `<Commentary>` amendment annotations belong in the body as footnotes or in a collapsible section — affects readability for the non-lawyer audience that PROJECT.md targets.
- Point-in-time versioning (multiple dated snapshots per Act) is available but almost certainly out of scope for v1.1; worth an explicit "current in-force only" decision.

---
*Stack research for: UK legislation ingestion (legislation.gov.uk / CLML)*
*Researched: 2026-08-09*
