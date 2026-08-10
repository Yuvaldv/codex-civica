# Phase 8: UK Acquisition — Research

**Compiled:** 2026-08-10
**Status:** Distilled from milestone-level research (`.planning/research/{ARCHITECTURE,FEATURES,PITFALLS,STACK}.md`, all HIGH confidence, live-verified 2026-08-09) — no new agent research spawned. That research already answered every question this phase needs at the CLML-fetching level of detail; this document extracts exactly the Phase-8-relevant slice and adds the one new decision the milestone research left open (the concrete 10-of-13 batch cut).

---

## Scope (from ROADMAP.md / REQUIREMENTS.md)

**Goal:** England-applicable Acts land on disk as trustworthy CLML XML, with empty stubs and wrong-version documents rejected before they can reach conversion.

**Requirements:** UKFETCH-01, UKFETCH-02, UKFETCH-03 — download `ukpga`/`aep` CLML XML respecting fair-use rules; gate on `NumberOfProvisions > 0` + `<Body>`/`<Schedules>` presence; record resolved `DocumentURI` + version, restricted to genuine revised content (never `/enacted` silently mixed in).

**Explicit user constraint (2026-08-09, recorded in ROADMAP.md and STATE.md):** initial fetch capped at 10 Acts or fewer, selected from FEATURES.md's Tier A candidates. Do not fetch the full 13-Act list or beyond without an explicit later go-ahead.

**Out of scope for this phase:** anything in `pipeline/uk/clml.py` (CLML → IR), `render.py`, `validate.py` — Phase 8 only acquires and caches raw XML plus a manifest. No parsing beyond the root-element gate check needed to reject stubs.

---

## API Surface (STACK.md, PITFALLS.md — live-verified 2026-08-09)

| Endpoint | Purpose | Verified |
|---|---|---|
| `https://www.legislation.gov.uk/{uri-path}/data.xml` | Latest in-force (revised) CLML for an item | `200` |
| `https://www.legislation.gov.uk/{uri-path}/enacted/data.xml` | As-enacted text | `200` for some, `404` for others (e.g. Magna Carta, Habeas Corpus) — **never fetched by this phase**; only mentioned to explain why version resolution matters |
| `https://www.legislation.gov.uk/{uri-path}/resources/data.xml` | Metadata + list of alternative representations (PDF-only detection) | `200` — not needed if the root `data.xml` element already carries `NumberOfProvisions` (it does) |

`{uri-path}` is the item's canonical path exactly as it appears in the Tier A table below (e.g. `ukpga/1998/42`, or the pre-1963 regnal form `ukpga/Geo6/12-13-14/103`) — legislation.gov.uk resolves both forms; do not attempt to normalize regnal paths before fetching.

**Fair use (robots.txt + Fair Use Policy, fetched live):**
- `Crawl-delay: 5` seconds — the binding constraint, not the 3,000-req/5-min ceiling (10 items × ~5s ≈ 50s total, far under any ceiling)
- Mandatory, non-anonymous `User-Agent` with a contact URL, e.g. `CodexCivica (https://github.com/Yuvaldv/codex-civica)` — an anonymous/default `python-requests/x.x` UA is an explicit fair-use violation
- Sequential requests only — concurrency breaches the crawl-delay by construction
- `Disallow: */data.pdf`, `*/data.docx` in `robots.txt` — this phase never touches those paths anyway (XML only)

**No `/data.json` exists** (verified 404) and there is no bulk-download dataset usable without gated access — `data.xml` per item is the only supported path for a curated batch this size.

---

## The Two Hard Gates (PITFALLS.md Pitfall 1 & 2 — both MUST be enforced, not just logged)

### Gate 1 — Bodyless stub rejection (UKFETCH-02)

Some documents return HTTP `200` with a valid-but-empty XML shell — the real text exists only as a scanned pre-digital PDF (`ukm:Alternatives/ukm:Alternative[@Print="true"]`). Verified examples: `ukla/1990/1` (2.1 KB, `NumberOfProvisions="0"`), `ukpga/1957/20` (2.4 KB, `NumberOfProvisions="0"`, after a 301).

**Gate, applied before anything is written to `data/raw/uk/xml/`:** reject if `/Legislation/@NumberOfProvisions` is `"0"` or the attribute is absent, **or** there is no `<Body>` and no `<Schedules>` child under `/Legislation/Primary` (or `/Legislation/Secondary`). Log the reason and the URI; write nothing for that item; record `status: "pdf_only"` in the manifest rather than silently dropping the row (the manifest entry itself is the log of what was skipped and why).

None of the 10 selected Tier A items are stubs (all were live-verified with `NumberOfProvisions > 0`), but the check must run unconditionally on every fetch — the fixture value is not a substitute for the runtime gate, per CLAUDE.md ("validation errors must never be silently ignored") and per the roadmap's own success criterion 3.

### Gate 2 — Version resolution (UKFETCH-03)

