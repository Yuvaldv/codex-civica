# Phase 7: Shared Pipeline Core - Pattern Map

**Mapped:** 2026-08-09
**Files analyzed:** 11 (7 create, 4 modify)
**Analogs found:** 11 / 11 (10 exact — this is an extraction refactor, so the "analog" is usually the current in-place source being moved)

**Special property of this phase:** Phase 7 is a *pure extraction refactor*. For 8 of the 11 files, the closest analog is not a stylistically-similar sibling but **the literal current implementation being moved**. Those excerpts below are verbatim current source (copied from the working tree at `HEAD`, line numbers verified) — the executor must reproduce them character-for-character in the new location, because every phase gate is a byte-identity check.

**Rule for the executor:** where an excerpt is marked `VERBATIM — DO NOT REFORMAT`, do not change quote style, whitespace, blank-line count, argument order, or comment text. Reformatting is a silent gate failure risk (`build_frontmatter`) or a real regression (`save_progress` trailing-newline behaviour).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pipeline/common/__init__.py` (new) | package marker | n/a | **none in repo** — zero `__init__.py` files exist anywhere | no analog |
| `pipeline/common/frontmatter.py` (new) | utility (pure text) | transform | `pipeline/link_resolver.py:27-36` (`split_frontmatter`) + `pipeline/reconcile.py:120-184` (`build_frontmatter` fence half) | exact (source being moved) |
| `pipeline/common/progress.py` (new) | service (state store) | file-I/O + batch selection | `pipeline/batch_import.py:47-56, 255-293, 296-313` | exact (source being moved) |
| `pipeline/common/deploy.py` (new) | service (subprocess shell-out) | request-response (external process) | `pipeline/batch_import.py:229-248` (`deploy`) | exact (source being moved) |
| `pipeline/tests/capture_golden.py` (new) | test harness (capture) | file-I/O + transform | `pipeline/backfill_seo_meta.py` (stdlib-only standalone script: `sys.path.insert` + bare import + `main()` + `if __name__` argv flag) | role-match |
| `pipeline/tests/verify_golden.py` (new) | test harness (gate) | file-I/O + transform | `pipeline/link_resolver.py:258-265` (`argparse` + `raise SystemExit(main(...))` exit-code contract) | role-match |
| `pipeline/tests/test_country_blind.py` (new) | test (integration probe) | transform | `pipeline/backfill_seo_meta.py` `main()` + `if __name__ == "__main__"` | role-match |
| `pipeline/link_resolver.py` (modify) | pipeline stage | file-I/O transform | itself (delete def, add import) | exact |
| `pipeline/cross_linker.py` (modify) | pipeline stage | file-I/O transform | itself (delete def, add **aliased** import) | exact |
| `pipeline/reconcile.py` (modify) | pipeline stage | transform | itself (delegate fence-wrapping only) | exact |
| `pipeline/batch_import.py` (modify) | orchestrator | batch / event-driven loop | itself (replace 4 defs with thin wrappers) | exact |

**Import convention every new/modified file must follow** (established by `batch_import.py:365` `import link_resolver`, `:381` `import cross_linker`, `:382` `import reconcile as _reconcile`): bare top-level import resolved via `sys.path[0] == pipeline/`. New form: `from common.frontmatter import split_frontmatter`. **Do not create `pipeline/__init__.py`** and do not use relative imports.

---

## Pattern Assignments

### `pipeline/common/__init__.py` (package marker)

**Analog:** none — `find . -name "__init__.py"` returns zero results repo-wide (verified this session). `pipeline/_legacy/` is a plain directory of four scripts with no init.

**Pattern to use:** empty file (or a one-line docstring). Nothing else. No re-exports — re-exporting would create an import surface that `test_country_blind.py`'s boundary assertion has to reason about, for zero benefit.

```python
"""Country-blind pipeline core. Imported as top-level `common` via sys.path[0]."""
```

---

### `pipeline/common/frontmatter.py` (utility, transform)

**Analog A:** `pipeline/link_resolver.py:27-36` — the `split_frontmatter` to move.

**Module header pattern to copy** (from `link_resolver.py:12-22` — `from __future__` first, stdlib imports alphabetised, then module constants; note `common/` needs **no** path constants):

```python
from __future__ import annotations

