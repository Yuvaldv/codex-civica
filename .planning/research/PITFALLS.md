# Pitfalls Research

**Domain:** UK legislation ingestion (legislation.gov.uk CLML/XML) + adding a second country to a single-country legal corpus site
**Researched:** 2026-08-09
**Confidence:** HIGH for legislation.gov.uk behaviour (verified by live API probes against the real service on 2026-08-09 plus official TNA documentation); HIGH for Codex Civica integration pitfalls (verified by reading the actual source files); MEDIUM for LLM-reconciliation advice (reasoning from the existing `pipeline/reconcile.py` design + CLAUDE.md rules, not from external post-mortems).

**Phase labels used below:** `UK-Scope` (architecture decisions before code), `UK-Fetch`, `UK-Convert`, `UK-Validate`, `UK-Site`. These map to the milestone's stated fetch → convert → validate → site-integration structure, with `UK-Scope` added because several pitfalls must be decided *before* the fetcher is written.

---

## Critical Pitfalls

### Pitfall 1: The 200-OK Empty Law (PDF-only items return a valid but bodyless XML stub)

**What goes wrong:**
You request `/data.xml` for an Act, get **HTTP 200**, valid CLML, a correct `<dc:title>`, correct dates — and **no legislative text at all**. You emit a Markdown file with perfect frontmatter and an empty body. Nothing errors.

Verified live (2026-08-09):

