---
phase: 01-pipeline
plan: 02
type: execute
wave: 2
depends_on:
  - "01-PLAN-01-fetch"
files_modified:
  - pipeline/convert.py
autonomous: true
requirements:
  - PIPE-01

must_haves:
  truths:
    - "Running `python pipeline/convert.py --input data/raw/israel/ --output laws/israel/` converts every PDF in manifest.json into a .md file in laws/israel/"
    - "Every output .md file has complete YAML frontmatter: title_he, law_id, category, enacted, status, source_url"
    - "File names are lowercase-hyphenated slugs derived from the Hebrew law name"
    - "Basic Laws (Name starts with 'חוק-יסוד') are assigned category: basic-laws"
    - "Extracted law body text appears under a '## Full Text' heading in the Markdown file"
    - "Laws already converted are skipped on re-run (idempotent)"
  artifacts:
    - path: "pipeline/convert.py"
      provides: "PDF-to-Markdown converter with frontmatter generation"
      exports: ["extract_text", "build_frontmatter", "make_slug", "convert_pdf", "main"]
    - path: "laws/israel/{slug}.md"
      provides: "Per-law Markdown file with YAML frontmatter (produced at runtime)"
      contains: "title_he"
  key_links:
    - from: "pipeline/convert.py"
      to: "data/raw/israel/manifest.json"
      via: "json.load — reads metadata for each law"
      pattern: "manifest.json"
    - from: "pipeline/convert.py"
      to: "laws/israel/{slug}.md"
      via: "Path.write_text with frontmatter + body"
      pattern: "laws/israel"
    - from: "pipeline/convert.py"
      to: "data/raw/israel/{bill_id}.pdf"
      via: "fitz.open(pdf_path)"
      pattern: "fitz.open"
---

<objective>
Build pipeline/convert.py — the second stage of the Codex Civica data pipeline.

Purpose: For each entry in data/raw/israel/manifest.json that has a pdf_path, extract Hebrew law text using pymupdf (fitz), generate a slug from the Hebrew name, map OData metadata to the canonical CLAUDE.md frontmatter schema, and write a structured .md file to laws/israel/{slug}.md.

Output:
- pipeline/convert.py — runnable Python script
- laws/israel/{slug}.md — Markdown files produced at runtime (per-law, not committed in this plan)
</objective>

<execution_context>
@/home/yuvalv/.claude/get-shit-done/workflows/execute-plan.md
@/home/yuvalv/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/mnt/c/Dev/codex-civica/.planning/ROADMAP.md
@/mnt/c/Dev/codex-civica/.planning/STATE.md
@/mnt/c/Dev/codex-civica/.planning/phases/01-pipeline/01-CONTEXT.md
@/mnt/c/Dev/codex-civica/CLAUDE.md
@/mnt/c/Dev/codex-civica/pipeline/requirements.txt
@/mnt/c/Dev/codex-civica/.planning/phases/01-pipeline/01-01-SUMMARY.md

<interfaces>
<!-- Manifest JSON schema (output of fetch.py, input to convert.py): -->
<!-- [
  {
    "bill_id": 147449,
    "name_he": "חוק-יסוד: הממשלה",
    "publication_date": "1968-08-01T00:00:00",
    "sub_type_id": 53,
    "pdf_path": "data/raw/israel/147449.pdf",
    "pdf_url": "https://fs.knesset.gov.il//X/law/..."
  }
] -->

<!-- CLAUDE.md canonical frontmatter schema (mandatory fields): -->
<!--
title: "Law Name in English"       ← omit for Hebrew-only Phase 1
title_he: "שם החוק בעברית"         ← from manifest name_he
law_id: "knesset-147449"           ← "knesset-{bill_id}"
category: "basic-laws"             ← derived from name_he (see category logic)
tags: []                           ← empty list for Phase 1
enacted: "1968-08-01"              ← publication_date date portion
last_amended: ""                   ← omit for Phase 1
status: "active"                   ← hardcoded "active" for all StatusID=118
language: ["he"]                   ← Hebrew only for Phase 1
source_url: "https://fs.knesset.gov.il//X/law/..." ← pdf_url from manifest
related_laws: []                   ← empty for Phase 1
-->