import re
from pathlib import Path
```

**`split_frontmatter` — VERBATIM — DO NOT REFORMAT** (`link_resolver.py:25-36`, including the section-banner comment style used throughout this repo):

```python
# ─── Frontmatter ─────────────────────────────────────────────────────────────

def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    split = end + 4
    if split < len(text) and text[split] == "\n":
        split += 1
    return text[:split], text[split:]
```

**Analog B (the duplicate being deleted):** `pipeline/cross_linker.py:202-211`. It is AST-identical; the *only* differences are the leading underscore in the name and single-vs-double quotes:

```python
def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith('---'):
        return '', text
    end = text.find('\n---', 3)
    if end == -1:
        return '', text
    split = end + 4
    if split < len(text) and text[split] == '\n':
        split += 1
    return text[:split], text[split:]
```

Keep the **double-quoted** (`link_resolver`) form as canonical — it matches the newer module and the repo's dominant style.

**Analog C:** `pipeline/reconcile.py:134-184` — the fence-wrapping half of `build_frontmatter` to extract as `render_frontmatter`.

Current source, showing exactly what must move and what must stay (`reconcile.py:134-141` opens the list with a literal `"---"`, `:176-184` closes with `"---"` and `""` then joins):

```python
    lines = [
        "---", id_line,
        f'title: "{title}"',
        ...
    ]
    ...
    lines += [
        f"source_pdf: {pdf_url}",
        "generated_by: pipeline/reconcile.py",
        f"model: {MODEL}",
        f"generated_at: {now}",
        "---",
        "",
    ]
    return "\n".join(lines)
```

**Extract exactly this and no more** (`render_frontmatter` must be equivalent to `"\n".join(["---", *lines, "---", ""])` — a trailing `""` element means the returned string ends with `\n` and no extra blank line):

```python
def render_frontmatter(lines: list[str]) -> str:
    """Wrap pre-rendered YAML lines in --- fences. Trailing newline included.

    Callers own field selection, ordering, and value formatting; this owns only
    the block shape. Deliberately thin — see CLAUDE.md 'do not over-abstract'.
    """
    return "\n".join(["---", *lines, "---", ""])


def quote(value: str) -> str:
    """Double-quote a scalar, escaping embedded double quotes."""
    return '"' + value.replace('"', '\\"') + '"'
```

**Escaping pattern that `quote()` must reproduce** — note `reconcile.py` currently escapes at the *value* site, not the render site (`reconcile.py:122` and `:127`):

```python
    title = _strip_year(entry.get("name_he") or "").replace('"', '\\"')
    ...
    description = build_seo_description(title, pub_date, law_validity).replace('"', '\\"')
```

If `quote()` is adopted at these sites, the `.replace('"', '\\"')` must be removed from the value expression or quoting is applied twice. Safest smallest diff: leave `reconcile.py`'s existing `.replace` + `f'title: "{title}"'` lines completely untouched and delegate **only** the fence-wrapping. `quote()` then exists for the future UK caller and for `test_country_blind.py`, not as a `reconcile.py` refactor.

**Six value styles that must survive byte-identically** (enumerated from `reconcile.py:130-174`, all produced by the caller, none by `render_frontmatter`):

| Style | Current source line | Emitted form |
|---|---|---|
| bare int | `id_line = f"law_id: {law_id}"` (`:132`) | `law_id: 2000001` |
| escaped double-quoted | `f'title: "{title}"'` (`:136`) | `title: "חוק ... (העברת נכסים)"` |
| bare bool | `lines.append("hide_table_of_contents: true")` (`:140`) | `hide_table_of_contents: true` |
| bare scalar | `f"publication_date: {pub_date}"` (`:144`), `f"category: {category}"` (`:161`) | `publication_date: 1950-08-09` |
| explicit null | `lines.append("publication_date: ~")` (`:146`) | `publication_date: ~` |
| block list | `"\n".join(f'  - "{c["desc"]}"' ...)` (`:166-169`) | `law_tags:\n  - "מקרקעין"` |
| inline JSON | `f"ministry_ids: {json.dumps(ministry_ids)}"` (`:174`) | `ministry_ids: [16]` |

**Anti-pattern (explicit):** do not replace any of the above with `yaml.safe_dump`. PyYAML 6.0.3 is installed and would re-quote, reorder, line-wrap, and emit `null` for `~` — guaranteed failure of the `dab1887e…` SHA gate.

**Boundary constraint:** this module must import only `re` / `pathlib` / stdlib. No `reconcile`, no `link_resolver`, no `cross_linker`, no `batch_import`.

---

### `pipeline/common/progress.py` (service, file-I/O + batch selection)

**Analog:** `pipeline/batch_import.py:43-56, 251-313`.

**Section-banner comment style to copy** (`batch_import.py:43-45` — this repo uses two styles; `batch_import.py` uses `# ---`, `link_resolver.py`/`cross_linker.py` use `# ───`. Match the file you are extracting *from*):

