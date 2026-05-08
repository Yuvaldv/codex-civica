---
phase: 01-pipeline
plan: 03
type: execute
wave: 3
depends_on:
  - "01-PLAN-02-convert"
files_modified:
  - pipeline/validate.py
  - pipeline/README.md
autonomous: true
requirements:
  - PIPE-02
  - PIPE-03

must_haves:
  truths:
    - "Running `python pipeline/validate.py --laws laws/israel/ --report` checks all .md files and reports missing frontmatter fields and broken internal links"
    - "The script exits 0 when all files are clean and exits 1 when any errors are found"
    - "data/validation_report.json exists after a run with per-file results"
    - "pipeline/README.md documents the full automated pipeline workflow so a developer can run it without asking anyone"
    - "STDOUT summary is human-readable: lists each failing file with what is wrong"
  artifacts:
    - path: "pipeline/validate.py"
      provides: "Frontmatter completeness + internal link integrity checker"
      exports: ["validate_file", "main"]
    - path: "pipeline/README.md"
      provides: "Developer documentation for the full pipeline workflow"
      contains: "source ~/.venv-codex/bin/activate"
    - path: "data/validation_report.json"
      provides: "Machine-readable validation results (produced at runtime)"
      contains: "errors"
  key_links:
    - from: "pipeline/validate.py"
      to: "laws/israel/*.md"
      via: "python-frontmatter load — reads YAML frontmatter"
      pattern: "frontmatter.load"
    - from: "pipeline/validate.py"
      to: "data/validation_report.json"
      via: "json.dump after processing all files"
      pattern: "validation_report.json"
---

<objective>
Build pipeline/validate.py and pipeline/README.md — the third stage of the Codex Civica data pipeline and its documentation.

Purpose: validate.py enforces schema integrity across all converted laws (mandatory frontmatter fields present, internal Markdown links resolve). README.md documents the complete pipeline workflow so any developer can run it from scratch.

Output:
- pipeline/validate.py — runnable checker script; exits 0 (clean) or 1 (errors found)
- pipeline/README.md — pipeline documentation (venv setup, command sequence, data sources, output files)
- data/validation_report.json — produced at runtime
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
@/mnt/c/Dev/codex-civica/.planning/phases/01-pipeline/01-02-SUMMARY.md

<interfaces>
<!-- python-frontmatter API: -->
<!--   import frontmatter -->
<!--   post = frontmatter.load(str(path))  # parses YAML frontmatter -->
<!--   post.metadata  # dict of frontmatter fields -->
<!--   post.content   # string body after frontmatter -->

<!-- Mandatory frontmatter fields to check (from CLAUDE.md + REQUIREMENTS.md): -->
<!-- MANDATORY_FIELDS = ["title_he", "law_id", "category", "enacted", "status", "source_url"] -->
<!-- title is optional for Phase 1 (Hebrew-only per STATE.md decision) -->

<!-- Internal link pattern in Markdown: [text](./filename.md) -->
<!-- Internal links resolve to files in laws/israel/ -->
<!-- Link regex: r'\[([^\]]+)\]\((\./[^)]+\.md)\)' -->