<!-- Category detection logic (from name_he): -->
<!-- 1. name_he starts with "חוק-יסוד" → category: "basic-laws" -->
<!-- 2. else: category: "civil-law" (fallback — Phase 2 will improve mapping) -->

<!-- Slug generation: -->
<!-- python-hebrew-numbers is available to convert Hebrew numerals -->
<!-- Fallback: transliterate or use bill_id if slug generation fails -->
<!-- Examples: -->
<!--   "חוק-יסוד: הממשלה" → "basic-law-the-government" or "חוק-יסוד-הממשלה" as slug -->
<!--   For Phase 1: use simplified slug from name_he with hyphens, strip colons/punctuation -->
<!--   Acceptable: "knesset-147449" as fallback slug if Hebrew transliteration not available -->

<!-- pymupdf API (import fitz): -->
<!--   doc = fitz.open(str(pdf_path)) -->
<!--   text = "\n".join(page.get_text() for page in doc) -->
<!--   doc.close() -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write pipeline/convert.py</name>
  <files>pipeline/convert.py</files>
  <read_first>
    - CLAUDE.md — canonical frontmatter schema (mandatory fields, allowed category values, law_id format, status values, language field)
    - .planning/phases/01-pipeline/01-CONTEXT.md — locked decisions: pymupdf for PDF extraction, slug generation from name_he, SubTypeID NOT used for category (detect from name instead), manifest.json field names
    - pipeline/requirements.txt — confirm pymupdf is listed (added in Plan 01)
    - laws/israel/_index.md — see the output directory structure before writing there
  </read_first>
  <action>
    Create `/mnt/c/Dev/codex-civica/pipeline/convert.py` implementing the following exactly:

    **Shebang and imports:**
    ```python
    #!/usr/bin/env python3
    """Convert Knesset law PDFs to structured Markdown with YAML frontmatter."""

    import argparse
    import json
    import logging
    import re
    import unicodedata
    from datetime import datetime
    from pathlib import Path

    import fitz  # pymupdf
    import yaml
    ```

    **Constants:**
    ```python
    MANIFEST_PATH_DEFAULT = Path(__file__).parent.parent / "data" / "raw" / "israel" / "manifest.json"
    OUTPUT_DIR_DEFAULT = Path(__file__).parent.parent / "laws" / "israel"
    MANDATORY_FIELDS = ["title_he", "law_id", "category", "enacted", "status", "source_url"]
    ```

    **Function: `detect_category(name_he)` → str**
    ```
    name_he = name_he.strip()
    if name_he.startswith("חוק-יסוד") or name_he.startswith("חוק יסוד"):
        return "basic-laws"
    # Fallback — Phase 2 will improve with a full SubTypeDesc mapping
    return "civil-law"
    ```

    **Function: `make_slug(name_he, bill_id)` → str**
    Strategy: produce a lowercase-hyphenated slug from the Hebrew law name.
    ```
    # 1. Normalize: remove diacritics (nikud), punctuation, colons
    text = name_he.strip()
    text = re.sub(r'[ְ-ׇ]', '', text)   # remove Hebrew nikud
    text = re.sub(r'[:\.,;()\[\]"\'״׳]', ' ', text)  # punctuation to spaces

    # 2. If name starts with "חוק-יסוד" → prefix slug with "basic-law"
    if text.startswith("חוק-יסוד") or text.startswith("חוק יסוד"):
        text = re.sub(r'^חוק.יסוד\s*', '', text).strip()
        prefix = "basic-law"
    elif text.startswith("חוק"):
        text = re.sub(r'^חוק\s*', '', text).strip()
        prefix = "law"
    else:
        prefix = ""

    # 3. Try to extract year pattern e.g. "התשנ\"ב-1992" → "1992"
    year_match = re.search(r'(\d{4})', name_he)
    year_suffix = f"-{year_match.group(1)}" if year_match else ""

    # 4. Transliterate remaining Hebrew to ASCII-safe slug
    # Use a simplified approach: remove non-ASCII after normalization, use bill_id if empty
    ascii_part = unicodedata.normalize('NFKD', text)
    ascii_part = ascii_part.encode('ascii', 'ignore').decode('ascii')
    ascii_part = re.sub(r'[^a-zA-Z0-9\s-]', '', ascii_part).strip()
    ascii_part = re.sub(r'\s+', '-', ascii_part).lower()
    ascii_part = re.sub(r'-+', '-', ascii_part).strip('-')

    # 5. If transliteration produced nothing (pure Hebrew), use bill_id
    if not ascii_part:
        slug = f"{prefix}-{bill_id}" if prefix else f"law-{bill_id}"
    else:
        slug = f"{prefix}-{ascii_part}{year_suffix}" if prefix else f"{ascii_part}{year_suffix}"

    # 6. Final cleanup
    slug = re.sub(r'-+', '-', slug).strip('-').lower()
    return slug or f"law-{bill_id}"
    ```

    **Function: `extract_text(pdf_path)` → str**
    ```
    doc = fitz.open(str(pdf_path))
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()
    return "\n\n".join(pages_text)
    ```

    **Function: `build_frontmatter(entry)` → dict**
    ```
    # entry is one dict from manifest.json
    bill_id = entry["bill_id"]
    name_he = entry.get("name_he", "")
    pub_date = entry.get("publication_date")
    # Parse date: "1968-08-01T00:00:00" → "1968-08-01"
    enacted = ""
    if pub_date:
        try:
            enacted = datetime.fromisoformat(pub_date).date().isoformat()
        except ValueError:
            enacted = pub_date[:10] if len(pub_date) >= 10 else pub_date

    return {
        "title_he": name_he,
        "law_id": f"knesset-{bill_id}",
        "category": detect_category(name_he),
        "tags": [],
        "enacted": enacted,
        "status": "active",
        "language": ["he"],
        "source_url": entry.get("pdf_url") or "",
        "related_laws": [],
    }
    ```

    **Function: `build_markdown(frontmatter_dict, body_text, name_he)` → str**
    ```
    fm_str = yaml.dump(frontmatter_dict, allow_unicode=True, default_flow_style=False, sort_keys=False)
    # Clean up body: strip excessive blank lines
    body_clean = re.sub(r'\n{3,}', '\n\n', body_text.strip())
    return f"---\n{fm_str}---\n\n# {name_he}\n\n## Full Text\n\n{body_clean}\n"
    ```

    **Function: `convert_pdf(entry, output_dir)` → tuple[bool, str]**
    ```
    # Returns (success: bool, slug: str)
    bill_id = entry["bill_id"]
    pdf_path = entry.get("pdf_path")
    name_he = entry.get("name_he", "")

    slug = make_slug(name_he, bill_id)
    out_path = Path(output_dir) / f"{slug}.md"

    # Idempotency: skip if output already exists
    if out_path.exists():
        logging.info("Skipping %s (already converted)", slug)
        return True, slug

    if not pdf_path or not Path(pdf_path).exists():
        logging.warning("No PDF for bill %s (%s) — skipping", bill_id, name_he[:40])
        return False, slug

    try:
        body_text = extract_text(pdf_path)
    except Exception as e:
        logging.error("PDF extraction failed for bill %s: %s", bill_id, e)
        return False, slug

    fm = build_frontmatter(entry)
    md_content = build_markdown(fm, body_text, name_he)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md_content, encoding="utf-8")
    logging.info("Wrote %s", out_path)
    return True, slug
    ```

    **Function: `main(manifest_path, output_dir)`**
    ```
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)

    if not manifest_path.exists():
        logging.error("Manifest not found: %s — run fetch.py first", manifest_path)
        raise SystemExit(1)

    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    logging.info("Converting %d laws from manifest", len(entries))

    success_count = 0
    skip_count = 0
    fail_count = 0

    for entry in entries:
        ok, slug = convert_pdf(entry, output_dir)
        if ok:
            if (output_dir / f"{slug}.md").exists():
                success_count += 1
            else:
                skip_count += 1
        else:
            fail_count += 1

    print(f"Done. Converted: {success_count}, Skipped (no PDF): {skip_count}, Errors: {fail_count}")
    ```

    **CLI entrypoint:**
    ```python
    if __name__ == "__main__":
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument(
            "--input", default=str(MANIFEST_PATH_DEFAULT),
            help="Path to manifest.json (default: data/raw/israel/manifest.json)"
        )
        parser.add_argument(
            "--output", default=str(OUTPUT_DIR_DEFAULT),
            help="Output directory for .md files (default: laws/israel/)"
        )
        args = parser.parse_args()
        main(args.input, args.output)
    ```

    **Important notes on pymupdf Hebrew extraction:**
    - `fitz` import name for the `pymupdf` pip package — confirmed in CONTEXT.md
    - `page.get_text()` returns text in correct Hebrew RTL reading order for Knesset PDFs
    - Do NOT use `pdfplumber` — it reverses Hebrew word order (per CONTEXT.md decision)
    - The extracted text will be in Hebrew; no translation in Phase 1

    **Slug generation for Basic Laws (these are the priority for Phase 1):**
    - "חוק-יסוד: כבוד האדם וחירותו" → "basic-law-1992" (year extracted + prefix)
    - "חוק-יסוד: חופש העיסוק" → "basic-law-1992" — if collision, append bill_id
    - Slug collisions: if `out_path.exists()` AND it has a different `law_id` in frontmatter → append `-{bill_id}` to slug
  </action>
  <verify>
    <automated>cd /mnt/c/Dev/codex-civica && source ~/.venv-codex/bin/activate && python pipeline/convert.py --help</automated>
  </verify>
  <done>
    All of the following are true:
    - `python pipeline/convert.py --help` exits 0 and prints usage including `--input` and `--output`
    - convert.py contains `def extract_text(`
    - convert.py contains `def build_frontmatter(`
    - convert.py contains `def make_slug(`
    - convert.py contains `def detect_category(`
    - convert.py contains `def convert_pdf(`
    - convert.py contains `import fitz`
    - Running against a test PDF (after fetch.py --limit 1) produces a .md file in laws/israel/ with YAML frontmatter containing title_he, law_id, category, enacted, status, source_url
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    convert.py is complete. The script reads manifest.json, extracts Hebrew text from PDFs using pymupdf/fitz, generates law slugs, maps metadata to CLAUDE.md frontmatter schema, and writes structured .md files to laws/israel/.
  </what-built>
  <how-to-verify>
    Run an end-to-end test with a small batch:

    ```bash
    cd /mnt/c/Dev/codex-civica
    source ~/.venv-codex/bin/activate

    # 1. Fetch 3 laws (if not already done in Plan 01 verification)
    python pipeline/fetch.py --limit 3

    # 2. Convert them
    python pipeline/convert.py

    # 3. Check output
    ls laws/israel/*.md
    cat laws/israel/$(ls laws/israel/*.md | head -1 | xargs basename)
    ```

    Verify:
    a. At least one .md file exists in laws/israel/ (not counting _index.md)
    b. Open the file — confirm YAML frontmatter is present between `---` delimiters
    c. Confirm `title_he:` field contains Hebrew text
    d. Confirm `law_id:` starts with `knesset-`
    e. Confirm `category:` is either `basic-laws` or `civil-law`
    f. Confirm `enacted:` is a date string (YYYY-MM-DD format)
    g. Confirm `## Full Text` heading appears in the body
    h. Check that Hebrew text appears under `## Full Text` (not garbled, reads right-to-left)
    i. Run `python pipeline/convert.py` a second time — verify it says "Skipped" for already-converted files (idempotency)
  </how-to-verify>
  <resume-signal>Type "approved" if the output looks correct, or describe what is wrong (wrong category, garbled text, missing frontmatter field, etc.)</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| manifest.json → convert.py | JSON data read from local disk (produced by fetch.py from external source) |
