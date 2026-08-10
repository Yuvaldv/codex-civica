# UK Pipeline — Human Guide

Acquisition stage for England-applicable UK legislation, sourced as CLML XML from
legislation.gov.uk. Conversion (CLML → Markdown), validation, and site integration are later
phases — not built yet.

```
legislation.gov.uk (CLML XML)
      │
      ▼
 pipeline/uk/fetch_uk.py   → cached XML + manifest_uk.json
```

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