```python
# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------
```

**`load_progress` / `save_progress` — VERBATIM except the path parameter** (`batch_import.py:47-56`):

```python
def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        with open(PROGRESS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"done": [], "failed": [], "total_deployed": 0, "priority": []}


def save_progress(progress: dict) -> None:
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
```

Extracted signature: `load_progress(path: Path) -> dict` / `save_progress(path: Path, progress: dict) -> None`. **Critical byte-fidelity details, verified:** `ensure_ascii=False`, `indent=2`, and **no trailing newline** (`json.dump` writes none, and the live 1867-byte file ends with `}`). Do not "improve" this with `path.write_text(json.dumps(...) + "\n")`.

**Security note (ASVS V5):** `json.load` is already the correct choice. Preserve it — never `eval`/`pickle`.

**`get_next_batch` — VERBATIM, with two names parameterised** (`batch_import.py:255-293`):

```python
def get_next_batch(manifest: list[dict], progress: dict, count: int) -> list[dict]:
    """Return next N unprocessed laws that have PDFs. Priority queue is drained first."""
    done_set = set(str(x) for x in progress.get("done", []))
    failed_set = set(str(x) for x in progress.get("failed", []))
    priority_ids = [str(x) for x in progress.get("priority", [])
                    if str(x) not in done_set and str(x) not in failed_set]

    # Build a lookup by law_id for fast access
    by_id = {str(e.get("law_id") or e.get("bill_id")): e for e in manifest}

    batch: list[dict] = []

    # Drain priority queue first
    for pid in priority_ids:
        if len(batch) >= count:
            break
        entry = by_id.get(pid)
        if not entry:
            continue
        if not entry.get("pdf_path") or not Path(entry["pdf_path"]).exists():
            continue
        batch.append(entry)

    # Fill remaining slots from manifest in order
    for entry in manifest:
        if len(batch) >= count:
            break
        law_id = entry.get("law_id") or entry.get("bill_id")
        if not law_id:
            continue
        if str(law_id) in done_set or str(law_id) in failed_set:
            continue
        if any(e is entry for e in batch):
            continue
        if not entry.get("pdf_path") or not Path(entry["pdf_path"]).exists():
            continue
        batch.append(entry)

    return batch
```

Extracted signature: `get_next_batch(manifest, progress, count, id_keys=("law_id", "bill_id"), source_key="pdf_path")`.

Three literal-name sites become parameterised: the `by_id` comprehension, the `law_id = entry.get(...)` line, and the two `entry.get("pdf_path") / Path(entry["pdf_path"]).exists()` checks. Everything else is verbatim.

**PRESERVE EXACTLY — `if any(e is entry for e in batch):` (line 287).** This is *identity* comparison, not equality. Dict entries are unhashable and may compare equal while being distinct manifest rows; `e is entry` is deliberate. Do not "modernise" to `if entry in batch` or to a set of ids — it changes selection and breaks the `next_batch.json` SHA gate.

**`print_status` — VERBATIM, labels defaulted** (`batch_import.py:296-313`):

```python
def print_status(manifest: list[dict], progress: dict) -> None:
    done = set(str(x) for x in progress.get("done", []))
    failed = set(str(x) for x in progress.get("failed", []))
    total = len(manifest)
    with_pdf = sum(1 for e in manifest if e.get("pdf_path"))
    pending = sum(
        1 for e in manifest
        if (e.get("law_id") or e.get("bill_id")) and
           str(e.get("law_id") or e.get("bill_id")) not in done and
           str(e.get("law_id") or e.get("bill_id")) not in failed and
           e.get("pdf_path")
    )
    print(f"Total laws:      {total}")
    print(f"With PDF:        {with_pdf}")
    print(f"Converted:       {len(done)}")
    print(f"Failed:          {len(failed)}")
    print(f"Pending:         {pending}")
    print(f"Total deployed:  {progress.get('total_deployed', 0)}")
```