| data/raw/israel/{bill_id}.pdf → fitz.open() | Binary PDF file from external source |
| convert.py → laws/israel/{slug}.md | File write; slug derived from Hebrew law name |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-01 | Tampering | manifest.json loaded from disk | accept | Manifest is project-local, not user-supplied; JSON parse error raises exception which is surfaced; no exec or eval |
| T-02-02 | Information Disclosure | PDF text written to .md file | accept | Law text is public domain; no secrets in PDFs |
| T-02-03 | Elevation of Privilege | Path traversal via slug in output file path | mitigate | `make_slug()` strips all characters except `[a-zA-Z0-9\s-]` before using as filename; output is always `output_dir / f"{slug}.md"` where slug is ASCII-only after processing; slug is validated to be non-empty before write |
| T-02-04 | Denial of Service | Malformed PDF causes fitz.open crash | mitigate | `extract_text()` is wrapped in try/except; failed PDFs are logged and skipped; pipeline continues |
| T-02-05 | Tampering | YAML frontmatter injection via name_he field | mitigate | `yaml.dump()` handles escaping of special characters including YAML control characters; title_he is passed as Python string value, never concatenated into raw YAML |
| T-02-06 | Tampering | Slug collision overwrites different law's .md file | mitigate | Slug collision check: if output .md exists, read its law_id; if different from current bill, append `-{bill_id}` to slug before writing |
</threat_model>