<!-- validation_report.json schema: -->
<!-- {
  "summary": {
    "total_files": 14,
    "files_with_errors": 2,
    "total_errors": 5
  },
  "files": [
    {
      "file": "basic-law-human-dignity.md",
      "errors": [],
      "warnings": []
    },
    {
      "file": "some-law.md",
      "errors": [
        {"type": "missing_field", "field": "enacted"},
        {"type": "broken_link", "target": "./nonexistent-law.md"}
      ],
      "warnings": []
    }
  ]
} -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write pipeline/validate.py</name>
  <files>pipeline/validate.py</files>
  <read_first>
    - CLAUDE.md — mandatory frontmatter fields (title_he, law_id, category, enacted, status, source_url), allowed category values, law_id format
    - .planning/REQUIREMENTS.md — PIPE-02 exact success criteria: "frontmatter completeness and internal link integrity across all laws in laws/israel/"
    - pipeline/requirements.txt — confirm python-frontmatter is available
  </read_first>
  <action>
    Create `/mnt/c/Dev/codex-civica/pipeline/validate.py` implementing the following exactly:

    **Shebang and imports:**
    ```python
    #!/usr/bin/env python3
    """Validate frontmatter completeness and internal link integrity for laws/israel/ .md files."""

    import argparse
    import json
    import re
    import sys
    from pathlib import Path

    import frontmatter
    ```

    **Constants:**
    ```python
    MANDATORY_FIELDS = ["title_he", "law_id", "category", "enacted", "status", "source_url"]
    LINK_PATTERN = re.compile(r'\[([^\]]+)\]\((\./[^\)]+\.md)\)')
    VALID_STATUSES = {"active", "repealed", "suspended"}
    VALID_LAW_ID_PREFIX = "knesset-"
    ```

    **Function: `validate_file(md_path, laws_dir)` → dict**
    ```
    # Returns {"file": str, "errors": list[dict], "warnings": list[dict]}
    errors = []
    warnings = []
    file_name = md_path.name

    # Load frontmatter
    try:
        post = frontmatter.load(str(md_path))
    except Exception as e:
        return {
            "file": file_name,
            "errors": [{"type": "parse_error", "message": str(e)}],
            "warnings": []
        }

    meta = post.metadata

    # Check mandatory fields
    for field in MANDATORY_FIELDS:
        value = meta.get(field)
        if value is None or value == "" or value == []:
            errors.append({"type": "missing_field", "field": field})

    # Check law_id format: must start with "knesset-" or "il-"
    law_id = meta.get("law_id", "")
    if law_id and not (law_id.startswith("knesset-") or law_id.startswith("il-")):
        errors.append({"type": "invalid_law_id", "value": law_id, "message": "law_id must start with 'knesset-' or 'il-'"})

    # Check status is a known value
    status = meta.get("status", "")
    if status and status not in VALID_STATUSES:
        errors.append({"type": "invalid_status", "value": status, "message": f"status must be one of {VALID_STATUSES}"})

    # Check internal links resolve
    body = post.content or ""
    for match in LINK_PATTERN.finditer(body):
        link_text, link_target = match.group(1), match.group(2)
        # Strip leading "./"
        target_file = link_target.lstrip("./")
        target_path = laws_dir / target_file
        if not target_path.exists():
            errors.append({"type": "broken_link", "link_text": link_text, "target": link_target})

    return {"file": file_name, "errors": errors, "warnings": warnings}
    ```

    **Function: `check_links(laws_dir)` → list[dict]**
    This is a convenience wrapper used by main; validate_file handles individual files.
    Not needed as a separate exported function — validate_file already checks links internally.

    **Function: `main(laws_dir, report_path, report_flag)`**
    ```
    laws_dir = Path(laws_dir)
    if not laws_dir.exists():
        print(f"ERROR: laws directory not found: {laws_dir}", file=sys.stderr)
        sys.exit(2)

    md_files = sorted(f for f in laws_dir.glob("*.md") if f.name != "_index.md")
    if not md_files:
        print(f"No .md files found in {laws_dir}")
        sys.exit(0)

    results = []
    total_errors = 0
    files_with_errors = 0

    for md_path in md_files:
        result = validate_file(md_path, laws_dir)
        results.append(result)
        if result["errors"]:
            files_with_errors += 1
            total_errors += len(result["errors"])

    # STDOUT summary
    print(f"\nValidation Report — {len(md_files)} files checked")
    print(f"{'=' * 50}")
    for r in results:
        if r["errors"] or r["warnings"]:
            status_mark = "FAIL" if r["errors"] else "WARN"
            print(f"[{status_mark}] {r['file']}")
            for err in r["errors"]:
                if err["type"] == "missing_field":
                    print(f"       ERROR: missing mandatory field '{err['field']}'")
                elif err["type"] == "broken_link":
                    print(f"       ERROR: broken link '{err['target']}' (text: '{err['link_text']}')")
                elif err["type"] == "parse_error":
                    print(f"       ERROR: could not parse frontmatter: {err['message']}")
                else:
                    print(f"       ERROR: {err}")
            for warn in r["warnings"]:
                print(f"       WARN:  {warn}")
        else:
            print(f"[ OK ] {r['file']}")

    print(f"{'=' * 50}")
    print(f"Total: {len(md_files)} files, {files_with_errors} with errors, {total_errors} total errors")

    # Write report JSON
    if report_flag and report_path:
        report = {
            "summary": {
                "total_files": len(md_files),
                "files_with_errors": files_with_errors,
                "total_errors": total_errors,
            },
            "files": results,
        }
        report_out = Path(report_path)
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nReport written to {report_out}")

    sys.exit(1 if total_errors > 0 else 0)
    ```

    **CLI entrypoint:**
    ```python
    if __name__ == "__main__":
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument(
            "--laws", default="laws/israel",
            help="Path to laws directory (default: laws/israel)"
        )
        parser.add_argument(
            "--report", action="store_true",
            help="Write machine-readable report to data/validation_report.json"
        )
        parser.add_argument(
            "--report-path", default="data/validation_report.json",
            help="Path for validation report JSON (default: data/validation_report.json)"
        )
        args = parser.parse_args()
        main(args.laws, args.report_path, args.report)
    ```

    **Edge cases:**
    - `_index.md` excluded from validation (it's a placeholder, not a law file)
    - laws_dir does not exist → exit 2 with error message
    - laws_dir exists but has no .md files → print message, exit 0 (not an error)
    - File cannot be parsed by python-frontmatter → record parse_error, continue
    - Internal links with `../` or absolute paths are not checked (only `./filename.md` form)
  </action>
  <verify>
    <automated>cd /mnt/c/Dev/codex-civica && source ~/.venv-codex/bin/activate && python pipeline/validate.py --help</automated>
  </verify>
  <done>
    All of the following are true:
    - `python pipeline/validate.py --help` exits 0 and prints usage including `--laws` and `--report`
    - validate.py contains `def validate_file(`
    - validate.py contains `def main(`
    - validate.py contains `MANDATORY_FIELDS = [`
    - validate.py contains `frontmatter.load`
    - Running `python pipeline/validate.py --laws laws/israel/ --report` on the converted batch produces STDOUT summary and data/validation_report.json
    - validate.py exits 0 when no errors, 1 when errors found
  </done>
</task>

<task type="auto">
  <name>Task 2: Write pipeline/README.md</name>
  <files>pipeline/README.md</files>
  <read_first>
    - CLAUDE.md — venv path (~/.venv-codex), pipeline command sequence, data paths, OData endpoint, fs.knesset.gov.il, Knesset site WAF note
    - .planning/phases/01-pipeline/01-CONTEXT.md — locked decisions: fully automated from WSL2, no manual download needed, command sequence: fetch → convert → validate
    - .planning/REQUIREMENTS.md — PIPE-03 success criteria: "a developer can follow it step-by-step to download a law from the Knesset site and run the full pipeline without needing to ask anyone"
  </read_first>
  <action>
    Create `/mnt/c/Dev/codex-civica/pipeline/README.md` with the following exact content structure:

    ```markdown
    # Pipeline — Codex Civica

    The Codex Civica pipeline fetches all enacted Israeli laws from the Knesset OData API,
    downloads their PDFs, converts them to structured Markdown, and validates the output.

    **All steps run from WSL2. No manual browser download is required.**

    ---

    ## Prerequisites

    - Python 3.12+
    - `~/.venv-codex` Python virtual environment (Linux-side)
    - Internet access (Knesset OData API and fs.knesset.gov.il are accessible from WSL2)

    Install dependencies (first time only):

    \`\`\`bash
    source ~/.venv-codex/bin/activate
    pip install -r pipeline/requirements.txt
    \`\`\`

    ---

    ## Data Sources

    | Source | URL | Purpose |
    |--------|-----|---------|
    | Knesset OData API | `https://knesset.gov.il/Odata/ParliamentInfo.svc/` | Law metadata (name, date, type) |
    | Knesset File Server | `https://fs.knesset.gov.il/` | Official PDF publications (Reshumot) |

    **Note on WAF blocking:** The main Knesset website (`main.knesset.gov.il`) blocks WSL2 IP
    ranges via Reblaze WAF. The OData API and file server are not blocked — all pipeline steps
    work from WSL2 without a VPN.

    ---

    ## Pipeline Steps

    ### Step 1 — Fetch metadata and PDFs

    \`\`\`bash
    source ~/.venv-codex/bin/activate
    python pipeline/fetch.py
    \`\`\`

    - Queries `KNS_Bill` (OData) for all `StatusID eq 118` (in-effect laws) — approximately 7,699 laws
    - Downloads each law's official PDF from `fs.knesset.gov.il` to `data/raw/israel/{bill_id}.pdf`
    - Writes `data/raw/israel/manifest.json` with per-law metadata (crash-safe: saves after every 100 laws)
    - Re-running is safe — already-downloaded PDFs are skipped

    **Test with a small batch:**

    \`\`\`bash
    python pipeline/fetch.py --limit 10
    \`\`\`

    **Output:**
    - `data/raw/israel/manifest.json` — metadata index
    - `data/raw/israel/{bill_id}.pdf` — one PDF per law

    ---

    ### Step 2 — Convert PDFs to Markdown

    \`\`\`bash
    python pipeline/convert.py
    \`\`\`

    - Reads `data/raw/israel/manifest.json`
    - Extracts Hebrew text from each PDF using `pymupdf` (correct RTL word order)
    - Generates a lowercase-hyphenated slug from the Hebrew law name
    - Writes `laws/israel/{slug}.md` with complete YAML frontmatter and law body
    - Re-running is safe — already-converted files are skipped

    **Custom paths:**

    \`\`\`bash
    python pipeline/convert.py --input data/raw/israel/manifest.json --output laws/israel/
    \`\`\`

    **Output:** `laws/israel/{slug}.md` — one Markdown file per law

    ---

    ### Step 3 — Validate output

    \`\`\`bash
    python pipeline/validate.py --laws laws/israel/ --report
    \`\`\`

    - Checks all `.md` files in `laws/israel/` for:
      - Mandatory frontmatter fields: `title_he`, `law_id`, `category`, `enacted`, `status`, `source_url`
      - Internal Markdown link integrity (`[text](./filename.md)` links resolve to real files)
    - Prints a human-readable summary to STDOUT
    - Writes machine-readable results to `data/validation_report.json`
    - Exit code `0` = all files clean; exit code `1` = errors found

    **Output:**
    - `data/validation_report.json` — per-file results with error details

    ---

    ## Full Pipeline (one command sequence)

    \`\`\`bash
    source ~/.venv-codex/bin/activate
    python pipeline/fetch.py
    python pipeline/convert.py
    python pipeline/validate.py --laws laws/israel/ --report
    \`\`\`

    ---

    ## Output Files

    | File | Description | Committed? |
    |------|-------------|------------|
    | `data/raw/israel/manifest.json` | Law metadata index | No |
    | `data/raw/israel/{bill_id}.pdf` | Raw PDFs from Knesset | No |
    | `laws/israel/{slug}.md` | Converted Markdown laws | Yes |
    | `data/validation_report.json` | Validation results | No |

    ---

    ## Law File Schema

    Each `.md` file uses the frontmatter schema defined in `CLAUDE.md`.
    Mandatory fields: `title_he`, `law_id`, `category`, `enacted`, `status`, `source_url`.

    Law ID format: `knesset-{BillID}` (e.g. `knesset-147449`).

    Category is detected from the Hebrew law name:
    - Laws starting with `חוק-יסוד` → `basic-laws`
    - All others → `civil-law` (Phase 1 default; improved in later phases)

    ---

    ## Troubleshooting

    | Problem | Cause | Fix |
    |---------|-------|-----|
    | `ModuleNotFoundError: fitz` | pymupdf not installed | `pip install pymupdf` |
    | `FileNotFoundError: manifest.json` | fetch.py not run yet | Run `python pipeline/fetch.py` first |
    | HTTP 247 from knesset.gov.il | Reblaze WAF blocking request | Only affects main site; OData API is not blocked |
    | Hebrew text appears reversed | Wrong PDF library | Ensure `fitz` (pymupdf) is used, not `pdfplumber` |
    | validate.py exits 1 | Errors found in .md files | Check STDOUT for list of failing files and missing fields |
    ```

    The README must:
    - Use `source ~/.venv-codex/bin/activate` (not `source .venv/bin/activate` — per CONTEXT.md venv decision)
    - Document OData endpoint: `https://knesset.gov.il/Odata/ParliamentInfo.svc/`
    - Document file server: `https://fs.knesset.gov.il/`
    - Document command sequence: fetch.py → convert.py → validate.py
    - Explain `--limit` flag on fetch.py for testing
    - Note WSL2 accessibility (no Reblaze on OData/file server)
    - Reference `CLAUDE.md` for frontmatter schema
    - Not include any manual browser download step (per CONTEXT.md decision: fully automated)
  </action>
  <verify>
    <automated>grep -c "source ~/.venv-codex/bin/activate" /mnt/c/Dev/codex-civica/pipeline/README.md</automated>
  </verify>
  <done>
    All of the following are true:
    - pipeline/README.md exists
    - README.md contains `source ~/.venv-codex/bin/activate`
    - README.md contains `fs.knesset.gov.il`
    - README.md contains `python pipeline/fetch.py`
    - README.md contains `python pipeline/convert.py`
    - README.md contains `python pipeline/validate.py`
    - README.md contains `manifest.json`
    - README.md contains `validation_report.json`
    - README.md contains `--limit`
    - README.md does NOT contain "Windows browser" or "manual download" (pipeline is automated)
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| laws/israel/*.md → frontmatter.load() | Markdown files from disk (produced by convert.py from external PDF source) |
| validate.py → data/validation_report.json | JSON write to local disk |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-01 | Tampering | validate.py reads laws/israel/*.md from disk | accept | Files are project-local outputs; not user-supplied at runtime; parsing errors caught and reported |
| T-03-02 | Information Disclosure | validation_report.json contains law file names and field values | accept | Public data only; report is gitignored; no secrets in law files |
| T-03-03 | Denial of Service | Malformed YAML frontmatter causes frontmatter.load crash | mitigate | Wrapped in try/except; parse_error recorded for that file; validation continues for remaining files |
| T-03-04 | Elevation of Privilege | Path traversal via --laws CLI argument | mitigate | `Path(laws_dir)` is used directly; glob is confined to that directory; no shell expansion; user runs locally, not as a web service |
| T-03-05 | Repudiation | validate.py exits 0 when it should exit 1 | mitigate | `sys.exit(1 if total_errors > 0 else 0)` — exit code is computed from actual error count, not a flag; covered by acceptance criteria |
</threat_model>

<verification>
Full validation check (run after both tasks):

```bash
cd /mnt/c/Dev/codex-civica
source ~/.venv-codex/bin/activate

# 1. validate.py --help
python pipeline/validate.py --help

# 2. Run validation on converted batch
python pipeline/validate.py --laws laws/israel/ --report
echo "Exit code: $?"

# 3. Verify report file was created
python -c "
import json
from pathlib import Path
report = json.loads(Path('data/validation_report.json').read_text())
print('summary:', report['summary'])
print('files checked:', len(report['files']))
assert 'total_files' in report['summary']
assert 'files_with_errors' in report['summary']
assert 'total_errors' in report['summary']
print('validation_report.json OK')
"

# 4. README checks
grep -c "source ~/.venv-codex/bin/activate" pipeline/README.md
grep -c "fs.knesset.gov.il" pipeline/README.md
grep -c "manifest.json" pipeline/README.md
grep -c "validation_report.json" pipeline/README.md

# 5. End-to-end pipeline smoke test (assumes fetch.py --limit 3 was run)
echo "=== End-to-end check ==="
echo "fetch.py:    $(python pipeline/fetch.py --help 2>&1 | head -1)"
echo "convert.py:  $(python pipeline/convert.py --help 2>&1 | head -1)"
echo "validate.py: $(python pipeline/validate.py --help 2>&1 | head -1)"
```
</verification>

<success_criteria>
- pipeline/validate.py exists and `python pipeline/validate.py --help` exits 0
- pipeline/README.md exists and documents the full pipeline workflow with correct venv path (~/.venv-codex)
- Running `python pipeline/validate.py --laws laws/israel/ --report` produces data/validation_report.json with summary.total_files, summary.files_with_errors, summary.total_errors keys
- STDOUT shows [OK] or [FAIL] per file with specific error messages for failures
- Exit code 0 for clean batch; exit code 1 when any errors found
- README.md references all three commands (fetch.py, convert.py, validate.py) in correct order
- README.md references source ~/.venv-codex/bin/activate (not .venv/)
</success_criteria>

<output>
After completion, create `/mnt/c/Dev/codex-civica/.planning/phases/01-pipeline/01-03-SUMMARY.md`
</output>