**Column alignment is load-bearing.** The gate is a byte-diff of the 6 lines against `golden/status.txt`. Only the `"With PDF"` label is source-format-flavoured; parameterise it as `source_label: str = "With PDF"` and keep the padding math producing `f"{source_label}:" ` at the same column (today: label + `:` + spaces to column 18). If parameterising the label risks the alignment, prefer hard-coding the default f-string and only substituting the label text.

---

### `pipeline/common/deploy.py` (service, subprocess request-response)

**Analog:** `pipeline/batch_import.py:225-248`.

**Current source — VERBATIM except `SITE_DIR` and `env`** (`batch_import.py:229-248`):

```python
def deploy() -> bool:
    """Build and deploy the Docusaurus site."""
    logging.info("Deploying site...")
    env = {**os.environ, "USE_SSH": "true", "GIT_USER": "Yuvaldv"}
    try:
        result = subprocess.run(
            ["npm", "run", "deploy"],
            cwd=str(SITE_DIR),
            env=env,
            timeout=300,
            capture_output=False,
        )
        if result.returncode != 0:
            logging.error("Deploy failed with exit code %d", result.returncode)
            return False
        logging.info("Deploy successful.")
        return True
    except (subprocess.TimeoutExpired, OSError) as e:
        logging.error("Deploy error: %s", e)
        return False
```

Extracted signature: `deploy(site_dir: Path, env_overrides: dict | None = None) -> bool`.

**`SITE_DIR` trap (must be handled explicitly).** In `batch_import.py:31-35`:

```python
PIPELINE_DIR = Path(__file__).parent
PROJECT_DIR = PIPELINE_DIR.parent
SITE_DIR = PROJECT_DIR / "site"
```

A `common/deploy.py` is **one directory deeper**, so copy-pasting `Path(__file__).parent.parent / "site"` silently resolves to `pipeline/site` — a directory that does not exist. Do **not** derive the path inside `common/`; take `site_dir` as a required parameter. `batch_import.deploy()` becomes a thin wrapper passing its own module-level `SITE_DIR`.

**Error-handling pattern to preserve verbatim:** the `logging.error(...)` + `return False` shape and the exact exception tuple `(subprocess.TimeoutExpired, OSError)`. Return type stays `bool`; do not raise.