`data.xml` with no explicit version segment returns the current **revised** text. Fetching `/enacted/data.xml` instead returns a different, often materially different document (Human Rights Act: enacted 189 KB vs revised 306 KB, and the enacted version carries no commencement/unapplied-effects metadata at all). The two must never be mixed in one batch.

**This phase fetches ONLY the un-suffixed `data.xml` path — never `/enacted/data.xml`, never a dated point-in-time path.** Record what was actually resolved: `doc_status` (from `ukm:PrimaryMetadata/ukm:DocumentClassification/ukm:DocumentStatus/@Value` — **corrected 2026-08-10 against live data; the attribute is `Value`, not `Category`, and the element is nested under `DocumentClassification`, not directly under `Metadata`** — expect `"revised"` for the whole batch since no `/enacted` fallback is used) and the root `DocumentURI` attribute (the URI the server actually served, which may differ from the requested path after a redirect — e.g. the 1957 Act's 301). A manifest entry with a missing or non-`revised` `doc_status`, or a `resolved_document_uri` that was never captured, is a fetch bug, not an acceptable variance.

Devolved/secondary legislation (`uksi` etc.) is generally **not** revised at all (as-made only) — irrelevant here since the batch is `ukpga`/`aep` only, but this is why the fetcher must not silently widen `type` beyond what the batch list specifies.

---

## Starter Batch: 10 of the 13 Tier A Candidates

FEATURES.md's Tier A table (13 Acts, live-verified sizes/structure) is reproduced in full at `.planning/research/FEATURES.md` lines 127–143. Per the user's ≤10 constraint, this phase drops exactly 3 — chosen for feature redundancy with an item that is kept, never for a feature that would otherwise be uncovered:

| Dropped | Reason |
|---|---|
| Parliament Act 1911 | "Pairs with #1 as an amend/amended pair" is a Phase-9/10 rendering nicety, not a fetch-layer concern; Parliament Act 1949 alone still covers "smallest real Act / smoke test" |
| Act of Settlement 1700 | "High citation density on a tiny Act" (42 citations) is dominated by Interpretation Act 1978, kept below, at 380 citations — same feature, better example |
| Habeas Corpus Act 1679 | "`/enacted` 404 — forces the revised-only path" is already the headline reason Magna Carta is in the batch ("best hard case in the batch"), kept below |

**The 10-item starter batch for this phase:**

| # | Act | URI | Type | XML size | Why kept |
|---|---|---|---|---|---|
| 1 | Parliament Act 1949 | `ukpga/Geo6/12-13-14/103` | ukpga | 9 KB | Smallest real Act — smoke test |
| 2 | Fixed-term Parliaments Act 2011 | `ukpga/2011/14` | ukpga | 26 KB | Title is literally "(repealed)" |
| 3 | Bill of Rights [1688] | `aep/WillandMarSess2/1/2` | aep | 36 KB | Archaic prose; `/enacted` exists (revised ≠ enacted still applies) |
| 4 | Magna Carta (1297) | `aep/Edw1cc1929/25/9` | aep | 38 KB | Mostly repealed, Roman numerals, no Part/Chapter, `/enacted` 404s |
| 5 | Union with Scotland Act 1706 | `aep/Ann/6/11` | aep | 56 KB | `Part=18` (Articles as Parts) |
| 6 | Defamation Act 2013 | `ukpga/2013/26` | ukpga | 111 KB | Extent E+W+S (not UK-wide) |
| 7 | Bribery Act 2010 | `ukpga/2010/23` | ukpga | 132 KB | Clean modern Act with Schedules |
| 8 | Computer Misuse Act 1990 | `ukpga/1990/18` | ukpga | 262 KB | 93 commentaries — annotation stress test |
| 9 | Human Rights Act 1998 | `ukpga/1998/42` | ukpga | 298 KB | Best all-round test case, 5 unapplied effects |
| 10 | Interpretation Act 1978 | `ukpga/1978/30` | ukpga | 483 KB | Highest citation density (380) |

Total ≈ 1.45 MB across 10 items — 3 `aep`, 7 `ukpga`, matching the ROADMAP goal's "`ukpga`/`aep`" framing (REQUIREMENTS.md's UKFETCH-03 phrasing of "restricting the starter batch to `ukpga` items" is read as the *version-policy* invariant — revised-only, no `/enacted` mixing — applying uniformly across both types, not as a type exclusion; the ROADMAP goal and success criterion 1 both explicitly name `ukpga`/`aep` together).

This is a hardcoded list, not a CSV-crawled discovery — ARCHITECTURE.md's per-year `data.csv` enumeration path (`Q4`) is Tier B/general-crawl machinery, explicitly out of scope until the ≤10 constraint is lifted by explicit go-ahead.

---

## `data/raw/uk/` Layout and Manifest Schema (ARCHITECTURE.md Q4)

```
data/raw/uk/
├── manifest_uk.json      # canonical item list — one entry per Tier A item, including skipped stubs
└── xml/                  # cached CLML, keyed by local slug
    ├── ukpga-1949-103.xml
    └── ...
```

