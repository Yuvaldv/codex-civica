# UK Pipeline — Human Guide

Acquisition + conversion for England-applicable UK legislation, sourced as CLML XML from
legislation.gov.uk. No LLM anywhere in this path — CLML is a single authoritative witness, not a
noisy one, so there is nothing to reconcile. Site integration is a later phase — not built yet.

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
 pipeline/uk/render.py     → IR -> Markdown + frontmatter
      │
      ▼
 pipeline/uk/validate.py   → round-trip + numbering checks (the phase-exit gate)
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
Two validators gate every conversion and fail the run (exit 1) on any error, never silently:

- **Round-trip losslessness** (`validate.check_round_trip`) — every source `<Text>` node's content,
  normalised for whitespace and the renderer's own bracket/footnote/anchor decoration, must appear
  somewhere in the rendered Markdown.
- **UK numbering** (`validate.check_numbering`) — alphanumeric/Roman provision numbers and duplicate-id
  detection. Deliberately NOT a port of Israel's dense-sequence gap validator: UK gaps (repealed
  sections, `19A`-style inserted numbers) are legitimate and never flagged.

**What's preserved, not just parsed:**
- Repealed/prospective provisions stay in the output, explicitly marked `**[REPEALED]**` /
  `**[NOT YET IN FORCE — prospective]**` — never silently dropped.
- Amendment markup (`Addition`/`Substitution`/`Repeal`) renders bracket-and-footnote style, citing
  the amending instrument via the source's own `Commentary` text.
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