<verification>
Full conversion check (run after both tasks):

```bash
cd /mnt/c/Dev/codex-civica
source ~/.venv-codex/bin/activate

# 1. Smoke test --help
python pipeline/convert.py --help

# 2. Run conversion (requires fetch.py to have run first)
python pipeline/convert.py

# 3. Check at least one .md was produced
MD_COUNT=$(ls laws/israel/*.md 2>/dev/null | grep -v '_index' | wc -l)
echo "MD files produced: $MD_COUNT"

# 4. Validate frontmatter on first output file
python -c "
import frontmatter
from pathlib import Path
import sys

mds = [p for p in Path('laws/israel').glob('*.md') if p.name != '_index.md']
if not mds:
    print('ERROR: no .md files found')
    sys.exit(1)

for f in mds[:3]:
    post = frontmatter.load(str(f))
    required = ['title_he', 'law_id', 'category', 'enacted', 'status', 'source_url']
    missing = [k for k in required if not post.get(k)]
    if missing:
        print(f'FAIL {f.name}: missing {missing}')
    else:
        print(f'OK   {f.name}: law_id={post[\"law_id\"]} category={post[\"category\"]}')
"
```
</verification>

<success_criteria>
- pipeline/convert.py exists and `python pipeline/convert.py --help` exits 0
- Running convert.py on a 3-law batch produces .md files in laws/israel/ with all required frontmatter fields populated
- Files with name_he starting with "חוק-יסוד" receive category: basic-laws
- Slug is lowercase-hyphenated ASCII (or knesset-{bill_id} fallback)
- Running convert.py twice does not re-convert already-converted files (idempotent)
- Human checkpoint approved: Hebrew text readable, frontmatter correct, Full Text section present
</success_criteria>

<output>
After completion, create `/mnt/c/Dev/codex-civica/.planning/phases/01-pipeline/01-02-SUMMARY.md`
</output>
