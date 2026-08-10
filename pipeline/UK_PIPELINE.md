# UK Pipeline — Human Guide

Acquisition + conversion for England-applicable UK legislation, sourced as CLML XML from
legislation.gov.uk. No LLM anywhere in this path — CLML is a single authoritative witness, not a
noisy one, so there is nothing to reconcile. Site integration (Phases 10/11) is live at
`/laws/england` on the Docusaurus site; see `site/src/countryConfig.js`.

```
legislation.gov.uk (CLML XML)
      │
      ▼
 pipeline/uk/fetch_uk.py   → cached XML + manifest_uk.json
      │
      ▼
 pipeline/uk/clml.py       → XML -> IR (pipeline/uk/ir.py)
      │
      ▼
 pipeline/uk/render.py     → IR -> Markdown + frontmatter (batch-aware: citations to
      │                        other docs in the same run resolve as internal links)
      ▼
 pipeline/uk/validate.py   → round-trip + numbering + cross-reference checks (the phase-exit gate)
      │
      ▼
 laws/uk/england/<slug>.md
```

## Converting

```bash
~/.venv-codex/bin/python pipeline/uk/convert.py             # every fetched manifest entry
~/.venv-codex/bin/python pipeline/uk/convert.py --slug ukpga-1998-42
```

Deterministic tree walk, byte-for-byte reproducible from the cached XML — safe to re-run any time.
Three validators gate every conversion and fail the run (exit 1) on any error, never silently:

- **Round-trip losslessness** (`validate.check_round_trip`) — every source `<Text>` node's content,
  normalised for whitespace and the renderer's own bracket/footnote/anchor decoration, must appear
  somewhere in the rendered Markdown.
- **UK numbering** (`validate.check_numbering`) — alphanumeric/Roman provision numbers and duplicate-id
  detection. Deliberately NOT a port of Israel's dense-sequence gap validator: UK gaps (repealed
  sections, `19A`-style inserted numbers) are legitimate and never flagged.
- **Cross-reference resolution** (`validate.check_cross_references`, batch-level — runs once after
  every doc in the run has been converted, not per-doc) — every internal link `render.py` produced
  must resolve: the target slug must actually have been rendered, and any anchor must exist on that
  page. Reads `render()`'s own structured `internal_links` return value rather than re-parsing the
  rendered Markdown — see "Cross-reference and amendment linking" below for why.

**What's preserved, not just parsed:**
- Repealed/prospective provisions stay in the output, explicitly marked `**[REPEALED]**` /
  `**[NOT YET IN FORCE — prospective]**` — never silently dropped.
- Amendment markup (`Addition`/`Substitution`/`Repeal`) renders bracket-and-footnote style, citing
  the amending instrument via the source's own `Commentary` text — now with working links (see below).
- `BlockAmendment`/`BlockText` (quoted text from another Act) renders as a marked blockquote, excluded
  from this document's own numbering.
- Per-provision territorial extent (`RestrictExtent`) is annotated wherever it differs from the
  document-level extent.
- Schedules keep their `Reference` back-link to the enabling section, and get their own short-form
  anchor namespace (`schedule-1-paragraph-2`, not the section-length full id).
- Every `ukm:UnappliedEffect` becomes a visible banner with a count — never silently incorporated as
  if it were already-applied current law.
- A defined-term index (`<Term>` elements) and any `Commentary` not already cited inline both surface
  at the bottom of the file, so round-trip losslessness holds even for editorial notes with no inline
  amendment marker.

## Cross-reference and amendment linking (UKLINK-01/02/03)

Every `Citation`/`CitationSubRef`/`ExternalLink` — in body text *and* in `Commentary`/footnote text —
resolves through `render._resolve_link`: if the target is another document converted in the *same*
`convert.py` run, it becomes a relative link (`./slug.md#anchor`, or `#anchor` for a self-citation);
otherwise it's an explicit `https://www.legislation.gov.uk/...` link. Nothing is ever silently dropped.

- **UKLINK-02** (amendments affecting a document): the end-of-document footnote block now prefixes
  each entry with a link back to the provision(s) it affects (`[section-1-1-a](#section-1-1-a): ...`),
  collected as `_footnote_marker` fires during the render.
- **UKLINK-03** (an amending Act linking to what it amends): no separate code path — any `Citation` in
  an amending Act's own body text that targets a batch-mate resolves in-batch through the same
  `_resolve_link` used everywhere else.
- **Self-citation anchor safety**: legislation.gov.uk's own `SectionRef` can name a *compound* citation
  (`S. 8(2)(6)(b)` → one ref spanning three sibling subsections) or a virtual location (`introduction`)
  that has no single matching provision in the parsed tree. For a self-citation, `render.py` checks the
  anchor against the document's own known ids (`RenderContext.known_anchors`, cheap — computed from the
  same doc) and degrades to a plain link rather than a fragment already known to be wrong. **This check
  does not extend to cross-document anchors** — render.py is a pure per-document function with no
  visibility into another doc's provision tree at render time — so a compound/virtual `SectionRef`
  pointing at *another* batch doc still emits the (unverified) anchor and relies on
  `check_cross_references` to catch it after the full batch has been rendered. None of the current
  10-Act batch triggers this (verified: zero in-batch citations exist at all in the live data — see
  STATE.md), so it's untested against real content; `pipeline/uk/tests/test_link_resolution.py` proves
  the mechanism synthetically.

## Testing

```bash
~/.venv-codex/bin/python pipeline/uk/tests/test_link_resolution.py
```

Stdlib-only (no pytest, matching `pipeline/tests/test_country_blind.py`'s precedent). Exercises
`render.py`'s in-batch/external/self-citation resolution and `validate.check_cross_references`
directly against hand-built `ir.py` objects — necessary because the live 10-Act batch has zero real
in-batch citations to exercise this path against.

## Running

```bash
~/.venv-codex/bin/python pipeline/uk/fetch_uk.py
```

No arguments — the batch is a hardcoded list of 10 Tier A Acts (see `BATCH` in the script).
Deliberately unparameterised: growing the batch past 10 Acts needs an explicit go-ahead per the
project's roadmap constraint (2026-08-09).

**Outputs:**
- `data/raw/uk/xml/<type>-<year>-<number>.xml` — raw CLML per Act
- `data/raw/uk/manifest_uk.json` — one row per item, including any rejected by a gate

## The two hard gates

1. **Stub rejection** — a document with `NumberOfProvisions="0"` or no `<Body>`/`<Schedules>` is a
   PDF-only historic Act with no real CLML content. Rejected before any file is written; recorded
   in the manifest as `status: "pdf_only"`.
2. **Version gate** — only `<ukm:DocumentStatus Value="revised">` is accepted. `/enacted/data.xml`
   is never requested. A non-revised or unlabelled document is rejected as `status: "wrong_version"`.

## Key constraints

- **Fair use**: mandatory identifying `User-Agent` (`CodexCivica (https://github.com/Yuvaldv/codex-civica)`),
  5-second delay between requests, sequential only — no concurrency.
- **Interpreter**: always `~/.venv-codex/bin/python`.
- **Slugs** are derived from the fetched item's own `ukm:Year`/`ukm:Number` metadata, never from
  the request URI — this is what keeps pre-1963 regnal-year URIs (e.g. `ukpga/Geo6/12-13-14/103`)
  from leaking into filenames.