| URI | HTTP | Size | Body |
|-----|------|------|------|
| `ukpga/1998/42/data.xml` (Human Rights Act) | 200 | 306 KB | `NumberOfProvisions="57"` |
| `ukla/1990/1/data.xml` (St. George's Hill Estate Act) | 200 | **2.1 KB** | `NumberOfProvisions="0"`, no `<Body>` |
| `ukpga/1957/20/data.xml` (House of Commons Disqualification Act) | 200 (after 301) | **2.4 KB** | `NumberOfProvisions="0"`, no `<Body>` |

The stub's only content payload is `<ukm:Alternatives><ukm:Alternative ... URI=".../pdfs/ukla_19900001_en.pdf" Print="true"/></ukm:Alternatives>` — the real law exists only as a scanned King's Printer PDF.

**Why it happens:**
Developers treat HTTP 200 + well-formed XML as success. TNA's coverage is genuinely incomplete for: all Local and Private/Personal Acts; most primary legislation not at least partially in force on 1 Feb 1991; pre-1987 local SIs; and pre-2012 unprinted instruments. For these, the API still serves a metadata record.

**How to avoid:**
Make the fetcher fail loudly on bodyless documents. Concrete gate, applied before anything is written to `laws/uk/`:
- Reject if `/Legislation/@NumberOfProvisions` is `0` or absent.
- Reject if there is no `<Body>` element and no `<Schedules>` element.
- Reject if `<ukm:Alternatives>` is the only substantive child (i.e. PDF-only item).
Record rejects in a `data/raw/uk/skipped.json` with reason `pdf-only`, and exclude them from the starter batch rather than silently emitting a shell file. Do **not** be tempted to route PDF-only UK Acts into the Israel OCR pipeline for this milestone — that reintroduces the entire noisy-witness problem the UK source was chosen to avoid.

**Warning signs:**
A `laws/uk/*.md` file under ~1 KB. A Markdown file whose only heading is the Act title. `NumberOfProvisions="0"` anywhere in the fetch log.

**Phase to address:** `UK-Fetch` (hard gate), re-checked in `UK-Validate`.

---

### Pitfall 2: Silently getting the wrong version — bare `/data.xml` is not always "current law"

**What goes wrong:**
The URI scheme's default is documented as "the version currently in force." In practice, for items with no revised version the site **301-redirects to `/enacted`** and you receive the *original 1957 text* believing you have current law. Verified: `GET /ukpga/1957/20/data.xml` → `301` → `/ukpga/Eliz2/5-6/20/data.xml` → `200` at `/ukpga/Eliz2/5-6/20/enacted/data.xml`. The response body does not shout "this is the enacted version" — you must read `DocumentURI` / `<dc:identifier>` and notice the `/enacted` suffix.

The inverse error is equally bad: fetching `/enacted` because it "looks canonical" or because it's smaller/simpler. Human Rights Act enacted = 189 KB, revised = 306 KB. The enacted version of the HRA is materially different law from the revised version, and enacted versions carry **no I-note commencement information at all**.

Compounding this, **secondary legislation is not revised** on legislation.gov.uk at all (except NI Orders in Council). A UK Statutory Instrument's "current" text on the site is its as-made text with all subsequent amendments *not* incorporated. If your starter batch mixes `ukpga` and `uksi`, half your corpus silently means something different from the other half.

**Why it happens:**
The version is expressed in the URL, not in an obvious body field, and the redirect is transparent to most HTTP clients.

**How to avoid:**
1. Always request an **explicit** version and always record what you actually got. Store `resolved_document_uri` (from `/Legislation/@DocumentURI`) and derive `version: revised | enacted | point-in-time` from its suffix.
2. Follow redirects but persist the **final** effective URL, never the requested one.
3. Assert that the resolved version matches the requested one; if you asked for revised and got `/enacted`, that is a *finding to record in frontmatter*, not a silent pass.
4. Emit `version`, `valid_at` (`<dct:valid>`), and `last_modified` (`<dc:modified>`) into every UK law's frontmatter, and render them on the page.
5. **Scope decision:** restrict the v1.1 starter batch to `ukpga` items that have a genuine revised version. Excluding SIs from the starter batch sidesteps the not-revised problem entirely for this milestone.

**Warning signs:**
Any fetched document whose `DocumentURI` ends `/enacted` when you asked for current. A `uksi` item in the batch. Frontmatter with no version field.

**Phase to address:** `UK-Scope` (decide the version policy and batch composition), enforced in `UK-Fetch`.

---

### Pitfall 3: Publishing text the source itself declares out of date (unapplied effects)

**What goes wrong:**
TNA ships known-but-not-yet-incorporated amendments as machine-readable metadata rather than editing the text. Verified counts: Human Rights Act 1998 has **5** `<ukm:UnappliedEffect>` entries; Equality Act 2010 has **24**, several with `RequiresApplied="true"`. On legislation.gov.uk these produce the orange "There are changes that may be brought into force / changes not yet applied" banner. If you extract only the body text you strip that warning and publish a document that the authoritative publisher explicitly says is not up to date — while your site presents it as the readable, current law.

For a project whose stated value is "find and read any law in plain readable form" and whose CLAUDE.md rule is *"prefer explicit uncertainty over incorrect confidence,"* dropping this is the single worst fidelity failure available in the UK source.

**Why it happens:**
The data lives in `<ukm:Metadata>`, not in the body. Body-only extraction (`/body/data.xml`, or XPath from `<Body>`) never sees it.

**How to avoid:**
Parse `<ukm:UnappliedEffects>` and materialise it. Each `<ukm:UnappliedEffect>` carries `AffectedProvisions`, `AffectingTitle`, `AffectingURI`, `Type` (e.g. `"excluded by 1997 c. 43, s. 34A (as inserted)"`), `AffectingEffectsExtent` and `RequiresApplied`. Minimum viable treatment:
- Frontmatter `unapplied_effects_count: 24`.
- A rendered banner block at the top of the law page when the count is > 0, mirroring TNA's own wording and linking to the source.
- Per-provision markers where `ukm:AffectedProvisions/ukm:Section/@Ref` identifies a specific section.
This is also the cleanest reuse of the project's existing `[UNCERTAIN TEXT]` / annotated-metadata philosophy.

**Warning signs:**
A UK law page that renders more confidently than legislation.gov.uk's own page for the same Act. No `ukm:` namespace handling in the converter.

**Phase to address:** `UK-Convert` (extract), `UK-Site` (render the banner).

---

### Pitfall 4: Prospective and repealed provisions are inside the default XML

**What goes wrong:**
The "current" revised XML contains provisions that are **not law today**. Verified in Equality Act 2010 revised XML: `Status="Prospective"` ×17, `Status="Repealed"` ×2 (including the whole of `Schedule 24`, which is present with full text and `RestrictStartDate="2020-12-31"`), and `Match="false"` ×18.

A naive "walk the tree, emit the text" converter publishes not-yet-in-force provisions and repealed schedules as operative law, with no marking. This is a *substantively wrong law*, not a formatting bug.

**Why it happens:**
The status lives in an attribute on the container element, not in the text. `.itertext()`-style extraction — which is exactly the shortest path from XML to Markdown — discards it.

**How to avoid:**
- Treat `@Status` and `@Match` as first-class. Never emit a node with `Status="Repealed"` or `Match="false"` as ordinary body text.
- Decide the policy explicitly in `UK-Scope`. Recommended: **omit** `Status="Repealed"` / `Match="false"` provisions from the body but list them in a "Repealed provisions" appendix with their numbers (so numbering gaps are explained rather than mysterious); **render** `Status="Prospective"` provisions inline but wrapped in an explicit not-yet-in-force callout.
- Add a validator that fails the build if any `Status` value the converter does not recognise appears in a source document (defensive against schema values you haven't met yet).

**Warning signs:**
Your Markdown for an Act is longer than the rendered legislation.gov.uk page. A schedule with no corresponding live content on the source site. Any `Status=` attribute unhandled in the converter.

**Phase to address:** `UK-Scope` (policy), `UK-Convert` (implementation), `UK-Validate` (unknown-status guard).

---

### Pitfall 5: Extent — one Act, four different laws, sometimes at word level

**What goes wrong:**
A single UK-wide Act does not say the same thing in every jurisdiction. Verified in Equality Act 2010: `RestrictExtent` values across the document are `E+W+S` (191), `E+W` (14), **`S` (8)**, `E+W+S+N.I.` (3), `E+W+N.I.` (1) — i.e. eight provisions are Scotland-only inside an Act you'd label "UK".

Worse, extent applies **inside a sentence**. Real markup from section 1(3):

```xml
<Repeal ChangeId="..." RetainText="true" SubstitutionRef="..." Extent="S">3</Repeal>
```

That is subsection **(3) repealed for Scotland only, text retained** for England & Wales. Flatten the tags and you produce a paragraph that is simultaneously in force and repealed depending on where the reader is standing — presented with no qualification whatsoever.

**Why it happens:**
Extent has no analogue in Israeli legislation. There is nothing in the existing pipeline, schema, or mental model that prompts you to look for it, and the Israel-derived converter has no place to put it.

**How to avoid:**
- Carry `RestrictExtent` from `/Legislation/@RestrictExtent` into frontmatter as `extent: "E+W+S+N.I."`.
- Carry per-provision `RestrictExtent` into the rendered Markdown wherever it **differs from the parent**. This is a natural fit for the project's existing margin-note convention:
  `> [Extent — Section 1(3)] Scotland only`
- Never drop `<Repeal @Extent>` / `@RetainText`. `RetainText="true"` means "keep showing this text but it is repealed for the listed extent" — that has to survive into the output as an explicit annotation.
- Add a validator: any provision whose `RestrictExtent` differs from the document-level extent must have an extent annotation in the emitted Markdown.

**Warning signs:**
No `extent` key in UK frontmatter. Grep of `laws/uk/*.md` finds zero occurrences of "Scotland" / "Northern Ireland" as annotations. Converter code that reads element text without inspecting `Repeal` attributes.

**Phase to address:** `UK-Convert` + `UK-Validate`; display in `UK-Site`.

---

### Pitfall 6: `<BlockAmendment>` — quoted text from *another* Act, with its own numbering, inlined in this one

**What goes wrong:**
UK Acts routinely amend other Acts by quoting replacement text. In CLML that quoted text is a real `<BlockAmendment>` subtree containing full `<P3><Pnumber>a</Pnumber><P3para><Text>…` structure. Verified: **32** `<BlockAmendment>` elements in Equality Act 2010, plus `<AppendText>.</AppendText>` carrying the trailing punctuation that closes the quotation.

A naive recursive walk emits that quoted `(a)` as if it were a provision of the Equality Act, at a hierarchy level it doesn't belong to. Two of the project's core rules break at once: numbering is no longer preserved exactly, and hierarchy has been invented. Downstream, your numbering validator sees a stray `(a)` in the middle of section 118(5) and reports garbage.

**Why it happens:**
`<BlockAmendment>` looks structurally identical to real provisions. There is no equivalent construct in the Israeli PDFs — Knesset amendment text arrives as prose, so the pipeline never learned to distinguish quoted from operative text.

**How to avoid:**
- Explicitly handle `<BlockAmendment>` (and `<BlockText>`, `<AppendText>`) as **quoted content**. Render as a blockquote with an explicit marker, never as headings:
  `> [Quoted amendment text — inserted into <target>]`
- Suppress heading generation and ID/anchor generation for anything inside a `BlockAmendment` subtree.
- Exclude `BlockAmendment` descendants from the numbering validator's input entirely.
- Note `TargetClass` / `TargetSubClass` / `Context` attributes are frequently `"unknown"` — do not build logic that depends on them being populated.

**Warning signs:**
Duplicate `(a)`/`(b)` headings within one section. Anchor ID collisions. A numbering validator reporting hundreds of "orphan subsection" errors on a modern Act.

**Phase to address:** `UK-Convert`, with a dedicated `UK-Validate` check that no heading is emitted from inside a `BlockAmendment`.

---

### Pitfall 7: Stripping amendment markup destroys the square-bracket convention

**What goes wrong:**
Revised UK legislation uses a strict, legally meaningful typographic convention: **inserted or substituted text appears in square brackets**, **repealed/omitted text appears as `. . . . . .`**, and every one of those is tied to an F-note explaining which instrument made the change. In CLML this is `<Addition>`, `<Substitution>`, `<Repeal>`, each with `ChangeId` and `CommentaryRef` pointing at a `<Commentary Type="F">`. Verified volumes in Equality Act 2010: `Addition` ×2614, `Substitution` ×373, `Repeal` ×34, `Commentary Type="F"` ×557.

The markup nests — real example from the HRA:
```xml
<Addition ChangeId="d29p369" CommentaryRef="c18838751">…the <Substitution ChangeId="key-fae7…" CommentaryRef="…">…
```
and `<Addition>` can wrap a `<Pnumber>`, i.e. the *section number itself* is an insertion.

If you `.itertext()` these away you get grammatically correct current text — which reads beautifully and quietly tells the reader that every word of it was in the original Act. That is a false statement about the law.

**Why it happens:**
Stripping tags is the one-line solution and the output *looks* right. Nothing fails.

**How to avoid:**
Pick one of two defensible policies in `UK-Scope` and implement it consistently:
- **(A) Faithful:** render `[ ]` around `Addition`/`Substitution` content and a superscript F-marker linking to a collected annotations section at the bottom of the file, mirroring legislation.gov.uk. Highest fidelity, matches the source exactly, noisier to read.
- **(B) Clean-with-disclosure:** render clean text but emit a per-provision annotation (`> [Amended — s. 2(3): words inserted by …]`) built from the `<Commentary Type="F">` payload, plus a document-level `amended: true` and a link to the source. Readable, still honest.

Whichever you choose, **never** silently drop `<Repeal RetainText="true">` (see Pitfall 5) and never drop the F-note text — the commentary contains the citing instrument and commencement date, which is exactly the "attached metadata" the project already models for margin notes.

**Warning signs:**
`laws/uk/*.md` contains no square brackets and no annotation blocks for an Act you know has been heavily amended. Converter code calling `''.join(node.itertext())`.

**Phase to address:** `UK-Scope` (choose policy), `UK-Convert`.

---

### Pitfall 8: Reusing the Gemini reconciliation step on already-authoritative XML

**What goes wrong:**
`pipeline/reconcile.py` exists, works, and is the obvious thing to point at UK content. It is the wrong tool here, and the failure mode is invisible.

Its whole justification is triangulating **two noisy witnesses** (`native.txt` + `ocr.txt`) of a scanned Hebrew PDF. legislation.gov.uk XML is not a noisy witness — it is the King's Printer's own structured text, with hierarchy already explicit in `<P1group>/<P1>/<P2>/<P3>/<P4>` and `<Pnumber>`. There is nothing to reconcile. Handing it to an LLM introduces exactly the risks CLAUDE.md forbids:
- Normalising typographic quotes, en/em dashes and the `. . . . . .` omission convention.
- "Helpfully" closing numbering gaps left by repeals (see Pitfall 9) — i.e. inventing a provision.
- Expanding or contracting statutory abbreviations ("S.I. 2001/3500").
- Rewording archaic drafting into modern English.
- **Silent truncation.** `reconcile.py`'s own comment records that thinking tokens caused silent truncation on long Knesset documents. Equality Act 2010's XML is **3.5 MB**; Data Protection-scale Acts are 1.8 MB. These are one to two orders of magnitude larger than the Knesset PDFs the prompt was tuned on. Truncation here means a law that just stops mid-Schedule, with valid frontmatter.

**Why it happens:**
Sunk-cost reuse plus a genuine-seeming argument ("the LLM will make it prettier / handle the weird cases"). The output is fluent, so review passes.

**How to avoid:**
- **Make the UK converter deterministic and LLM-free.** XML → Markdown via an explicit XSLT or lxml tree walk. This is a stated milestone decision already ("don't reuse Israel's OCR/Gemini pipeline blindly") — hold the line on it.
- If an LLM is used at all in v1.1, confine it to work where it **cannot touch statutory text**: generating the `description` SEO field, proposing a category, or drafting a plain-English summary rendered in a clearly separated block. Never in the path that produces the operative text.
- Enforce mechanically: a `UK-Validate` check that every `<Text>` node's normalised string content from the source XML appears verbatim in the emitted Markdown. On clean XML this round-trip check is *achievable* — it was never achievable for the OCR pipeline. That is the real prize of the structured source, and it should be a phase exit criterion.

**Warning signs:**
`GEMINI_API_KEY` referenced anywhere in `pipeline_uk/`. A UK Markdown file whose text differs from the source XML under whitespace-normalised comparison. Output that ends abruptly.

**Phase to address:** `UK-Scope` (architectural commitment), enforced by the round-trip check in `UK-Validate`.

---

### Pitfall 9: Porting the Israeli numbering-continuity validator produces a false-positive flood

**What goes wrong:**
CLAUDE.md specifies a validator that flags `(a) (b) (d)` as a missing `(c)`. In UK revised legislation, **gaps are correct and expected**:
- Repealed sections are removed, leaving legitimate gaps.
- Inserted sections use alphanumeric suffixes — Equality Act 2010's live section list is verifiably `… 18, 19, **19A**, 20, 21 …`.
- Schedule paragraphs use `<Pnumber>` sequences independent of the body's.
- CLML emits synthetic wrapper IDs such as `schedule-24-paragraph-**wrapper28n1**` for unnumbered wrapper paragraphs.
- Pre-1963 Acts carry regnal chapter numbers (`5_and_6_Eliz_2`) rather than plain integers.

Run the Israel validator unchanged and every Act reports dozens of errors. The predictable human response is to disable or ignore the validator — at which point real structural corruption (e.g. Pitfall 6's stray quoted numbering) also goes unnoticed.

**Why it happens:**
The validator is generic-sounding ("numbering continuity") so it looks portable. Its assumption — dense integer/Hebrew-letter sequences — is Israel-specific.

**How to avoid:**
Write a **separate UK validator**, do not parameterise the Israeli one. UK rules:
- Accept alphanumeric provision numbers (`19A`, `19ZA`, `4B`).
- Do not flag gaps; instead **cross-check** them: a gap at *n* is acceptable only if a `<Commentary Type="F">` referenced from the surrounding provisions records the repeal, or the number appears in the repealed-provisions appendix. Flag *unexplained* gaps only.
- Validate against `/Legislation/@NumberOfProvisions` as a count oracle — the source tells you how many provisions it thinks there are.
- Skip everything inside `BlockAmendment`.
- Validate schedule numbering in its own namespace, not against body sections.

**Warning signs:**
Validator output measured in hundreds of lines per Act. Anyone proposing a `--no-validate` flag.

**Phase to address:** `UK-Validate` (new validator, built fresh).

---

### Pitfall 10: Every UK page will render right-to-left and claim to be Hebrew/Israeli

**What goes wrong:**
This is not hypothetical — it is what the current code does today, verified by reading it.

`site/src/css/custom.css:59-64` applies globally to every doc page in the site:
```css
.markdown { direction: rtl; text-align: right; ... }
```
There is no locale or path scoping. Plus `aside.theme-doc-sidebar-container { order: 2 }` forces the sidebar to the right for all docs, and `.theme-doc-toc-desktop { display: none !important }` kills the table of contents site-wide — reasonable for Hebrew law text, wrong for long UK Acts where a ToC is the primary navigation aid.

`site/src/theme/DocItem/Content/index.jsx` unconditionally injects, on **every** doc page:
```jsx
<html lang="he" dir="rtl" />
<meta property="og:locale" content="he_IL" />
```
and JSON-LD with `legislationJurisdiction: {'@type':'Country', name:'Israel'}`, `inLanguage: 'he'`, and `legislationStatus` derived from `law_validity === 'תקף'`.

So a UK Act would ship declaring itself Hebrew, right-to-left, and Israeli legislation — to users, to screen readers, and to Google, immediately after a deliberate SEO pass that made those tags authoritative.

**Why it happens:**
The Israel-only assumption was correct when written and is invisible because it is expressed as a global default rather than a condition.

**How to avoid:**
Introduce a `country` discriminator before any UK content ships:
- Add `country: uk` / `country: israel` to frontmatter (backfill Israel — 111 files, scriptable, and `pipeline/backfill_seo_meta.py` is a working precedent for exactly this kind of pass).
- In `DocItem/Content/index.jsx`, derive `lang`, `dir`, `og:locale`, `inLanguage` and `legislationJurisdiction` from `country`, with no hardcoded fallback to Hebrew.
- Scope RTL CSS behind a body/html attribute or `[dir='rtl']` rather than applying it to `.markdown` unconditionally.
- Reconsider `hide_table_of_contents` for UK — long Acts need it; the CSS `!important` kill rule must become conditional.

**Warning signs:**
`view-source:` on a UK law page showing `lang="he"`. UK text rendering right-aligned. Lighthouse/axe reporting a language mismatch.

**Phase to address:** `UK-Site` — and it must land **before** the first UK law is deployed, not after.

---

### Pitfall 11: The metadata pipeline is Israel-shaped, and its fallbacks are Hebrew

**What goes wrong:**
`site/scripts/generate-law-meta.js` (run via `prebuild`/`predeploy`) reads **only** `../../laws/israel`, keys the output map by bare `law_id` in a single flat namespace, maps `ministry_ids` through a hardcoded Knesset `KNS_IsraelLawMinistry` 1–50 table, and derives status from Hebrew strings (`תקף` / `בטל` / `פקע`).

If UK laws are simply added to `laws/uk/`, they are absent from `GENERATED_LAW_META`. Then in `DocItem/Content/index.jsx`:
```jsx
const meta = GENERATED_LAW_META[id] || {};
const statusHe = meta.statusHe || 'תקף';
```
Every UK law page renders a **Hebrew "תקף" status badge**. The failure is not a crash — it is a confidently wrong Hebrew label on English legislation.

There is also a live ID-namespace hazard: the map is keyed by bare ID with no country prefix, so any UK identifier scheme that produces a bare number collides with Israeli `law_id`s.

**How to avoid:**
- Make `generate-law-meta.js` iterate a list of country directories and key entries as `"<country>:<id>"` (or nest by country). Change the lookup in `DocItem` to match.
- Remove the `|| 'תקף'` fallback outright — an unknown status must render nothing or "Unknown", never a default in the wrong language.
- Do **not** shoehorn UK into `ministry_ids`. UK legislation has no equivalent; the correct UK analogues are legislation type (`ukpga`/`uksi`/`asp`), year, and extent. Give the group-by control a country-aware option set.
- Do **not** force UK into the existing 50-slug Israeli taxonomy — `knesset`, `basic-laws`, `religion`, `economic-arrangements` have no UK meaning. Either add UK-specific slugs alongside, or (simpler for a starter batch) leave `category` empty for UK and group by legislation type + year.

**Warning signs:**
Hebrew text on a UK page. `GENERATED_LAW_META` entry count unchanged after importing UK laws. Any UK law showing a ministry.

**Phase to address:** `UK-Site`.

---

### Pitfall 12: The sidebar grouping script silently excludes UK laws (numeric-ID regex)

**What goes wrong:**
`site/src/clientModules/lawSort.js` identifies laws by:
```js
function lawIdFromHref(href) {
  const m = (href || '').match(/\/laws\/(\d+)/);   // digits only
  return m ? m[1] : null;
}
```
UK slugs (`/laws/uk/ukpga-1998-42`, or anything non-numeric) never match, so UK entries are dropped from `byId` and simply do not appear in any group. Meanwhile:
- `_showGroupBy = location.pathname.includes('/laws')` is true for `/laws/uk/...`, so the **Group by** control is visible on UK pages while doing nothing useful.
- The selector `a[href*="/laws/"]` *does* match UK links, so if UK and Israel ever share a sidebar the script will detach UK `<li>` nodes (via `li.remove()`) and never re-append them — **items vanish from the sidebar**.
- Sorting uses `localeCompare(a, b, 'he')` and the option list includes `Ministry`.

**How to avoid:**
- Replace the numeric regex with a country-aware parser producing the same `"<country>:<id>"` key used by `generate-law-meta.js`.
- Gate `_showGroupBy` and the option set on the detected country, not on `pathname.includes('/laws')`.
- Use the country's locale for `localeCompare`.
- Add a guard: if an `<a href*="/laws/">` is detached but produces no key, re-append it rather than dropping it.

**Warning signs:**
UK laws missing from the sidebar while their pages load fine. Sidebar item count < file count. Group-by dropdown visible with irrelevant options.

**Phase to address:** `UK-Site`.

---

### Pitfall 13: Docs-plugin instancing and the URL/SEO trap

**What goes wrong:**
The site currently has exactly one docs instance, configured in the preset:
```ts
docs: { path: '../laws/israel', routeBasePath: 'laws', sidebarPath: './sidebars.ts' }
```
Docusaurus multi-instance rules require each additional instance to have a unique `id`, unique `path`, unique `routeBasePath`, and **its own sidebar file** — and navbar doc items must carry `docsPluginId`. Adding UK by editing the preset in place (rather than adding a second `@docusaurus/plugin-content-docs` entry to `plugins`) is the standard first mistake.

The sharper trap is URLs. Israel's laws currently live at `/codex-civica/laws/<numeric-id>`, and those URLs were just made canonical by the SEO work (JSON-LD `url` built as `siteConfig.url + metadata.permalink`, `sitemap.xml` referenced from `static/robots.txt`). Restructuring to `/laws/israel/<id>` for symmetry with `/laws/uk/<id>` **breaks every indexed URL and every JSON-LD `url`** for 111 already-deployed laws.

**How to avoid:**
Two viable options — decide in `UK-Scope`:
- **(A) Leave Israel where it is.** Israel stays at `routeBasePath: 'laws'`; UK gets a second instance at `routeBasePath: 'uk'` or `'laws-uk'`. Asymmetric, but zero SEO breakage. Recommended for v1.1.
- **(B) Restructure to `/laws/israel` + `/laws/uk`.** Cleaner long-term; requires `@docusaurus/plugin-client-redirects` with 111 explicit `/laws/<id>` → `/laws/israel/<id>` redirects, a regenerated sitemap, and accepting a re-index period.

Also note `onBrokenLinks: 'warn'` and `onBrokenAnchors: 'ignore'` are currently set. A UK import that generates internal links from `<Citation>` URIs will produce many links to laws not yet in the corpus, and every one will be swallowed as a warning. Cap this in `UK-Validate` rather than relying on the build.

**Warning signs:**
Docusaurus warning about duplicate plugin ids or route conflicts. A drop in indexed pages after deploy. Build log warnings scrolling past.

**Phase to address:** `UK-Scope` (URL decision), `UK-Site` (implementation).

---

### Pitfall 14: Schedules dropped or mis-modelled — and in UK Acts that's most of the content

**What goes wrong:**
Two related errors.

First, **dropping schedules entirely.** CLML exposes `<Body>` and `<Schedules>` as siblings, and the API offers `/body/data.xml` as a lighter fetch. Take the light path and you lose Schedule 1 of the Human Rights Act (the actual text of the Convention rights — i.e. the entire point of the Act) and 28 of the Equality Act's schedules. In UK drafting, schedules routinely carry the operative detail.

Second, **modelling schedules as sections.** Their element vocabulary genuinely differs:
```xml
<Schedule id="schedule-1" RestrictExtent="E+W+S+N.I." RestrictStartDate="2004-06-22">
  <Number>SCHEDULE 1</Number>
  <TitleBlock><Title>The Articles</Title></TitleBlock>
  <Reference>Section 1(3).</Reference>
  <ScheduleBody> … <Part> … </ScheduleBody>
</Schedule>
```
Units are **paragraphs**, not sections (`/schedule/1/paragraph/2`), numbering restarts, `<Part>` nests differently inside `<ScheduleBody>`, and `<Reference>` is the back-link to the enabling section — a structurally meaningful relationship that has no counterpart in the Israeli model and gets thrown away by default.

**How to avoid:**
- Always fetch the whole item (`/data.xml`), never `/body`.
- Give schedules their own converter branch and their own anchor namespace (`#schedule-1-paragraph-2`).
- Preserve `<Reference>` as an explicit annotation: `> [Enabled by — Section 1(3)]`.
- Validate that emitted schedule count equals `<Schedule>` element count, and that schedule paragraph numbering is validated separately from body sections.

**Warning signs:**
A UK Markdown file with no `SCHEDULE` heading for an Act you know has schedules. Anchor collisions between `section/3` and `schedule/1/paragraph/3`.

**Phase to address:** `UK-Convert`, verified in `UK-Validate`.

---

### Pitfall 15: Fair-use / rate-limit violations that look like intermittent bugs

**What goes wrong:**
Documented limit: **3,000 API requests per IP per 5 minutes**; exceeding it returns **403 Forbidden**, not 429. A 403 is easily misread as an auth or blocking problem (and this team already has a WAF-blocking scar from Knesset/Reblaze, priming exactly that misdiagnosis). TNA's Fair Use Policy also **requires a User-Agent** on API requests, and advises a **minimum 10 seconds between retries** for dynamically generated content. Large items compound it — Equality Act 2010 is 3.5 MB per request.

**How to avoid:**
- Set an identifying `User-Agent` (project name + contact URL) on every request. Do not ship a library default.
- Rate-limit client-side well under the ceiling (a few requests/second is ample for a starter batch) with backoff ≥ 10 s on retry.
- Cache raw XML on disk under `data/raw/uk/` and never re-fetch what you already have — the milestone's own precedent (i-dot-ai's `lex` project reports tens of hours for a full crawl) argues for cache-first from day one.
- Treat 403 as "back off", not "blocked" — retry after a cooling period before escalating.
- Note `data/raw/` and `*.pdf` are already gitignored, so raw cache stays out of Git by default. That is correct; just be aware PDF-only items therefore leave no archived artifact.

**Warning signs:**
Sporadic 403s that resolve on retry. Fetch runs that fail differently each time. No `User-Agent` header in the HTTP client setup.

**Phase to address:** `UK-Fetch`.

---

### Pitfall 16: Atom feed pagination — silently importing 20 of N

**What goes wrong:**
Verified: `GET /ukpga/2010/data.feed` returns `<openSearch:totalResults>41</openSearch:totalResults>`, `<openSearch:itemsPerPage>20</openSearch:itemsPerPage>`, and a single `<link rel="next" href=".../data.feed?page=2">`. Read page 1 only and you import 20 of 41 with no error. On a "starter batch" this is invisible — the batch was always going to be partial, so a truncated list looks like success.

**How to avoid:**
Always read `openSearch:totalResults`, follow `rel="next"` until exhausted, and **assert** collected count == totalResults before proceeding. Log both numbers.

**Warning signs:**
Any collected count that is an exact multiple of 20. No pagination loop in the fetcher.

**Phase to address:** `UK-Fetch`.

---

### Pitfall 17: Regnal-year URIs break identity and dedup

**What goes wrong:**
Pre-1963 Acts are canonically identified by regnal year, not calendar year. Verified: `/ukpga/1957/20` **301-redirects** to `/ukpga/Eliz2/5-6/20`, and the metadata carries `<ukm:AlternativeNumber Category="Regnal" Value="5_and_6_Eliz_2"/>`. If you key files, frontmatter and `source_url` off the *requested* URI, the same Act can enter the corpus under two identities, and the stored source link may not be the canonical one.

**How to avoid:**
Derive the canonical identity from `/Legislation/@IdURI` (the version-independent identifier) after following redirects — never from the URL you typed. Use it to build both the filename and `source_url`. Note that the regnal path segment contains `/` characters (`Eliz2/5-6/20`), so filename slugification must handle it deliberately (`ukpga-Eliz2-5-6-20.md`).

**Warning signs:**
Two files for one Act. `source_url` that 301s. Filename slug logic assuming exactly three URI components.

**Phase to address:** `UK-Fetch` (identity), `UK-Validate` (duplicate detection).

---

### Pitfall 18: Bilingual Welsh legislation published as English-only

**What goes wrong:**
Acts of Senedd Cymru (`asc`) and Welsh SIs have Welsh and English texts that are **equally authoritative in law**. Verified on `asc/2020/1`: `<dc:language>en</dc:language>` with alternate links to `/asc/2020/1/welsh`, `/asc/2020/1/enacted/welsh`. Fetch the default and you publish half of a bilingual law while labelling it complete — the same class of error as publishing an English translation of a Hebrew law as if it were the source.

Note the project has form here: it deliberately kept Hebrew as the source of truth and declared translations out of scope. The equivalent discipline for Wales is either both texts or neither.

**How to avoid:**
Exclude `asc` / `wsi` from the v1.1 starter batch (recommended — keeps the batch to `ukpga`, which is monolingual). If included later, fetch both `/welsh` and default, and model the pair explicitly rather than picking one.

**Warning signs:**
An `asc` item in the batch. A law page with no language indicator.

**Phase to address:** `UK-Scope` (batch composition).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `''.join(node.itertext())` to get provision text | Converter written in an afternoon | Destroys Addition/Substitution/Repeal semantics, extent, status, and BlockAmendment boundaries — i.e. produces legally wrong text that reads fine (Pitfalls 4–7) | Never |
| Point `pipeline/reconcile.py` (Gemini) at UK XML | Reuses working code, "handles edge cases" | Paraphrase/normalisation risk on authoritative text; silent truncation on 3.5 MB inputs; forfeits the verbatim round-trip check that clean XML uniquely makes possible | Never for operative text; acceptable for `description`/summary fields rendered separately |
| Fetch `/data.xml` with no explicit version | Simplest URL | Silently mixes revised and enacted text across the corpus (Pitfall 2) | Never — always record the resolved version |
| Reuse `sidebars.ts` and the preset docs instance for UK | One fewer config file | Route/id conflicts, Israel sidebar swallows UK, no per-instance control | Never (Docusaurus requires unique id/path/routeBasePath) |
| Fetch `/body/data.xml` instead of full item | Smaller payloads, faster | Loses all schedules and all `ukm:` metadata including unapplied effects | Never |
| Reuse the Israel numbering validator for UK | No new code | False-positive flood → validator disabled → real corruption missed (Pitfall 9) | Never |
| Leave `country` out of frontmatter, infer from path | No backfill of 111 Israeli files | Every consumer (meta generator, DocItem, sort module, search) reimplements path-sniffing; the Hebrew-default bugs stay latent | Only if a single path-parsing helper is the sole source of truth |
| Skip the unapplied-effects banner in v1.1 | Ships sooner | Publishes stale law more confidently than the official source does — directly contradicts "prefer explicit uncertainty" | Never; frontmatter count is the minimum |
| Include `uksi` in the starter batch | More laws, looks more complete | SIs are not revised — amendments are not incorporated; corpus silently mixes two meanings of "current" | Only with an explicit "as made — not amended" banner on every SI page |
| Skip disk caching of raw XML | Less code | Repeated crawls risk 403s and waste; no reproducibility of a conversion | Only for a <10-item spike |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| legislation.gov.uk API | Treating HTTP 200 as "got the law" | Gate on `NumberOfProvisions > 0` and presence of `<Body>`/`<Schedules>` |
| legislation.gov.uk API | No `User-Agent`; interpreting 403 as a WAF block | Identifying UA on every request; treat 403 as rate-limit, back off ≥10 s, stay well under 3,000 req/5 min |
| legislation.gov.uk API | Reading only page 1 of `/data.feed` | Follow `rel="next"`; assert count == `openSearch:totalResults` |
| legislation.gov.uk API | Keying identity off the requested URL | Key off `@IdURI` after redirects; store `@DocumentURI` for version provenance |
| legislation.gov.uk API | Assuming SIs are revised like Acts | Secondary legislation is **not** revised (except NI Orders in Council) — label as-made explicitly |
| CLML XML | Ignoring the `ukm:` metadata namespace | Parse `ukm:UnappliedEffects`, `ukm:Alternatives`, `ukm:AlternativeNumber`, `dct:valid`, `dc:modified` |
| CLML XML | Assuming `TargetClass`/`Context` on `BlockAmendment` are populated | Verified frequently `"unknown"` — never depend on them |
| CLML XML | Extracting `<Pnumber>` text naively | `<Pnumber>` can contain `<CommentaryRef>`, `<Addition>` and `<Repeal>` children — extract deliberately |
| Docusaurus docs plugin | Editing the preset instance to add UK | Add a second `@docusaurus/plugin-content-docs` entry with unique `id`, `path`, `routeBasePath`, `sidebarPath`; navbar items need `docsPluginId` |
| Docusaurus + SEO | Changing Israel's `routeBasePath` for symmetry | Either keep `/laws` for Israel, or add `@docusaurus/plugin-client-redirects` for all 111 existing URLs and regenerate the sitemap |
| Docusaurus i18n | Assuming `i18n.locales` handles per-document language | Site is `defaultLocale: 'en'`, `locales: ['en']` — per-doc `lang`/`dir` must come from frontmatter via the swizzled `DocItem`, not from i18n |
| `generate-law-meta.js` | Adding UK files without changing the key scheme | Namespace keys by country; remove the `\|\| 'תקף'` fallback |
| Local search (Phase 6, pending) | Configuring it after UK lands, for one instance only | Most Docusaurus local-search plugins take an explicit list of docs route base paths — configure for both instances, and be aware Hebrew and English tokenise differently |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fetching whole large Acts repeatedly | Slow runs, sporadic 403s | Disk-cache raw XML keyed by `IdURI` + version; conditional GET on `dc:modified` | Immediately at 3.5 MB/item; TNA explicitly advises against requesting entire large items |
| DOM-parsing multi-MB XML per law in one process | Memory growth across a batch | `lxml.etree.iterparse` or parse-and-release per document | ~50+ large Acts in one run |
| Docusaurus build time with two docs instances | `npm run build` minutes → tens of minutes | Keep UK a starter batch; if the corpus grows past a few thousand docs, Docusaurus docs recommend separate sites over more instances | Israel alone is heading to 718; adding a full UK Acts corpus (~4,000+ ukpga) would be the breaking point |
| `GENERATED_LAW_META` shipped as one JS object to the client | Growing JS bundle on every page | Already ~111 entries; split per country or move to a lazy-loaded JSON before the full corpus lands | Low thousands of entries |
| `lawSort.js` MutationObserver over a very long sidebar | Sidebar jank, layout thrash on mobile | It already rebuilds the whole list per route change; adding a second country doubles the node count | Noticeable in the high hundreds of items |
| Re-fetching the whole corpus to catch amendments | Long refresh cycles | Use `dc:modified`/`dct:valid` + the API publication log for incremental refresh | The first time you need to re-sync — and revised law *does* change (TNA targets applying effects within ~3 months of commencement) |

## Security / Legal-Compliance Mistakes

Domain-specific issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Republishing without OGL v3 attribution | Licence breach; TNA requires attribution for Open Government Licence content | Add the required OGL attribution statement to the site footer and to UK law page metadata; the footer currently says only "content derived from public legislation of the State of Israel" and must become country-aware |
| Assuming everything on legislation.gov.uk is OGL | Some content derives from EUR-Lex under Commission Decision 2011/833/EU; Explanatory Notes and PDFs can carry distinct terms | Record `dc:publisher` / `dc:contributor` per item; keep retained-EU-law items out of the starter batch |
| Presenting revised text as authoritative without provenance | Users relying on stale or partially-in-force law; reputational and (for a legal-information site) real-world harm | Mandatory per-page provenance block: version, `valid_at`, `last_modified`, unapplied-effects count, link to source |
| Committing raw fetch artefacts or API config | Leakage of keys/paths | Already handled — `data/raw/`, `*.pdf`, `.env` are gitignored and `pipeline/.env` is untracked (verified). Keep any UK fetcher config under the same rules |
| Unpinned GitHub Actions in the deploy workflow | Supply-chain risk on a site that publishes legal text | Pin action SHAs (already flagged in `.planning/codebase/CONCERNS.md`) |
| No CSP headers | XSS surface on a public reference site | Already flagged in CONCERNS.md; adding a second content source is a reasonable trigger to address it |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| UK Act rendered RTL with Hebrew status badge | Immediately signals the site is broken/untrustworthy for exactly the audience the milestone is courting | Country-driven `dir`/`lang`/labels (Pitfalls 10, 11) |
| ToC globally suppressed | A 218-section Act with no in-page navigation is unusable | Make `hide_table_of_contents` a per-country default; keep ToC for UK |
| No visible extent indicator | A Scottish reader reads an E+W-only provision as applying to them | Extent badge in the page header + inline annotations where a provision's extent differs from the Act's |
| No "not yet in force" / "repealed" marking | Reader acts on text that isn't law | Explicit inline callouts driven by `@Status` (Pitfall 4) |
| Amendment brackets stripped for readability | Reader believes the current wording is the original wording | Choose policy (A) or (B) from Pitfall 7 and state it in a site-wide "how to read these pages" note |
| Single "Group by: Ministry" control across both countries | Meaningless option on UK pages; erodes trust in the whole UI | Country-aware option sets (type/year/extent for UK) |
| Internal citation links pointing at laws not in the corpus | Dead-end clicks | Resolve `<Citation @URI>` against the local corpus; fall back to an outbound legislation.gov.uk link marked as external, never a broken internal link |
| Homepage country grid implying equal coverage | User expects the UK corpus to be as complete as Israel's | Show per-country counts and a "starter batch" qualifier |

## "Looks Done But Isn't" Checklist

- [ ] **UK law Markdown files:** often missing schedules — verify `SCHEDULE n` heading count equals `<Schedule>` element count in the source XML
- [ ] **UK law Markdown files:** often missing the unapplied-effects warning — verify `unapplied_effects_count` in frontmatter matches `<ukm:UnappliedEffect>` count (HRA: 5, Equality Act: 24)
- [ ] **UK law Markdown files:** often silently truncated — verify every source `<Text>` node appears verbatim (whitespace-normalised) in the output
- [ ] **UK law Markdown files:** often missing extent — verify `extent` frontmatter present, and every provision whose `RestrictExtent` differs from the document's carries an annotation
- [ ] **UK law Markdown files:** often contain quoted amendment text as real headings — verify no heading was emitted from inside a `BlockAmendment`
- [ ] **Fetcher:** often imports a truncated list — verify collected item count equals `openSearch:totalResults`
- [ ] **Fetcher:** often imports bodyless stubs — verify no output file where `NumberOfProvisions="0"`
- [ ] **Fetcher:** often records the wrong version — verify every record stores the resolved `DocumentURI` and a derived `version` field
- [ ] **Site:** often ships RTL/Hebrew on UK pages — verify `view-source` on a UK page shows `lang="en" dir="ltr"`, `og:locale` not `he_IL`, and JSON-LD `legislationJurisdiction` = United Kingdom
- [ ] **Site:** often drops UK from the sidebar — verify UK sidebar item count equals `laws/uk/*.md` count with the group-by control exercised in all modes
- [ ] **Site:** often leaves Hebrew fallbacks — grep the built `site/build/` output for `תקף` on UK routes; expect zero hits
- [ ] **Site:** often breaks existing SEO — verify all 111 pre-existing `/laws/<id>` URLs still resolve (200, not 301→404) and the sitemap contains both countries
- [ ] **Site:** footer/JSON-LD often still says Israel — verify the copyright line and OGL attribution are country-aware
- [ ] **Validator:** often just noise — verify a clean Act produces zero findings, and that a deliberately corrupted fixture produces exactly one

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Bodyless stubs published (P1) | LOW | Identify files under a size threshold, delete, add to skip list, add the `NumberOfProvisions` gate, re-run |
| Wrong version imported (P2) | LOW–MEDIUM | Deterministic converter means re-fetch and re-convert is cheap; cost is only reputational if it shipped. Recoverable *because* no LLM is in the path — a strong argument for Pitfall 8's recommendation |
| Amendment/extent/status semantics stripped (P4–P7) | MEDIUM | Requires converter rework then full re-conversion; raw XML cache makes re-conversion offline and free |
| Gemini paraphrase shipped into `laws/uk/` (P8) | **HIGH** | No mechanical way to distinguish paraphrase from source without re-deriving from XML; every affected file must be regenerated and manually spot-checked. This is why Pitfall 8 is a design-time decision, not a review-time one |
| Hebrew/RTL leakage on UK pages (P10, P11) | LOW | Config/component fix + rebuild; cost is only the window during which it was live and indexed |
| Israel URLs broken by restructuring (P13) | MEDIUM–HIGH | Add `plugin-client-redirects` for all old paths, regenerate sitemap, request re-index; expect weeks of degraded search visibility |
| Validator disabled due to false positives (P9) | MEDIUM | Rewrite as a UK-specific validator; re-audit every law imported while it was off |
| Rate-limit ban / sustained 403s (P15) | LOW | Stop, wait, add UA + throttle + cache, resume from the disk cache |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. Bodyless 200-OK stubs | UK-Fetch | No output file with `NumberOfProvisions="0"`; skip list populated |
| 2. Wrong version (enacted vs revised; SIs not revised) | UK-Scope → UK-Fetch | Every record has `version` + `resolved_document_uri`; batch contains no unlabelled `uksi` |
| 3. Unapplied effects dropped | UK-Convert → UK-Site | Frontmatter count matches source; banner renders when > 0 |
| 4. Prospective/repealed text published as current | UK-Scope → UK-Convert → UK-Validate | Zero unhandled `@Status` values; repealed content only in the appendix |
| 5. Extent ignored | UK-Convert → UK-Validate | Every divergent-extent provision carries an annotation; `extent` in frontmatter |
| 6. `BlockAmendment` treated as operative provisions | UK-Convert → UK-Validate | No heading emitted from inside `BlockAmendment`; no duplicate sibling numbers |
| 7. Amendment markup stripped | UK-Scope → UK-Convert | Chosen policy (A or B) applied uniformly; F-note payload present |
| 8. Gemini reused on clean XML | UK-Scope → UK-Validate | No LLM call in the text path; verbatim `<Text>` round-trip check passes on 100% of the batch |
| 9. Israeli numbering validator ported | UK-Validate | Clean Act → zero findings; corrupted fixture → exactly one |
| 10. Global RTL / hardcoded `lang="he"` | UK-Site (before first deploy) | `lang="en" dir="ltr"` + correct JSON-LD jurisdiction on UK pages |
| 11. Israel-shaped meta generator + Hebrew fallbacks | UK-Site | Zero `תקף` occurrences on UK routes in `site/build/` |
| 12. Numeric-only sidebar ID regex | UK-Site | Sidebar item count == UK file count in every group-by mode |
| 13. Docs instancing / URL & SEO breakage | UK-Scope → UK-Site | Clean build with no route warnings; all 111 legacy URLs still 200 |
| 14. Schedules dropped or mis-modelled | UK-Convert → UK-Validate | Schedule count matches; separate anchor namespace; `<Reference>` preserved |
| 15. Rate limit / fair use | UK-Fetch | UA set; throttle configured; cache-first; 403 handled as backoff |
| 16. Atom pagination truncation | UK-Fetch | Collected count == `openSearch:totalResults` |
| 17. Regnal-year URI identity | UK-Fetch → UK-Validate | Identity derived from `@IdURI`; no duplicate Acts |
| 18. Welsh bilingual half-publication | UK-Scope | No `asc`/`wsi` in the starter batch (or both texts modelled) |

## Sources

**Official (HIGH confidence)**
- legislation.gov.uk Developer Zone — https://www.legislation.gov.uk/developer
- Documented limitations (basedates, unrevised secondary legislation, data-quality caveats) — https://www.legislation.gov.uk/developer/limitations
- URI scheme (type codes, regnal years, `/enacted`, point-in-time, extent URIs, `/welsh`) — https://www.legislation.gov.uk/developer/uris
- Formats (`data.xml`, `data.feed`, `data.rdf`, `data.akn`) — https://www.legislation.gov.uk/developer/formats
- Data-reuse documentation, API overview — **rate limit 3,000 req / 5 min per IP → 403; User-Agent required; ≥10 s between retries; crawling explicitly permitted** — https://legislation.github.io/data-documentation/api/overview.html
- Coverage ("what we have") — pre-1988 gaps, Local/Private Acts PDF-only, amendments recorded from 1994, ~95% of primary legislation current — https://legislation.github.io/data-documentation/what-we-have.html
- Data model (items vs versions, effects, commencements) — https://legislation.github.io/data-documentation/model/overview.html
- XML/CLML format notes (`Match="false"`, `Status` = Prospective/Repealed/Discarded, `RestrictStartDate`/`RestrictEndDate`/`RestrictExtent`, `ukm:UnappliedEffects`, `IdURI` vs `DocumentURI`) — https://www.legislation.gov.uk/developer/formats/xml and https://legislation.github.io/data-documentation/formats/xml.html
- CLML schema reference — https://legislation.github.io/clml-schema/ and https://github.com/legislation/clml-schema
- Guide to Revised Legislation (square brackets for insertions, dots for omissions, F/C/I/E/M/P annotations, base dates, unapplied effects) — https://www.legislation.gov.uk/pdfs/GuideToRevisedLegislation_Oct_2013.pdf
- Understanding Legislation (enacted vs revised, commencement orders, extent vs territorial application, ~3-month target for applying effects) — https://www.legislation.gov.uk/understanding-legislation
- Annotation conventions (F = amendments, C = modifications not altering text, I = commencement, E = extent) — http://community.legislation.gov.uk/mediawiki/index.php?title=Editorial_Update/Annotation_Conventions
- Docusaurus multi-instance docs (unique `id`, `path`, `routeBasePath`, per-instance `sidebarPath`, `docsPluginId`) — https://docusaurus.io/docs/docs-multi-instance

**Live API probes, 2026-08-09 (HIGH confidence — first-hand)**
- `ukpga/1998/42/data.xml` — 306 KB revised, `NumberOfProvisions="57"`, `RestrictExtent="E+W+S+N.I."`, 5 `ukm:UnappliedEffect`; enacted version 189 KB
- `ukpga/2010/15/data.xml` — 3.5 MB; `Addition`×2614, `Substitution`×373, `Repeal`×34, `BlockAmendment`×32, `Commentary` F×557 / I×162 / C×23, `Status="Prospective"`×17, `Status="Repealed"`×2, `Match="false"`×18, `RestrictExtent` values `E+W+S`/`E+W`/`S`/`E+W+S+N.I.`/`E+W+N.I.`, 24 `ukm:UnappliedEffect`, section list containing `19A`, `<Repeal RetainText="true" Extent="S">`
- `ukla/1990/1/data.xml`, `ukpga/1957/20/data.xml` — HTTP 200, ~2 KB, `NumberOfProvisions="0"`, PDF-only via `ukm:Alternatives`
- `ukpga/1957/20/data.xml` → 301 → `ukpga/Eliz2/5-6/20/…/enacted/data.xml`, `ukm:AlternativeNumber Category="Regnal" Value="5_and_6_Eliz_2"`
- `ukpga/2010/data.feed` — 20 entries/page, `openSearch:totalResults` 41, `rel="next"`
- `asc/2020/1/data.xml` — `dc:language` `en` with `/welsh` alternates

**Third-party (MEDIUM confidence)**
- i-dot-ai `lex` (UK government AI incubator, legislation.gov.uk ingestion) — cache-first scraping, "several tens of hours" for a full crawl, start with a subset — https://github.com/i-dot-ai/lex/blob/main/src/lex/README.md
- GDS on legislation.gov.uk API design and pitfalls (performance, avoid requesting entire large items) — https://gds.blog.gov.uk/2012/03/30/putting-apis-first-legislation-gov-uk/

**Codebase inspection, 2026-08-09 (HIGH confidence — first-hand)**
- `/mnt/c/Dev/codex-civica/site/docusaurus.config.ts` — single docs instance at `../laws/israel`, `routeBasePath: 'laws'`; hardcoded 🇮🇱 navbar link; Israel-only footer copyright; `i18n` en-only
- `/mnt/c/Dev/codex-civica/site/src/css/custom.css` — global `.markdown { direction: rtl }`, right-side sidebar, global ToC suppression
- `/mnt/c/Dev/codex-civica/site/src/theme/DocItem/Content/index.jsx` — unconditional `lang="he" dir="rtl"`, `og:locale he_IL`, JSON-LD `legislationJurisdiction: Israel`, `inLanguage: 'he'`, `statusHe || 'תקף'` fallback
- `/mnt/c/Dev/codex-civica/site/scripts/generate-law-meta.js` — reads `laws/israel` only; flat `law_id` keys; Knesset ministry ID tables; Hebrew status mapping
- `/mnt/c/Dev/codex-civica/site/src/clientModules/lawSort.js` — `/\/laws\/(\d+)/` numeric-only ID regex; `pathname.includes('/laws')`; `localeCompare(..., 'he')`
- `/mnt/c/Dev/codex-civica/site/src/pages/index.tsx` — single-card country grid
- `/mnt/c/Dev/codex-civica/pipeline/reconcile.py` — Gemini 2.5 Flash two-witness reconciliation; thinking disabled due to silent truncation on long documents
- `/mnt/c/Dev/codex-civica/pipeline/link_resolver.py`, `cross_linker.py` — hardcoded `laws/israel` paths
- `/mnt/c/Dev/codex-civica/laws/israel/2000001.md` — frontmatter shape; no `country` field; numeric filename identity

---
*Pitfalls research for: UK legislation ingestion + second-country integration into Codex Civica*
*Researched: 2026-08-09*