**Security (ASVS V7 / command injection):** list-form `subprocess.run`, no `shell=True`, `capture_output=False`. Preserve all three. **Never log the `env` dict** — it carries `GIT_USER` and the full inherited environment (which in this repo's shell can include `GEMINI_API_KEY` from `pipeline/.env` once `load_dotenv` has run).

**Standing user constraint:** `deploy()` must never be executed during this phase. Gate this file on import-time smoke + source-equivalence review only.

---

### `pipeline/tests/capture_golden.py` (test harness, file-I/O + transform)

**Analog:** `pipeline/backfill_seo_meta.py` — the repo's canonical stdlib-only standalone script that imports a pipeline module.

**Bootstrap + import pattern — copy this exactly** (`backfill_seo_meta.py:1-14`). Note this script lives in `pipeline/`, so `Path(__file__).parent` is right; a script in `pipeline/tests/` needs `Path(__file__).parent.parent`:

```python
"""Backfill `title` + `description` frontmatter onto already-converted laws.
...
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reconcile import build_seo_description  # noqa: E402

LAWS_DIR = Path(__file__).parent.parent / "laws" / "israel"
SKIP = {"placeholder.md", "index.md", "_index.md"}
```

For `pipeline/tests/capture_golden.py` the equivalent is:

```python
PIPELINE_DIR = Path(__file__).parent.parent
PROJECT_DIR = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))
```

**Results-reporting pattern** (`backfill_seo_meta.py` `main()` — group by status, print counts, only enumerate names for non-OK buckets):

```python
def main(dry_run: bool = False) -> None:
    files = sorted(p for p in LAWS_DIR.glob("*.md") if p.name not in SKIP)
    results: dict[str, list[str]] = {}
    for path in files:
        status = fix_file(path, dry_run=dry_run)
        results.setdefault(status, []).append(path.name)

    for status, names in sorted(results.items()):
        print(f"\n[{status}] ({len(names)} files)")
        if status not in ("ok (already has description)", "fixed"):
            for n in names:
                print(f"  {n}")
```

**Frozen-clock shim** — needed because `reconcile.build_frontmatter:125` calls `dt.datetime.now(dt.timezone.utc)`. The hack lives in the harness; production code is not touched:

```python
_real = reconcile.dt.datetime
class _Shim:
    timezone = dt.timezone
    class datetime:
        @staticmethod
        def now(tz=None): return _real(2000, 1, 1, tzinfo=dt.timezone.utc)
reconcile.dt = _Shim
```

**Fingerprint pattern:** one `sha256` over `json.dumps(mapping, ensure_ascii=False, sort_keys=True)`, with the mapping written alongside so a mismatch is inspectable. Expected BEFORE value: `entries=111`, `sha256=dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37`.

---

### `pipeline/tests/verify_golden.py` (test harness / gate, file-I/O + transform)

**Analog:** `pipeline/link_resolver.py:258-265` — the repo's `argparse` + explicit-exit-code CLI contract. `verify_golden.py` is a gate, so the non-zero exit path matters.

**CLI + exit-code pattern — VERBATIM shape** (`link_resolver.py:258-265`):

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--law-id", action="append", dest="law_ids",
                        help="Process specific law_id (repeatable)")
    parser.add_argument("--all", action="store_true", dest="relink_all",
                        help="Re-run on all converted laws")
    args = parser.parse_args()
    raise SystemExit(main(law_ids=args.law_ids, relink_all=args.relink_all))
```

`main()` returns `int` (`link_resolver.py:235` `def main(...) -> int:`, `:243-244` `logging.error(...)` then `return 1`, `:255` `return 0`). Copy that contract: `verify_golden.main()` returns `0` on all-green, `1` on any mismatch.

**Flag set required by the validation map:** `--quick`, `--structure`, `--split`, `--frontmatter`, `--batch`, `--progress-roundtrip`, and no-flag = full suite (adds the link-resolver differential).

**Logging pattern** (`link_resolver.py:236`) — this repo configures logging inside `main()`, not at import:

```python
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
```

`batch_import.py:435` uses `level=logging.WARNING` for its read-only `--status` branch — mirror that for `--quick`.

**Never silently pass a diff.** CLAUDE.md: "Validation errors must never be silently ignored." A non-empty diff is `return 1`, not a warning.

---

### `pipeline/tests/test_country_blind.py` (test, transform)

**Analog:** `pipeline/backfill_seo_meta.py` `main()` + `if __name__ == "__main__":` argv-flag block (same as `capture_golden.py`).

```python
if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("DRY RUN — no files written\n")
    main(dry_run=dry)
```

**Import-boundary requirement (this is the whole point of the file):** it may import **only** from `common.*` plus stdlib. It must never `import reconcile`, `batch_import`, `link_resolver`, or `cross_linker` — which means it must *not* copy `backfill_seo_meta.py`'s `from reconcile import ...` line, only its bootstrap shape.

**Synthetic non-Israel shapes to exercise:** `save_progress(tmp/p.json, {...})` → `load_progress` round-trip; `get_next_batch(manifest, progress, count, id_keys=("doc_id",), source_key="xml_path")`; `render_frontmatter([...])` with UK-shaped fields; `quote()` on a value containing `"`.

**Static boundary assertion to pair with it:**

```
! grep -rnE "^\s*(from|import) (reconcile|batch_import|link_resolver|cross_linker)" pipeline/common/
grep -rn "GEMINI_API_KEY\|GIT_USER" pipeline/common/   # only the deliberate deploy default
```

---

### `pipeline/link_resolver.py` (MODIFY — pipeline stage)

**Change:** delete lines 27-36 (`split_frontmatter`); add a plain import. Call site at line 216 is `split_frontmatter(text)` — **unchanged**, because the extracted name matches.

**Import goes in the existing stdlib block** (`link_resolver.py:12-22`), after the stdlib imports, separated by a blank line — mirroring how `backfill_seo_meta.py` separates its bootstrap import:

```python
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

from common.frontmatter import split_frontmatter

PIPELINE_DIR = Path(__file__).parent
```

**Leave the `# ─── Frontmatter ───` banner removed along with the function** — an empty banner is noise.

**Untouched call site for reference** (`link_resolver.py:215-216`):

```python
    text = md_path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
```

---

### `pipeline/cross_linker.py` (MODIFY — pipeline stage)

**Change:** delete lines 202-211 (`_split_frontmatter`); add an **aliased** import so the call site is untouched.

```python
from common.frontmatter import split_frontmatter as _split_frontmatter
```

**Why aliased:** the call site at line 217 uses the underscored name. Renaming it works too, but the alias is the smaller diff, and — critically — `cross_link_one()` requires a live Gemini client, so a missed rename surfaces as a runtime `NameError` only during a real API run, long after the gate has passed.

**Untouched call site for reference** (`cross_linker.py:214-217`):

```python
def cross_link_one(md_path: Path, client, manifest: list[dict]) -> list[str]:
    """Cross-link one law file in-place. Returns law_ids in manifest but not yet converted."""
    text = md_path.read_text(encoding='utf-8')
    fm, body = _split_frontmatter(text)
```

**Import placement** — `cross_linker.py:13-22` block:

```python
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from common.frontmatter import split_frontmatter as _split_frontmatter

PIPELINE_DIR = Path(__file__).parent
```

**Smoke check after this edit** (no API key needed):

```bash
~/.venv-codex/bin/python -c "import sys; sys.path.insert(0,'pipeline'); import cross_linker; print(cross_linker._split_frontmatter('---\na\n---\nb'))"
```

---

### `pipeline/reconcile.py` (MODIFY — pipeline stage, highest risk)

**Change:** `build_frontmatter` keeps **all** field selection, ordering, and value formatting. It delegates only fence-wrapping.

**Three edits, and only three:**

1. Add the import next to the existing third-party block (`reconcile.py:32-34`):

```python
from dotenv import load_dotenv
from google import genai
from google.genai import types

from common.frontmatter import render_frontmatter
```

2. Line 134-135 — drop the leading `"---"` from the list literal:

```python
    lines = [
        "---", id_line,          # BEFORE
        f'title: "{title}"',
```
becomes
```python
    lines = [
        id_line,                 # AFTER
        f'title: "{title}"',
```

3. Lines 176-184 — drop the trailing `"---"` and `""` and replace the join:

```python
    lines += [
        f"source_pdf: {pdf_url}",
        "generated_by: pipeline/reconcile.py",
        f"model: {MODEL}",
        f"generated_at: {now}",
        "---",                   # DELETE
        "",                      # DELETE
    ]
    return "\n".join(lines)      # → return render_frontmatter(lines)
```

**Forgetting any of the three produces doubled fences on all 111 laws.** The `dab1887e…` SHA gate catches it immediately — run it before committing.

**MUST STAY in `reconcile.py` (do not extract — Hebrew-literal-bearing, extracting them is a legal-fidelity error per CLAUDE.md):**

```python
_YEAR_RE = re.compile(r',\s*ה?תש[א-ת]*"[א-ת]-\d{4}$')


def _strip_year(title: str) -> str:
    """Remove the Hebrew/Gregorian year suffix (e.g. ', התשנ"ו-1996') from a law title."""
    return _YEAR_RE.sub("", title).strip()


def build_seo_description(title: str, pub_date: str, law_validity: str | None) -> str:
    """Deterministic (no-LLM) meta description — templated from data already in frontmatter."""
    year = pub_date[:4] if pub_date else ""
    status = law_validity or "תקף"
    year_part = f" ({year})" if year else ""
    return (
        f'{title}{year_part} — חוק ישראלי, {status}. '
        "הטקסט המלא, מסעיף לסעיף עם קישורים פנימיים, לקריאה חינם ב-Codex Civica."
    )
```

**Downstream consumer to re-verify after this edit** — `pipeline/backfill_seo_meta.py:12-13` does `sys.path.insert(0, str(Path(__file__).parent))` then `from reconcile import build_seo_description`. Adding `from common.frontmatter import ...` to `reconcile.py` means that import now also has to resolve; it does, because `sys.path[0]` is `pipeline/` either way. Confirm with:

```bash
~/.venv-codex/bin/python -c "import sys; sys.path.insert(0,'pipeline'); import backfill_seo_meta; print('ok')"
```

---

### `pipeline/batch_import.py` (MODIFY — orchestrator)

**Change:** replace four definitions with thin module-level wrappers bound to this module's constants, so **all 12 existing call sites stay untouched.**

**Existing call sites that must not change** (verified by grep):

| Line | Call |
|---|---|
| 332 | `progress = load_progress()` |
| 333 | `batch = get_next_batch(manifest, progress, count)` |
| 337, 360, 368, 423 | `print_status(manifest, progress)` |
| 357, 409, 419 | `save_progress(progress)` |
| 417 | `if deploy():` |
| 437 | `progress = load_progress()` |
| 438 | `print_status(manifest, progress)` |

**Wrapper pattern** (keeps the module-level constants at `:31-37` as the single source of path truth):

```python
from common import deploy as _deploy
from common import progress as _progress


def load_progress() -> dict:
    return _progress.load_progress(PROGRESS_PATH)


def save_progress(progress: dict) -> None:
    _progress.save_progress(PROGRESS_PATH, progress)


def get_next_batch(manifest: list[dict], progress: dict, count: int) -> list[dict]:
    return _progress.get_next_batch(manifest, progress, count)


def print_status(manifest: list[dict], progress: dict) -> None:
    _progress.print_status(manifest, progress)


def deploy() -> bool:
    return _deploy.deploy(SITE_DIR, {"USE_SSH": "true", "GIT_USER": "Yuvaldv"})
```

The `import X as _X` aliasing convention already exists in this file (`:382` `import reconcile as _reconcile`, `:383` `from google import genai as _genai`).

**MUST STAY in `batch_import.py` — the `DEPLOY_EVERY` threshold policy** (`:411-421`). This is batch-loop cadence, not a deploy mechanism; each country orchestrator owns its own:

```python
    # ── Deploy check ──────────────────────────────────────────────────────────
    total_done = len(progress.get("done", []))
    prev_deployed = progress.get("total_deployed", 0)
    deploy_threshold = (prev_deployed // DEPLOY_EVERY + 1) * DEPLOY_EVERY
    if total_done >= deploy_threshold:
        logging.info("Reached %d laws — triggering deploy...", total_done)
        if deploy():
            progress["total_deployed"] = total_done
            save_progress(progress)
        else:
            logging.warning("Deploy failed — will retry next batch.")
```

**Also stays:** `load_manifest` / `save_manifest` (`:63-70`), `_process_law`, `run_batch`, and the deferred `import link_resolver` at `:365` (do not hoist it — the try/except ImportError fallback at `:366-369` is deliberate).

**Read-only invocation only.** `python pipeline/batch_import.py --status` is the sole permitted execution form in this phase (standing user instruction: factory import is paused at 111/718).

---

## Shared Patterns

### Module header / import ordering
**Source:** `pipeline/link_resolver.py:12-22`, `pipeline/cross_linker.py:13-22`, `pipeline/batch_import.py:18-29`
**Apply to:** every new and modified `.py` file

```python
#!/usr/bin/env python3
"""One-line summary.

Longer description.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
```

Order: shebang → module docstring → `from __future__ import annotations` → stdlib (alphabetical) → third-party → local (`common.*`) → module constants. `batch_import.py` and `reconcile.py` put a blank line between the docstring and `from __future__`; `link_resolver.py` and `cross_linker.py` do not. Match whichever file you are editing.

### Type-hint style
**Source:** all four modified modules
**Apply to:** every new function

Modern PEP 604/585 built-in generics, enabled by `from __future__ import annotations`: `tuple[str, str]`, `list[dict]`, `dict[str, str] | None`, `Path`. No `typing.List` / `typing.Optional` anywhere in this repo — do not introduce them.

### Section-banner comments
**Source:** two coexisting styles
**Apply to:** new modules — pick the one matching the file the code came from

```python
# ─── Frontmatter ─────────────────────────────────────────────────────────────   # link_resolver.py:25, cross_linker.py:200
```
```python
# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------                                            # batch_import.py:43-45
```

`common/frontmatter.py` ← box-drawing style (from `link_resolver`). `common/progress.py` and `common/deploy.py` ← dashed style (from `batch_import`).