No `listings/` directory in this phase (that's for the CSV-crawl path, not needed for a hardcoded 10-item list). `.gitignore` already excludes `data/raw/` — verified, no change needed.

**Slug scheme:** `{type}-{year}-{number}` derived from the fetched item's own metadata (`ukm:Metadata/ukm:Year/@Value`, `ukm:Metadata/ukm:Number/@Value`), never from the request URI path — this is what makes the pre-1963 regnal URIs (`ukpga/Geo6/12-13-14/103`) resolve to a clean `ukpga-1949-103` rather than leaking the regnal path into a filename.

**`manifest_uk.json` entry** (JSON list, same `ensure_ascii=False, indent=2` idiom as `manifest_laws.json` — see `pipeline/fetch.py:135-142`):

```json
{
  "slug": "ukpga-1998-42",
  "uri": "ukpga/1998/42",
  "type": "ukpga",
  "requested_url": "https://www.legislation.gov.uk/ukpga/1998/42/data.xml",
  "resolved_document_uri": "http://www.legislation.gov.uk/id/ukpga/1998/42",
  "doc_status": "revised",
  "title": "Human Rights Act 1998",
  "year": 1998,
  "number": 42,
  "number_of_provisions": 57,
  "xml_path": "data/raw/uk/xml/ukpga-1998-42.xml",
  "fetched_at": "2026-08-10T12:00:00Z",
  "status": "fetched"
}
```

A skipped stub gets `"status": "pdf_only"`, `"xml_path": null`, and a `"skip_reason"` field — never a row silently omitted from the manifest, since the manifest is the auditable record of what was attempted (mirrors the Israel pipeline's "log the reason" convention for skips).

---

## Code Patterns to Reuse (existing analogs in `pipeline/`)

| Concern | Analog | What to copy |
|---|---|---|
| `requests.Session` + retry loop | `pipeline/fetch_laws.py:80-109` (`paginate`) | The `try/except (requests.HTTPError, requests.ConnectionError, requests.Timeout)` retry shape, `REQUEST_TIMEOUT`/`MAX_RETRIES`/`RETRY_DELAY` module constants |
| Idempotent download-and-cache | `pipeline/fetch.py:94-120` (`download_pdf`) | Skip-if-`dest_path.exists()`, `dest_path.parent.mkdir(parents=True, exist_ok=True)`, remove partial file on failure |
| Manifest load/save | `pipeline/fetch.py:123-142` (`load_manifest`/`save_manifest`) | Dict keyed by id for in-memory dedup, `json.dump(..., ensure_ascii=False, indent=2)` on save — this is the same shape `pipeline/common/progress.py` already generalized for progress files, but the UK **manifest** (as opposed to progress) is new content, not a `common/` extraction target (ARCHITECTURE.md is explicit: only frontmatter/progress/deploy are country-blind; manifest schema is inherently country-specific) |
| Logging setup | Every `pipeline/*.py` `if __name__ == "__main__":` block | `logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")` |

**New code, no existing analog:** the `User-Agent` header requirement and the 5-second inter-request sleep are new to this pipeline (Israel's Knesset OData API has no such requirement) — implement as a session-level `session.headers.update({"User-Agent": ...})` plus `time.sleep(5)` between item fetches (not between retries of the same item — retries use a shorter backoff, matching `fetch_laws.py`'s existing `RETRY_DELAY = 2`).

---

## Dependency Check (STACK.md)

**Zero new hard dependencies.** `requests==2.33.1`, `lxml==6.1.0`, `tqdm==4.67.3` are already installed and in `pipeline/requirements.txt`. `tenacity` is installed in `~/.venv-codex` but absent from `requirements.txt` (a symptom of the same stale-`requirements.txt` defect already tracked in STATE.md Todos) — this phase does not need `tenacity`'s decorator-based retry (the existing hand-rolled `try/except` retry loop pattern from `fetch_laws.py` is sufficient and consistent with the rest of the codebase); no new entry required.

`requests-cache` (STACK.md: "recommended, optional") is deliberately **not** added — a 10-item batch with manual `dest_path.exists()` skip-on-rerun (the same idiom `fetch.py`/`download_pdf` already uses) gets the same practical caching benefit without a new pip dependency, consistent with CLAUDE.md's "do not over-abstract" and the project's demonstrated preference for minimal dependencies.

`pipeline/uk/` does not exist yet — this phase creates it for the first time (`pipeline/uk/__init__.py`, `pipeline/uk/fetch_uk.py`). No `pipeline/common/` import is needed in this phase (progress-file tracking across a 10-item one-shot batch is not warranted yet; `common.progress`'s `get_next_batch`/priority-queue machinery earns its keep once there's a resumable multi-hundred-item crawl, which is explicitly Tier B, out of scope here).

---

## Open Questions Deliberately Not Answered Here

Per ARCHITECTURE.md's "Open Questions" list, items 1 (page-splitting), 3 (`Commentary` rendering), and 5 (`/enacted` capture policy — resolved above as "never, this phase") belong to Phase 9 (conversion) or later. This phase's only job is acquisition + the two hard gates.