### Error handling: log + return sentinel, don't raise
**Source:** `pipeline/batch_import.py:229-248` (`deploy`), `pipeline/link_resolver.py:242-244` (`main`)
**Apply to:** `common/deploy.py`, `verify_golden.py`

```python
    try:
        result = subprocess.run(...)
        if result.returncode != 0:
            logging.error("Deploy failed with exit code %d", result.returncode)
            return False
        return True
    except (subprocess.TimeoutExpired, OSError) as e:
        logging.error("Deploy error: %s", e)
        return False
```

`%s`-style lazy logging args (never f-strings inside `logging.*`). Narrow exception tuples, never bare `except:`. `main()` returns `int`; callers do `raise SystemExit(main(...))`.

### File I/O: always explicit UTF-8
**Source:** `link_resolver.py:215,232`, `cross_linker.py:216`, `batch_import.py:49,55,66`
**Apply to:** every read/write in every new file

```python
text = md_path.read_text(encoding="utf-8")
md_path.write_text(fm + body, encoding="utf-8")
with open(PROGRESS_PATH, encoding="utf-8") as f: ...
json.dump(progress, f, ensure_ascii=False, indent=2)
```

Hebrew content makes `ensure_ascii=False` and explicit `encoding="utf-8"` mandatory, not stylistic.

### `sys.path` bootstrap for scripts outside `pipeline/`
**Source:** `pipeline/backfill_seo_meta.py:12-13`
**Apply to:** all three files under `pipeline/tests/`

```python
sys.path.insert(0, str(Path(__file__).parent))     # for a script IN pipeline/
sys.path.insert(0, str(PIPELINE_DIR))              # for a script in pipeline/tests/ — one level deeper
from reconcile import build_seo_description  # noqa: E402
```

The `# noqa: E402` comment on the post-bootstrap import is the existing convention.

### Interpreter
**Source:** `STATE.md` Known Constraints
**Apply to:** every command in every task

`~/.venv-codex/bin/python` — absolute path, always. `which python3` resolves to the in-repo `.venv/` which lacks `google-genai` / `python-dotenv`, producing `ModuleNotFoundError` that reads like a refactor regression.

### Tree-restore discipline after any proof run
**Source:** research Pitfall 1/2 (no code analog — this is a process pattern)
**Apply to:** every task that executes `link_resolver.py --all`

```bash
git checkout -- laws/israel/
test -z "$(git status --porcelain laws/israel/)"
```

Every push to `main` auto-deploys (`.github/workflows/deploy.yml`, `on: push: branches: [main]`, no path filter). Never `git add -A` in this phase; stage `pipeline/` paths explicitly.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pipeline/common/__init__.py` | package marker | n/a | Zero `__init__.py` files exist repo-wide (verified: `find . -name "__init__.py"` → empty). No packaging config either (no `pyproject.toml`/`setup.py`/`setup.cfg`). Use an empty file with a one-line docstring; deliberately do **not** create `pipeline/__init__.py`. |

**Partial-analog note:** `pipeline/tests/*` have no true analog either — the repo has **zero test infrastructure** (no `tests/` dir, no pytest, no config). Their assigned analogs (`backfill_seo_meta.py`, `link_resolver.py`'s CLI block) supply the *script shape* only. The harness *logic* (frozen-clock shim, SHA fingerprinting, git-diff differential) has no in-repo precedent — take it from `07-RESEARCH.md` "Code Examples", where every snippet was prototyped and executed with a recorded BEFORE value.

**Deliberately excluded as analogs:** `pipeline/_legacy/convert*.py` each define their own `build_frontmatter`, but are imported by nothing and are superseded. Do not consolidate them into `common/`; do not copy their patterns.

---

## Metadata

**Analog search scope:** `pipeline/` (all 11 top-level modules + `_legacy/`), repo-wide `find -name "__init__.py"`
**Files scanned:** 8 read (targeted ranges), 15 listed
**Grep verifications this session:** `split_frontmatter` → 4 hits (2 defs, 2 call sites); `load_progress|save_progress|get_next_batch|print_status|deploy(` in `batch_import.py` → 5 defs + 12 call sites; `__init__.py` repo-wide → 0
**All line numbers in this document re-verified against the working tree at `HEAD` (12665ad) on 2026-08-09.**
