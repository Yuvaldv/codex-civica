# Phase 7: Shared Pipeline Core — Research

**Researched:** 2026-08-09
**Domain:** Python refactoring / behaviour-preserving code extraction (stdlib only, no new runtime dependencies)
**Confidence:** HIGH (every structural claim below was verified by reading and *executing* the current source in this session)

---

## Summary

Phase 7 is a pure extraction refactor: move ~150 already-duplicated or country-blind lines out of four Israel-specific pipeline modules into a new `pipeline/common/` package, with a hard zero-behaviour-change bar. The milestone research (`.planning/research/ARCHITECTURE.md:96–105`) named the exact targets; **all of its line references were re-verified against the current source and every one is still accurate.** The two `split_frontmatter` implementations were confirmed **AST-identical** (not merely similar) and produce identical output on all 112 files in `laws/israel/` plus six edge cases — so that extraction is provably risk-free.

The single most important finding is a **blocker on the phase's stated exit gate**. Success criterion 2 and `ARCHITECTURE.md:422–424` both prescribe: *"run `python pipeline/link_resolver.py --all`, then `git diff --stat laws/israel/` must be empty."* **That gate fails today, before a single line of refactor code is written.** On a clean tree at `HEAD`, one run of `link_resolver.py --all` mutates 8 of 111 law files (22 insertions / 22 deletions). Four of them converge after one run (stale content — the Pass-2 regex changed after the last full relink). The other four (`2000326`, `2000390`, `2000416`, `2000595`) **accumulate corrupted text on every single run** — a genuine, reproducible, pre-existing idempotency bug in `link_resolver._STRIP_MG_INDEX`. The phase gate must therefore be redefined as a *before/after differential* rather than a diff-vs-HEAD test, and the idempotency bug must be filed separately, not fixed inside a "zero behaviour change" refactor.

Everything else needed to prove byte-identity was prototyped and confirmed working in this session: `link_resolver --all` is fully deterministic (same input → byte-identical output, verified across a checkout/re-run cycle), `build_frontmatter` can be characterised over all 111 manifest entries offline with a frozen timestamp (SHA `dab1887e…`), `get_next_batch` is pure and snapshot-able, `save_progress` round-trips byte-identically, and `batch_import.py --status` produces a stable 6-line output. No Gemini API call is required for any part of the proof.

**Primary recommendation:** Create `pipeline/common/` as a plain sys.path-rooted subpackage (`pipeline/common/__init__.py`, **no** `pipeline/__init__.py`), extract in four independently-provable steps ordered lowest-risk-first (`split_frontmatter` → `progress` → `deploy` → `render_frontmatter`), and gate each step on a stdlib-only characterization harness that compares pipeline output *before* vs *after* the refactor — never against `HEAD`.

---

## User Constraints

**No `CONTEXT.md` exists for this phase** (`.planning/phases/07-shared-pipeline-core/` is empty). There are no locked user decisions from `/gsd:discuss-phase` to honour. All design latitude below is Claude's discretion, bounded by CLAUDE.md and by the milestone decisions already recorded in `STATE.md`.

Binding milestone decisions carried from `STATE.md` (treat as locked):

| Date | Decision |
|------|----------|
| 2026-08-09 | "UK pipeline is a sibling of Israel's, not a shared framework — two data sources is not evidence for an abstraction (CLAUDE.md: 'do not over-abstract'); only the ~150 genuinely country-blind lines (frontmatter split, progress tracking, deploy) move to `pipeline/common/` in Phase 7" |
| 2026-05-19 | "Paused factory import at 111/718 — do not resume `batch_import.py` proactively; wait for explicit next steps" |

**Direct consequence for the planner:** no task in this phase may invoke `batch_import.py` without `--status`, and no task may call `deploy()`. Both would violate a standing user instruction.

---

## Project Constraints (from CLAUDE.md)

| Directive | Consequence for Phase 7 |
|-----------|------------------------|
| "Do not redesign architecture prematurely" | Extract exactly the four named items. Do not introduce a plugin/registry/ABC "country interface". |
| "Do not over-abstract" | `render_frontmatter` must be a thin, order-preserving emitter — not a schema/validation layer. |
| "Do not refactor without evidence" | Evidence exists and is cited below (AST-identical duplicate, 4 call sites, milestone need). Nothing beyond that list has evidence. |
| "Iterate incrementally" | Four commits, one extraction each — not one big-bang commit. |
| "Compare outputs before updating pipeline logic" | The characterization harness must be built and its BEFORE fingerprints captured *before* any production file is edited. This is Wave 0. |
| "Keep fixtures and golden outputs" | Commit the BEFORE fingerprints as tracked fixtures under `pipeline/tests/golden/` so the AFTER run diffs against a versioned artefact, not a `/tmp` file. |
| "Validation errors must never be silently ignored" | If a characterization diff is non-empty, the step fails — do not "accept" a diff as cosmetic. |
| "Never paraphrase legal language" / "Preserve numbering exactly" | Zero law-body text may change. The gate enforces this mechanically. |
| "Prefer explicit uncertainty over incorrect confidence" | The pre-existing idempotency bug must be documented and filed, not silently absorbed into the refactor's diff. |

**No project skills directory exists** — `.claude/skills/` is absent. [VERIFIED: `ls .claude/skills/` → not found]

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Frontmatter `---` block split | `pipeline/common/frontmatter.py` | — | Pure text operation on a Markdown convention. Zero language/jurisdiction content. Already duplicated verbatim in two Israel modules. |
| Frontmatter YAML-block rendering | `pipeline/common/frontmatter.py` | `pipeline/reconcile.py` (builds the Israel field set) | The *serialisation* (quoting, `~` for null, block lists, `---` fences) is the site's contract; the *field values* are Israel-specific and stay in `reconcile.py`. |
| SEO description text / year-suffix stripping | `pipeline/reconcile.py` (stays) | — | `build_seo_description()` and `_strip_year()` are Hebrew-literal-bearing. Extracting them would be a fidelity error. Explicitly excluded by `ARCHITECTURE.md:101`. |
| Progress file load/save | `pipeline/common/progress.py` | caller supplies path | JSON `{done, failed, total_deployed, priority}` — no country content; only `PROGRESS_PATH` differs. |
| Batch selection (priority-queue-first) | `pipeline/common/progress.py` | caller supplies id/source keys | The drain-priority-then-manifest-order algorithm is the project's scheduling idea, generic once `pdf_path` → `source_path`. |
| Status printing | `pipeline/common/progress.py` | caller supplies labels | Generic counting; only the `"With PDF"` label is source-format-flavoured → parameterise with a default that reproduces today's output byte-for-byte. |
| Site deploy | `pipeline/common/deploy.py` | — | Site-level (`npm run deploy` in `site/`), not country-level. One site serves all countries. |
| Deploy *threshold* logic (`DEPLOY_EVERY`, `total_deployed` bookkeeping) | `pipeline/batch_import.py` (stays) | — | Batch-loop policy, not a deploy mechanism. Each country's orchestrator owns its own cadence. |
| OCR / native extraction / Gemini reconciliation | `pipeline/extract_*.py`, `reconcile.py` (stay) | — | PDF+Hebrew+LLM specific; the UK path has none of these (`STATE.md` 2026-08-09 decision). |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`json`, `pathlib`, `os`, `subprocess`, `sys`) | 3.12.3 | Everything `pipeline/common/` needs | The four extraction targets already use nothing else. Adding a dependency to a zero-behaviour-change refactor is unjustifiable. [VERIFIED: read all four source modules] |

**This phase requires zero new runtime dependencies.** [VERIFIED: `load_progress`/`save_progress`/`get_next_batch`/`print_status`/`deploy`/`split_frontmatter`/`build_frontmatter` import only `json`, `os`, `subprocess`, `logging`, `pathlib`, `datetime`, `sys`]

### Supporting (dev-only, optional)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 9.1.1 (latest on PyPI) | Test-runner ergonomics for the characterization suite | **Optional.** The repo has zero test infrastructure today. The characterization harnesses prototyped in this session are plain stdlib scripts and need no runner. Recommend deferring pytest to Phase 9 (which has real golden-fixture needs per `ARCHITECTURE.md`). [VERIFIED: `pip index versions pytest` → 9.1.1; `python -m pytest --version` in `~/.venv-codex` → *No module named pytest*] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled YAML emitter in `render_frontmatter` | `PyYAML` (already installed, 6.0.3) or `python-frontmatter` (1.1.0) | **Reject.** Normally "don't hand-roll YAML" is correct — here it is inverted. `yaml.safe_dump` would re-quote strings, reorder keys, wrap long lines, and emit `null` instead of `~`. That breaks byte-identity on all 111 files and would rewrite the site's frontmatter contract mid-refactor. The existing hand-rolled emitter must be preserved *verbatim*. |
| Plain package (`pipeline/common/__init__.py`, no `pipeline/__init__.py`) | Full package with `pipeline/__init__.py` + relative imports (`from .common.frontmatter import …`) | **Reject.** Relative imports break `python pipeline/link_resolver.py` — the invocation form used by every script in this repo and by `PIPELINE.md`. Would force every entry point to `-m`, a large blast radius for a refactor whose whole point is zero change. |
| Plain package | Installable package (`pyproject.toml` + `pip install -e .`) | **Reject for this phase.** No packaging exists today (no `setup.py`/`pyproject.toml`/`setup.cfg` anywhere) [VERIFIED: `find`]. Introducing one is a separate decision with its own regression surface. |
| `sys.path.insert` bootstrap in each module | Rely on `sys.path[0]` = script dir | Script-dir is sufficient for all current invocations and is cwd-independent (verified from `/`). Only `python -m pipeline.X` would need the bootstrap, and that form is **already partially broken today** (see Pitfall 4). |

**Installation:** none required.

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| *(none — no runtime dependency added)* | — | — | — | — | — | N/A |
| `pytest` (optional dev-only) | PyPI | 150+ releases, 2.0.0 → 9.1.1 | very high | github.com/pytest-dev/pytest | **unavailable** | Optional / recommend defer |

**slopcheck could not be installed or run in this environment** (`pip install slopcheck` failed; `slopcheck` not on PATH). Per the degradation protocol, `pytest` is tagged **[ASSUMED]** rather than `[VERIFIED: PyPI]`, even though `pip index versions pytest` confirmed 9.1.1 exists and the release history spans 150+ versions. Because the recommendation is to **not install it in this phase**, no `checkpoint:human-verify` gate is needed. If the planner chooses to add it anyway, gate it behind one.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │  ENTRY POINTS (all: python pipeline/X.py)   │
                    │  sys.path[0] == /mnt/c/Dev/codex-civica/    │
                    │                 pipeline/                    │
                    └──────────────┬──────────────────────────────┘
                                   │
        ┌──────────────┬───────────┼────────────┬──────────────────┐
        ▼              ▼           ▼            ▼                  ▼
  batch_import.py  link_resolver reconcile  cross_linker   backfill_seo_meta.py
   (orchestrator)      .py          .py        .py         (sys.path.insert +
        │               │            │           │          from reconcile import)
        │               │            │           │
        │  reads/writes │            │           │
        │  data/raw/israel/          │           │
        │  import_progress.json      │           │
        │  (GITIGNORED — no git      │           │
        │   recovery possible)       │           │
        │               │            │           │
        └───────┬───────┴─────┬──────┴─────┬─────┘
                │             │            │
                ▼             ▼            ▼
        ┌───────────────────────────────────────────────────┐
        │      NEW: pipeline/common/  (import as top-level  │
        │      `common.*` — resolves via sys.path[0])       │
        │                                                    │
        │  frontmatter.py                                    │
        │    split_frontmatter(text) -> (fm, body)           │
        │      ← link_resolver.resolve_one()                 │
        │      ← cross_linker.cross_link_one()               │
        │    render_frontmatter(fields) -> str               │
        │      ← reconcile.build_frontmatter()               │
        │                                                    │
        │  progress.py                                       │
        │    load_progress / save_progress                   │
        │    get_next_batch / print_status                   │
        │      ← batch_import.run_batch(), __main__          │
        │                                                    │
        │  deploy.py                                         │
        │    deploy(site_dir, env)                           │
        │      ← batch_import.run_batch() [NEVER CALLED      │
        │         DURING THIS PHASE]                          │
        └───────────────────────────────────────────────────┘
                │  one-way dependency edge only
                ▼
        common/ must NEVER import from any Israel module,
        nor from the future pipeline/uk/ package.

  Output boundary:  laws/israel/*.md  (111 laws + index.md, git-TRACKED)
  Deploy boundary:  push to main ──► .github/workflows/deploy.yml ──► gh-pages
                    (AUTOMATIC on every push — see Pitfall 6)
```

### Recommended Project Structure

```
pipeline/
├── common/                  # NEW — country-blind core
│   ├── __init__.py          # empty; makes `common` importable as a package
│   ├── frontmatter.py       # split_frontmatter, render_frontmatter
│   ├── progress.py          # load/save_progress, get_next_batch, print_status
│   └── deploy.py            # deploy()
├── tests/                   # NEW — characterization harness (stdlib only)
│   ├── golden/              # committed BEFORE fingerprints
│   │   ├── link_resolver_all.diff
│   │   ├── frontmatter_111.json
│   │   ├── next_batch.json
│   │   └── status.txt
│   ├── capture_golden.py    # writes golden/* — run once, pre-refactor
│   └── verify_golden.py     # re-runs and diffs — the phase gate
├── batch_import.py          # MODIFIED — imports common.progress, common.deploy
├── link_resolver.py         # MODIFIED — imports common.frontmatter
├── cross_linker.py          # MODIFIED — imports common.frontmatter
├── reconcile.py             # MODIFIED — build_frontmatter delegates to common
├── extract_native.py        # UNCHANGED
├── extract_ocr.py           # UNCHANGED
├── backfill_*.py            # UNCHANGED
├── fetch*.py                # UNCHANGED
└── _legacy/                 # UNCHANGED (dead code, imported by nothing)
```

**Do NOT create `pipeline/__init__.py`.** It converts `pipeline` into a package and, combined with relative imports, breaks every documented invocation.

### Pattern 1: sys.path-rooted subpackage import

**What:** `pipeline/common/` becomes importable as top-level `common` because `sys.path[0]` is the directory of the executed script.

**When to use:** This repo, this phase. It matches the existing convention exactly — `batch_import.py` already does bare `import reconcile` / `import link_resolver` / `import cross_linker`.

**Authoritative basis:** *"The first entry in the module search path is the directory that contains the input script, if there is one. Otherwise, the first entry is the current directory, which is the case when executing the interactive shell, a `-c` command, or `-m` module."* [CITED: docs.python.org/3/library/sys_path_init.html]

**Example:**

```python
# pipeline/link_resolver.py  (after)
from common.frontmatter import split_frontmatter   # resolves via sys.path[0] == pipeline/
```

```python
# pipeline/cross_linker.py  (after)
from common.frontmatter import split_frontmatter
# and delete the local _split_frontmatter (lines 202-211).
# NOTE: cross_link_one() calls it at line 217 as `_split_frontmatter(text)`.
# Either rename the call site or alias:
#   from common.frontmatter import split_frontmatter as _split_frontmatter
# Aliasing is the smaller diff and keeps the call site untouched — prefer it.
```

**Empirically verified in this session** with a scratch prototype at `/tmp/proto/`:
- `python /tmp/proto/pipeline/probe_a.py` from repo root → `from common.frontmatter import …` **works**
- same script run with cwd=`/` → **works** (cwd-independent)
- `python -m pipeline.probe_a` from `/tmp/proto` → **`ModuleNotFoundError: No module named 'common'`** (expected; `-m` is not a supported invocation form here)

### Pattern 2: Byte-fidelity-preserving extraction of a hand-rolled emitter

**What:** `render_frontmatter` must reproduce `reconcile.build_frontmatter`'s output byte-for-byte. The safest shape is an ordered `(key, rendered_value)` list plus a small set of explicit value styles — **not** a dict-to-YAML converter.

**Why:** `build_frontmatter` uses six distinct value styles that no generic serialiser reproduces. Enumerated from `reconcile.py:120-184` [VERIFIED: read source + executed over 111 entries]:

| Style | Example line | Rule |
|-------|--------------|------|
| bare int | `law_id: 2000001` | no quotes |
| escaped double-quoted | `title: "חוק רשות הפיתוח (העברת נכסים)"` | inner `"` → `\"` |
| bare bool | `hide_table_of_contents: true` | lowercase, unquoted |
| bare scalar | `publication_date: 1950-08-09`, `category: real-estate`, `source_pdf: https://…` | unquoted, verbatim |
| explicit null | `publication_date: ~` | tilde, not `null` |
| block list | `law_tags:\n  - "מקרקעין"\n  - "ניהול נכסים"` | two-space indent, quoted items |
| inline JSON | `ministry_ids: [16]` | `json.dumps` output |

**Example:**

```python
# pipeline/common/frontmatter.py
def render_frontmatter(lines: list[str]) -> str:
    """Wrap pre-rendered YAML lines in --- fences. Trailing blank line included.

    Callers own field selection, ordering, and value formatting; this owns only
    the block shape. Deliberately thin — see CLAUDE.md 'do not over-abstract'.
    """
    return "\n".join(["---", *lines, "---", ""])


def quote(value: str) -> str:
    """Double-quote a scalar, escaping embedded double quotes (Israel + UK share this)."""
    return '"' + value.replace('"', '\\"') + '"'
```

```python
# pipeline/reconcile.py  (after) — build_frontmatter keeps ALL field logic,
# delegates only the fence-wrapping:
    lines = [id_line, f'title: {quote(title)}', ...]
    ...
    lines += [
        f"source_pdf: {pdf_url}",
        "generated_by: pipeline/reconcile.py",
        f"model: {MODEL}",
        f"generated_at: {now}",
    ]
    return render_frontmatter(lines)
```

**Beware:** today's `build_frontmatter` appends the literal strings `"---"` and `""` to `lines` *before* joining (`reconcile.py:176-184`). After delegation, those two entries must be removed from the caller or the output gains a duplicate fence. This is exactly what the frontmatter SHA gate catches.

### Pattern 3: Diff-fingerprint gate (git as the snapshot mechanism)

**What:** Because `link_resolver.py --all` mutates tracked files in place and is deterministic, `git diff` *is* the output fingerprint. Capture it before the refactor, restore, refactor, capture again, compare the two diffs.

**Verified deterministic:** ran `--all` from a clean `HEAD`, snapshotted; `git checkout -- laws/israel/`; ran again; `diff -rq` against the snapshot → **identical**. [VERIFIED: executed this session]

### Anti-Patterns to Avoid

- **Big-bang extraction (all four in one commit).** Loses the ability to bisect which extraction broke byte-identity. Contradicts CLAUDE.md "iterate incrementally".
- **Fixing the `_STRIP_MG_INDEX` idempotency bug inside this phase.** It changes `laws/israel/` content, which destroys the only property that makes the refactor verifiable. File it as a separate v1.0 bug.
- **Committing pipeline output produced by a proof run.** Every push to `main` auto-deploys (see Pitfall 6). Always `git checkout -- laws/israel/` after a proof run.
- **Adding `pipeline/__init__.py`** or converting to relative imports. Breaks all documented entry points.
- **Replacing the hand-rolled YAML emitter with PyYAML.** Guaranteed byte-identity failure.
- **Generalising `print_status` labels without defaults.** Criterion 3 requires the exact 6-line output to survive.
- **Speculatively adding a `Country` ABC / plugin registry / config schema.** No evidence; explicitly forbidden by the 2026-08-09 `STATE.md` decision and by CLAUDE.md.
- **Running `batch_import.py` without `--status`.** Violates the standing import-pause instruction and burns Gemini quota.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Snapshotting 111 law files before/after | A custom copy-tree + manifest-hash utility | `git diff laws/israel/ > golden/link_resolver_all.diff` + `git checkout -- laws/israel/` | Working tree is clean and the files are tracked. Git already is the snapshot store, restore mechanism, and diff engine. |
| Proving two functions behave identically | Eyeballing the diff | `ast.parse` + `ast.dump` comparison (used in this session) **plus** differential execution over all 112 real files | Textual similarity ≠ behavioural identity. AST-equality proves the former; corpus execution proves the latter. |
| Freezing `generated_at` for the frontmatter characterization | Editing `reconcile.py` to accept an injectable clock | Monkeypatch `reconcile.dt` with a shim exposing `datetime.now()` and `timezone` (prototyped and working this session) | Injecting a clock parameter is a production-code change inside a zero-change refactor. The harness owns the hack; production stays untouched. |
| Comparing 111 frontmatter blocks | Per-file assertions | One `sha256` over `json.dumps(mapping, sort_keys=True, ensure_ascii=False)` | Single scalar, trivially diffable, and the mapping is dumped alongside so a mismatch is inspectable. |
| YAML serialisation | *(inverted)* — do NOT reach for PyYAML here | Preserve the existing hand-rolled emitter verbatim | The normal advice is wrong in a byte-identity refactor. See Alternatives Considered. |

**Key insight:** in a behaviour-preservation refactor, "reuse a library" is often the *wrong* instinct — any library that normalises output is a regression generator. The tooling to reach for is the tooling that *detects* change (git, AST comparison, hashing), not the tooling that *produces* output.

---

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | `data/raw/israel/import_progress.json` — `{done: 111, failed: 0, total_deployed: 111, priority: 23}`, 1867 bytes. **`data/raw/` is gitignored** (`.gitignore:2`), so this file is **untracked and NOT recoverable via git** if corrupted. Also `data/raw/israel/manifest_laws.json` (1076 entries) and ~700 `*.native.txt` / `*.ocr.txt` / `*.ocr_layout.json` / `*.pdf` artefacts — same gitignored status. [VERIFIED: `git check-ignore -v` → `.gitignore:2:data/raw/`] | **Back up `import_progress.json` and `manifest_laws.json` to a location outside the repo before any task touches `batch_import.py`.** No code change needed — the JSON shape is unchanged. `save_progress` round-trips the current file **byte-identically** with `json.dump(..., ensure_ascii=False, indent=2)` and **no trailing newline** [VERIFIED: executed]. Any extracted version must preserve that exactly. |
| **Live service config** | GitHub Pages `gh-pages` branch, published by `.github/workflows/deploy.yml` **on every push to `main`** and by `site/` npm script `deploy` (`docusaurus deploy`). Live at `https://Yuvaldv.github.io/codex-civica/`. Also `site/.docusaurus/` and `site/build/` caches (gitignored). | **No config change.** But: any accidental commit of mutated law files auto-publishes. Phase 7 must not call `deploy()` and must not commit pipeline output. |
| **OS-registered state** | **None — verified.** `crontab -l` → "no crontab for yuvalv"; `~/.config/systemd/user/` → does not exist; no launchd/pm2/Task Scheduler entries reference the pipeline. `.claude/scheduled_tasks.lock` exists but is gitignored local scratch and references no pipeline module. | None. |
| **Secrets / env vars** | `pipeline/.env` (gitignored) holds `GEMINI_API_KEY`, read by `reconcile.load_api_key()` via `dotenv.load_dotenv(PIPELINE_DIR / ".env")`. `deploy()` injects `USE_SSH=true` and `GIT_USER=Yuvaldv` into the subprocess env. | **Code-path only, no key rename.** If `deploy()` moves to `common/deploy.py`, `SITE_DIR` must be passed in (it is `PROJECT_DIR / "site"`, derived from `batch_import.py`'s `__file__` — a `common/` module's `__file__` is one level deeper, so a naive copy-paste of the `PIPELINE_DIR.parent` idiom silently points at the wrong directory). Prefer an explicit `site_dir: Path` parameter. `pipeline/.env` path is likewise `__file__`-relative in `reconcile.py` — unchanged by this phase, but the same trap applies to any future move. |
| **Build artifacts / installed packages** | `pipeline/__pycache__/` contains `.pyc` for `batch_import`, `convert`, `cross_linker`, `extract_native`, `extract_ocr`, `fetch`, `link_resolver`, `reconcile` (cpython-312). No `egg-info`, no `pyproject.toml`, no installed console scripts, no editable install. Two venvs exist: `~/.venv-codex` (the one `STATE.md` documents, has `google-genai 1.75.0`, `python-dotenv 1.2.2`, `PyMuPDF 1.27.2.3`, `PyYAML 6.0.3`, `python-frontmatter 1.1.0`) and an in-repo `.venv/` (gitignored, on NTFS). | **Purge `__pycache__` before each proof run**: `find pipeline -name __pycache__ -type d -exec rm -rf {} +`. Stale bytecode will not cause a false pass in CPython 3 (source is required), but a stale `.pyc` for a *deleted* module is confusing during bisect. **Use `~/.venv-codex/bin/python` explicitly** for every command — `which python3` in this shell resolves to the in-repo `.venv`, which is NOT the documented environment. |

---

## Common Pitfalls

### Pitfall 1 (BLOCKER): The phase's prescribed exit gate fails today, before any refactor

**What goes wrong:** `ARCHITECTURE.md:422-424` and success criterion 2 both say *"run `python pipeline/link_resolver.py --all` → `git diff --stat laws/israel/` must be empty."* On a clean tree at `HEAD` this produces **8 changed files, 22 insertions(+), 22 deletions(-)**.

**Verified this session:**

```
$ git status --porcelain            # clean
$ ~/.venv-codex/bin/python pipeline/link_resolver.py --all
$ git diff --stat laws/israel/ | tail -1
 8 files changed, 22 insertions(+), 22 deletions(-)
```

Changed files: `2000111`, `2000119`, `2000326`, `2000390`, `2000416`, `2000490`, `2000595`, `2001134`.

**Two distinct causes, verified by running the pipeline three consecutive times:**

| Class | Files | Behaviour |
|-------|-------|-----------|
| **A — stale content** | `2000111`, `2000119`, `2000490`, `2001134` | Converge after one run. The committed content predates the current Pass-2 regex. E.g. `2001134` gains `[סעיף 14](#section-14)` and re-scopes `[סעיף 4](#section-4)(ג)` → `[סעיף 4(ג)](#section-4)`. Harmless, one-shot. |
| **B — accumulating corruption** | `2000326`, `2000390`, `2000416`, `2000595` | **Grow on every run, forever.** Run 1 ≠ Run 2 ≠ Run 3. |

Class-B example (`2000595`, after run 2 — orphaned Sidenote bullets glued onto the source-link line, doubling each run):

```
[![מסמך PDF](/img/pdf-icon.svg)](…PDF) [מסמך המקור באתר הכנסת](…PDF)- [אי תחולת [סעיף 218](#section-218)](#section-219)- [ערעור …](#section-415)- [אי תחולת [סעיף 218](#section-218)](#section-219)- [ערעור …](#section-415)
```

**Root cause (isolated to one regex, `link_resolver.py:122-124`):**

```python
_STRIP_MG_INDEX = re.compile(
    r"\n+(?:##+ (?:Sidenotes|הערות גיליון)\n\n?)?(?:- \[[^\]]*\]\(#section-\d+\)\n)+"
)
```

The bullet sub-pattern `- \[[^\]]*\]\(#section-\d+\)` cannot match a bullet whose note text itself contains a Markdown link — `[^\]]*` stops at the *inner* `]`. Nested-link bullets arise because Pass 2 (`linkify_section_refs`) skips only lines starting with `>`, so on run N+1 it linkifies `סעיף 218` *inside* the previously-emitted Sidenotes bullet. When such a bullet is first in the run, the whole strip cannot anchor at the `## Sidenotes` header; it instead matches a later run of plain bullets, consuming the preceding `\n+` and leaving the header plus the nested bullet orphaned and glued to the previous line. `inject_margin_note_index` then appends a fresh complete Sidenotes block. Reproduced minimally:

```python
body = "TEXT\n\n## Sidenotes\n\n- [אי תחולת [סעיף 218](#section-218)](#section-219)\n- [plain](#section-5)\n"
lr._STRIP_MG_INDEX.sub("", body)
# → 'TEXT\n\n## Sidenotes\n\n- [אי תחולת [סעיף 218](#section-218)](#section-219)'
#   header NOT removed, nested bullet NOT removed  ← the leak
```

**How to avoid:** redefine the gate as a **before/after differential**, not a diff-against-HEAD:

1. `git checkout -- laws/israel/` (guarantee clean start)
2. run the pipeline; `git diff laws/israel/ > pipeline/tests/golden/link_resolver_all.diff`; `git checkout -- laws/israel/`
3. perform the extraction step
4. run the pipeline again; `git diff laws/israel/ > /tmp/after.diff`; `git checkout -- laws/israel/`
5. **gate:** `diff pipeline/tests/golden/link_resolver_all.diff /tmp/after.diff` is empty
6. **and** `git diff --stat laws/israel/` is empty (trivially true after step 5's checkout — this satisfies criterion 2 as literally written, because the *committed* Israel content is never touched by this phase)

**Recommendation for the planner:** restate criterion 2 in the plan as *"the diff the pipeline produces over `laws/israel/` is byte-identical before and after the refactor, and the committed content of `laws/israel/` is unchanged."* Both halves are mechanically checkable and together are strictly stronger than the original wording. File the Class-B bug as a separate v1.0 issue — **do not fix it in Phase 7.**

**Warning signs:** a task that says "run the pipeline and commit the result"; a diff that shrinks between steps (means someone "fixed" content mid-refactor).

### Pitfall 2: `git checkout -- laws/israel/` is the only safe restore, and it is easy to forget

**What goes wrong:** A proof run leaves 8 mutated tracked files. If the next task runs `git add -A` / `git commit -am`, corrupted law content enters history — and every push to `main` auto-deploys it live.

**How to avoid:** every proof task ends with an explicit `git checkout -- laws/israel/` followed by `git status --porcelain laws/israel/ | wc -l` asserting `0`. Never use `git add -A` in this phase; stage `pipeline/` paths explicitly.

**Warning signs:** `git status` shows modified `laws/israel/*.md` at commit time.

### Pitfall 3: `import_progress.json` is unrecoverable

**What goes wrong:** `data/raw/` is gitignored. Corrupting `import_progress.json` loses the record of which 111 laws are converted and the 23-entry priority queue, with no `git checkout` to fall back on. Reconstructing `done` from `ls laws/israel/` is possible; reconstructing `priority` and `total_deployed` is not.

**How to avoid:** Wave 0 task: copy `data/raw/israel/import_progress.json` and `manifest_laws.json` to a scratch path **outside** the repo, and verify the copies. Every subsequent progress task must be read-only (`--status`) or operate on a temp path.

**Warning signs:** any task that calls `save_progress` against the real `PROGRESS_PATH`.

### Pitfall 4: `python -m pipeline.X` is already partially broken — do not "fix" it here

**What goes wrong:** A reviewer notices `from common.frontmatter import …` fails under `python -m pipeline.link_resolver` and "fixes" it by adding `pipeline/__init__.py` + relative imports, which breaks every documented `python pipeline/X.py` invocation.

**Ground truth:** `python -m pipeline.batch_import --status` happens to work today, because the `--status` branch only touches `load_manifest`/`load_progress`/`print_status`. `run_batch()` does a bare `import link_resolver` at line 365 with no `sys.path` bootstrap — under `-m` from repo root that raises `ModuleNotFoundError`. So `-m` is *not* a supported invocation form and never was. [VERIFIED: executed both forms]

**How to avoid:** document `python pipeline/X.py` as the only supported form (it already is, in `PIPELINE.md`). If defensive coverage is wanted, add a 2-line `sys.path.insert(0, str(Path(__file__).parent))` guard to the modified modules — **not** `pipeline/__init__.py`.

### Pitfall 5: The wrong Python interpreter

**What goes wrong:** `which python3` in this workspace resolves to `/mnt/c/Dev/codex-civica/.venv/bin/python3` (in-repo, on NTFS), not the documented `~/.venv-codex`. A harness run under the wrong venv can fail at `import` time (e.g. `google.genai` for `reconcile`) and be misread as a refactor regression.

**How to avoid:** every command in every task uses the absolute path `~/.venv-codex/bin/python`. `STATE.md` Known Constraints already records `~/.venv-codex` as canonical.

**Warning signs:** `ModuleNotFoundError: No module named 'google'` or `'dotenv'` during a characterization run.

### Pitfall 6: `.github/workflows/deploy.yml` deploys on every push to `main`

**What goes wrong:** Trigger is `on: push: branches: [main]` with no path filter [VERIFIED: read `.github/workflows/deploy.yml`]. Every commit — including a pipeline-only refactor commit — runs `npm ci && npm run build` and publishes to `gh-pages`. A commit that accidentally includes mutated law content goes live immediately.

**How to avoid:** work on a branch, or verify `git status --porcelain laws/israel/` is empty immediately before every commit. The refactor itself is site-neutral (no `laws/` or `site/` file changes), so a clean pipeline-only commit will produce an identical rebuild.

### Pitfall 7: `reconcile.py`'s stale `requirements.txt`

**What goes wrong:** `pipeline/requirements.txt` lists neither `python-dotenv` nor `google-genai`, yet `reconcile.py` imports both at module top level. Anyone provisioning a fresh env from `requirements.txt` cannot import `reconcile` — and the frontmatter characterization harness imports `reconcile`.

**How to avoid:** run harnesses in the existing `~/.venv-codex` (where both are installed). Do **not** update `requirements.txt` in this phase — it is a real but out-of-scope defect; note it for a follow-up. [VERIFIED: `requirements.txt` read + `pip list` compared]

### Pitfall 8: `cross_linker._split_frontmatter` has a leading underscore and a different call-site name

**What goes wrong:** Deleting the local definition and adding `from common.frontmatter import split_frontmatter` leaves `cross_link_one` (line 217) calling the now-undefined `_split_frontmatter`, producing a `NameError` only at runtime — and `cross_link_one` requires a Gemini client, so the failure surfaces late.

**How to avoid:** import with an alias — `from common.frontmatter import split_frontmatter as _split_frontmatter` — so the call site is untouched (smallest possible diff). Add an import-time smoke check: `python -c "import sys; sys.path.insert(0,'pipeline'); import cross_linker; print(cross_linker._split_frontmatter('---\na\n---\nb'))"`.

### Pitfall 9: `build_frontmatter`'s embedded `---` fences

**What goes wrong:** `reconcile.py:134` starts `lines` with `"---"` and `:176-183` appends `"---"` and `""`. Delegating to `render_frontmatter(lines)` without removing those three entries emits doubled fences on all 111 laws.

**How to avoid:** the frontmatter SHA gate catches this immediately. Run it after the edit, before committing.

### Pitfall 10: `generated_at` makes `build_frontmatter` non-deterministic

**What goes wrong:** `build_frontmatter` calls `dt.datetime.now(dt.timezone.utc)`, so two consecutive runs differ. A naive characterization test reports a false regression.

**How to avoid:** monkeypatch the module's `dt` in the harness (prototyped and working — see Code Examples). Do not change production code.

---

## Code Examples

### Verify the two frontmatter splitters are truly interchangeable (run BEFORE deleting either)

```python
# Source: prototyped and executed in this session — result: 112 files, 0 mismatches
import sys
from pathlib import Path
sys.path.insert(0, 'pipeline')
import link_resolver as lr, cross_linker as cl

bad = 0
files = sorted(Path('laws/israel').glob('*.md'))
for p in files:
    t = p.read_text(encoding='utf-8')
    if lr.split_frontmatter(t) != cl._split_frontmatter(t):
        bad += 1
        print("DIFF", p.name)
for case in ["", "no frontmatter", "---\nx: 1\n---\nbody",
             "---\nx: 1\n---\n\nbody", "---\nonly-open\n", "---\n---\n"]:
    assert lr.split_frontmatter(case) == cl._split_frontmatter(case), repr(case)
print(f"checked {len(files)} files, mismatches={bad}")
```

Also verified structurally: `ast.dump(ast.parse(ast.unparse(fn)))` for both functions (normalised for the name difference) compares **equal** — they are the same function, not merely similar.

### Capture / verify the frontmatter fingerprint (no API calls, frozen clock)

```python
# Source: prototyped and executed in this session
# BEFORE-refactor result: entries=111  sha256=dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37
import sys, json, hashlib, datetime as dt
sys.path.insert(0, 'pipeline')
import reconcile

_real = reconcile.dt.datetime
class _Shim:                       # freeze generated_at without touching production code
    timezone = dt.timezone
    class datetime:
        @staticmethod
        def now(tz=None): return _real(2000, 1, 1, tzinfo=dt.timezone.utc)
reconcile.dt = _Shim

man  = json.load(open('data/raw/israel/manifest_laws.json'))
prog = json.load(open('data/raw/israel/import_progress.json'))
done = {str(x) for x in prog['done']}
out  = {str(e.get('law_id') or e.get('bill_id')): reconcile.build_frontmatter(e)
        for e in man if str(e.get('law_id') or e.get('bill_id')) in done}

blob = json.dumps(out, ensure_ascii=False, sort_keys=True)
print("entries:", len(out), "sha256:", hashlib.sha256(blob.encode()).hexdigest())
# capture mode: Path('pipeline/tests/golden/frontmatter_111.json').write_text(blob, encoding='utf-8')
# verify mode : assert blob == Path('pipeline/tests/golden/frontmatter_111.json').read_text(encoding='utf-8')
```

### Capture / verify the batch-selection fingerprint

```python
# Source: prototyped and executed in this session
# BEFORE-refactor: count=1 sha=0b9e40e316c044d1 | count=5 sha=20f03642a354d5cd
#                  count=25 sha=ea819da6b1647539 | count=100 sha=50e6737b1a7a24d2
#                  first three IDs at every count >= 5: ['2001111', '2001108', '2001070']
import sys, hashlib
sys.path.insert(0, 'pipeline')
import batch_import as bi

man, prog = bi.load_manifest(), bi.load_progress()
for c in (1, 5, 25, 100):
    ids = [str(e.get('law_id') or e.get('bill_id')) for e in bi.get_next_batch(man, prog, c)]
    print(c, len(ids), hashlib.sha256(','.join(ids).encode()).hexdigest()[:16])
```

### Progress round-trip byte-fidelity check

```python
# Source: prototyped and executed in this session — result: byte-identical, 1867 bytes,
#         file ends with '}' and NO trailing newline
import json, io
orig = open('data/raw/israel/import_progress.json', 'rb').read()
buf = io.StringIO(); json.dump(json.loads(orig.decode()), buf, ensure_ascii=False, indent=2)
assert orig == buf.getvalue().encode('utf-8')
```

### The link-resolver differential gate (shell)

```bash
set -euo pipefail
PY=~/.venv-codex/bin/python
cd /mnt/c/Dev/codex-civica

# --- capture BEFORE (Wave 0, once, pre-refactor) ---
git checkout -- laws/israel/
find pipeline -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
$PY pipeline/link_resolver.py --all >/dev/null
git diff laws/israel/ > pipeline/tests/golden/link_resolver_all.diff
git checkout -- laws/israel/
test -z "$(git status --porcelain laws/israel/)"    # tree restored

# --- verify AFTER (every extraction step) ---
git checkout -- laws/israel/
find pipeline -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
$PY pipeline/link_resolver.py --all >/dev/null
git diff laws/israel/ > /tmp/after.diff
git checkout -- laws/israel/
diff pipeline/tests/golden/link_resolver_all.diff /tmp/after.diff   # MUST be empty
test -z "$(git status --porcelain laws/israel/)"                    # criterion 2, literally
```

### Status-output gate (criterion 3)

```bash
# BEFORE-refactor output, captured this session — must be reproduced exactly:
#   Total laws:      1076
#   With PDF:        718
#   Converted:       111
#   Failed:          0
#   Pending:         607
#   Total deployed:  111
~/.venv-codex/bin/python pipeline/batch_import.py --status > /tmp/status_after.txt
diff pipeline/tests/golden/status.txt /tmp/status_after.txt   # MUST be empty
```

---

## Verified Extraction Targets

Every location from `ARCHITECTURE.md:96-105` was re-read against the current working tree. **All line numbers are still accurate.**

| Current location | Symbol | Lines (verified) | Destination | Risk |
|---|---|---|---|---|
| `pipeline/link_resolver.py` | `split_frontmatter` | 27-36 (called at 216) | `common/frontmatter.py` | **None** — AST-identical duplicate |
| `pipeline/cross_linker.py` | `_split_frontmatter` | 202-211 (called at 217) | delete; import alias | **None** — same |
| `pipeline/reconcile.py` | `build_frontmatter` (fence-wrapping half only) | 120-184 | `common/frontmatter.py: render_frontmatter` + `quote` | **Highest** — 6 value styles, 111-file blast radius |
| `pipeline/reconcile.py` | `_strip_year` (104-106), `build_seo_description` (109-117) | — | **STAY** — Hebrew-literal-bearing | — |
| `pipeline/batch_import.py` | `load_progress` / `save_progress` | 47-56 | `common/progress.py` | Low — parameterise path |
| `pipeline/batch_import.py` | `get_next_batch` | 255-293 | `common/progress.py` | Low-medium — parameterise `id_keys`, `source_key`; **preserve the `any(e is entry for e in batch)` identity check verbatim** (line 287) |
| `pipeline/batch_import.py` | `print_status` | 296-313 | `common/progress.py` | Low — labels must default to today's exact strings |
| `pipeline/batch_import.py` | `deploy` | 229-248 (called at 417) | `common/deploy.py` | Low — **pass `site_dir` explicitly**; `__file__`-relative derivation changes depth |
| `pipeline/batch_import.py` | `DEPLOY_EVERY` threshold logic | 412-421 | **STAYS** — batch-loop policy | — |
| `pipeline/backfill_seo_meta.py` | `from reconcile import build_seo_description` (line 13) | — | **UNCHANGED** — but re-verify it still imports after the reconcile edit | Low |

**Not duplicated anywhere else:** `grep -rn "split_frontmatter"` across the repo returns exactly the 4 hits above (2 definitions, 2 call sites). `backfill_seo_meta.py` and `backfill_source_links.py` use `re.search` on frontmatter *fields*, not block splitting — leave them alone. `pipeline/_legacy/convert*.py` define their own `build_frontmatter` but are imported by nothing.

---

## Recommended Extraction Sequence

Ordered **lowest-risk-first**, so the highest-risk extraction (`render_frontmatter`) lands last and everything else is already banked if it must be descoped. Each step is one commit and is independently provable — this is what keeps "Israel output unchanged" continuously true instead of only at the end.

**Wave 0 — safety net (no production code touched)**
1. Back up `data/raw/israel/import_progress.json` + `manifest_laws.json` outside the repo; verify copies.
2. Create `pipeline/tests/{capture_golden.py,verify_golden.py}` and `pipeline/tests/golden/`.
3. Run capture → commit `golden/link_resolver_all.diff`, `golden/frontmatter_111.json`, `golden/next_batch.json`, `golden/status.txt`.
4. Assert `git status --porcelain laws/israel/` is empty. **Gate: `verify_golden.py` passes against unmodified source.**

**Wave 1, Step 1 — `split_frontmatter`** *(risk: none)*
Create `common/__init__.py` + `common/frontmatter.py` with `split_frontmatter`. Repoint `link_resolver.py` (plain import) and `cross_linker.py` (aliased import). Delete both local copies.
**Gate:** splitter-equivalence script (112 files, 0 mismatches) + full `verify_golden.py`.

**Wave 1, Step 2 — progress module** *(risk: low)*
Add `common/progress.py` with `load_progress(path)`, `save_progress(path, progress)`, `get_next_batch(manifest, progress, count, id_keys=("law_id","bill_id"), source_key="pdf_path")`, `print_status(manifest, progress, source_label="With PDF")`. Repoint `batch_import.py` (module-level wrappers bound to `PROGRESS_PATH` keep the 12 existing call sites untouched).
**Gate:** `--status` byte-diff + `get_next_batch` SHAs + progress round-trip byte-fidelity + full `verify_golden.py`.

**Wave 1, Step 3 — deploy module** *(risk: low)*
Add `common/deploy.py` with `deploy(site_dir: Path, env_overrides: dict | None = None) -> bool`. `batch_import.deploy()` becomes a thin wrapper passing `SITE_DIR` and `{"USE_SSH": "true", "GIT_USER": "Yuvaldv"}`.
**Gate:** import-time smoke + source-equivalence review. **Never execute `deploy()`.**

**Wave 1, Step 4 — `render_frontmatter`** *(risk: highest)*
Add `render_frontmatter(lines)` + `quote(value)` to `common/frontmatter.py`. `reconcile.build_frontmatter` keeps all field selection/ordering/formatting; drop its embedded `"---"`/`""` entries and return `render_frontmatter(lines)`.
**Gate:** frontmatter SHA must equal `dab1887e06dd074051ed6a2eff2c2fcdabff1a2f523c8a3cc93fd20c7168dd37` + `backfill_seo_meta.py` still imports + full `verify_golden.py`.

**Wave 2 — close out**
Full `verify_golden.py`; confirm `git status --porcelain laws/israel/` empty; update `pipeline/PIPELINE.md` with the `common/` layout and the supported invocation form; note the two out-of-scope defects (Class-B idempotency bug; stale `requirements.txt`) in `STATE.md` Todos.

**Criterion 4 ("a new country package can read/write frontmatter and progress without copying Israel-specific code") is proven, not asserted,** by a throwaway probe committed as `pipeline/tests/test_country_blind.py`: create a temp dir, `save_progress(tmp/p.json, {...})`, `load_progress` it back, call `get_next_batch` over a synthetic non-Israel manifest using `id_keys=("doc_id",)`, `source_key="xml_path"`, and `render_frontmatter([...])` with UK-shaped fields — importing **only** from `common`, never from `reconcile`/`batch_import`/`link_resolver`/`cross_linker`. Enforce the boundary with a static assertion: no `common/*.py` may contain an import of any Israel module.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `git diff --stat` vs `HEAD` as the refactor gate (`ARCHITECTURE.md:422-424`) | Before/after diff-fingerprint differential | This research (2026-08-09) | The prescribed gate is unachievable today; the differential is achievable and strictly stronger |
| `pipeline/` as a flat bag of scripts with bare cross-imports | Flat scripts **plus** one `common/` subpackage on `sys.path[0]` | Phase 7 | Smallest change that satisfies criterion 4; preserves every documented entry point |

**Deprecated / outdated in this repo:**
- `pipeline/_legacy/convert*.py` — four superseded converters, imported by nothing. Leave untouched; do not "consolidate" their `build_frontmatter` copies into `common/`.
- `pipeline/requirements.txt` — stale (missing `python-dotenv`, `google-genai`). Out of scope; record as a Todo.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (venv `~/.venv-codex`) | all pipeline modules | ✓ | 3.12.3 | — |
| `google-genai` | `reconcile` module import (needed by the frontmatter harness) | ✓ | 1.75.0 | — |
| `python-dotenv` | `reconcile` module import | ✓ | 1.2.2 | — |
| `git` | the entire proof mechanism | ✓ | 2.43.0 | none needed |
| `pdftotext` (poppler) | `stage_native` — not exercised in this phase | ✓ | 24.02.0 | — |
| `tesseract` | `stage_ocr` — not exercised in this phase | ✓ | 5.3.4 | — |
| `npm` / `node` | `deploy()` — **must not run** in this phase | ✓ | 10.9.7 / v22.22.2 | — |
| `pytest` | optional characterization runner | ✗ | — | **stdlib scripts (recommended)**; `pip install pytest==9.1.1` works (network verified) |
| `slopcheck` | package legitimacy audit | ✗ | — | manual PyPI check performed; no packages installed |
| `ruff` / `black` / `mypy` | — | ✗ | — | not used by this repo; do not introduce |
| Gemini API (`GEMINI_API_KEY`) | `reconcile_one`, `cross_link_one` — **not needed** for any gate | n/a | — | every proof path is offline |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `pytest` → stdlib characterization scripts (recommended default); `slopcheck` → manual registry check (done).

---

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | **None installed.** Recommend stdlib characterization scripts under `pipeline/tests/`, run directly. `pytest` 9.1.1 is installable if the planner prefers it — see Wave 0 Gaps. |
| Config file | none — see Wave 0 |
| Quick run command | `~/.venv-codex/bin/python pipeline/tests/verify_golden.py --quick` (splitter equivalence + frontmatter SHA + status diff; ~2s, no file mutation) |
| Full suite command | `~/.venv-codex/bin/python pipeline/tests/verify_golden.py` (adds the link-resolver differential; ~5s incl. checkout/restore) |

### Phase Requirements → Test Map

Phase 7 carries no `REQUIREMENTS.md` IDs. Mapping is against the four ROADMAP success criteria.

| Criterion | Behaviour | Test Type | Automated Command | File Exists? |
|-----------|-----------|-----------|-------------------|-------------|
| SC-1 | `common/` exists with split/render, progress, deploy; Israel modules import them | structural | `~/.venv-codex/bin/python pipeline/tests/verify_golden.py --structure` (asserts `common/{frontmatter,progress,deploy}.py` exist; asserts `split_frontmatter`/`_split_frontmatter`/`load_progress`/`def deploy` no longer *defined* in the Israel modules) | ❌ Wave 0 |
| SC-2a | Pipeline output over `laws/israel/` byte-identical before vs after | golden differential | `diff pipeline/tests/golden/link_resolver_all.diff /tmp/after.diff` | ❌ Wave 0 |
| SC-2b | Committed Israel content untouched | smoke | `test -z "$(git status --porcelain laws/israel/)"` | ✓ (git) |
| SC-2c | `build_frontmatter` output byte-identical for all 111 laws | golden hash | `verify_golden.py --frontmatter` (expect `dab1887e…`) | ❌ Wave 0 |
| SC-2d | `split_frontmatter` behaviour identical to both originals | differential over corpus | `verify_golden.py --split` (112 files + 6 edge cases) | ❌ Wave 0 |
| SC-3 | `--status` reports 1076 / 718 / 111 / 0 / 607 / 111 | golden stdout | `diff pipeline/tests/golden/status.txt <(… --status)` | ❌ Wave 0 |
| SC-3b | `get_next_batch` selection unchanged | golden hash | `verify_golden.py --batch` (4 counts) | ❌ Wave 0 |
| SC-3c | `save_progress` writes byte-identical JSON | round-trip | `verify_golden.py --progress-roundtrip` | ❌ Wave 0 |
| SC-4 | A non-Israel caller can use `common` alone | integration | `~/.venv-codex/bin/python pipeline/tests/test_country_blind.py` | ❌ Wave 0 |
| SC-4b | `common/` imports nothing Israel-specific | static | `! grep -rnE "^\s*(from\|import) (reconcile\|batch_import\|link_resolver\|cross_linker)" pipeline/common/` | ❌ Wave 0 |
| — | `deploy()` never executes | manual-only | reviewer confirms no task invokes it (justified: executing it publishes to production) | n/a |

### Sampling Rate

- **Per task commit:** `verify_golden.py --quick` (no file mutation, ~2s)
- **Per wave merge:** `verify_golden.py` (full, incl. link-resolver differential + `git status` assertion)
- **Phase gate:** full suite green **and** `git status --porcelain laws/israel/` empty, before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `pipeline/tests/capture_golden.py` — captures all four BEFORE fingerprints
- [ ] `pipeline/tests/verify_golden.py` — re-runs and diffs; supports `--quick`, `--structure`, `--split`, `--frontmatter`, `--batch`, `--progress-roundtrip`
- [ ] `pipeline/tests/golden/{link_resolver_all.diff,frontmatter_111.json,next_batch.json,status.txt}` — committed fixtures
- [ ] `pipeline/tests/test_country_blind.py` — SC-4 proof
- [ ] Off-repo backup of `data/raw/israel/{import_progress.json,manifest_laws.json}`
- [ ] Framework install: **not required** (stdlib). Optional: `~/.venv-codex/bin/python -m pip install pytest==9.1.1`

---

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json` (absent = enabled). This is an internal, offline, single-user code-organisation refactor with no network surface, no untrusted input, and no new dependency — most ASVS categories are inapplicable.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface; static site + local scripts |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No multi-user surface |
| V5 Input Validation | **partially** | Inputs are local trusted JSON/Markdown. `json.load` (no `pickle`/`eval`) is already correct — preserve it verbatim in `common/progress.py` |
| V6 Cryptography | no | None used or added. `hashlib.sha256` in the harness is a change-detection digest, not a security control |
| V7 Error Handling & Logging | **yes** | `deploy()` injects `GIT_USER=Yuvaldv` into a subprocess env with `capture_output=False`. Verify the extracted version does not begin logging the env dict |
| V12 Files & Resources | **yes** | All paths must stay explicit; no user-controlled path joins introduced |
| V14 Configuration | **yes** | `pipeline/.env` (`GEMINI_API_KEY`) stays gitignored; `common/` must never read or log it |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leakage via a newly-created shared module | Information disclosure | `common/` reads no `.env`, holds no credential, logs no env dict. Add a `grep -rn "GEMINI_API_KEY\|GIT_USER" pipeline/common/` assertion returning only the deliberate `deploy` default |
| Accidental publication of corrupted content | Tampering (integrity) | Auto-deploy on push to `main`; enforced by the `git status --porcelain laws/israel/` gate before every commit |
| Command injection via `subprocess` | Tampering | `deploy()` already uses list-form `subprocess.run` with no `shell=True` — preserve exactly; never interpolate a caller-supplied string into the arg list |
| Unrecoverable state loss | Denial of service | `import_progress.json` is gitignored; Wave 0 off-repo backup is the mitigation |
| Dependency-confusion / slopsquatting | Tampering | Zero new runtime dependencies. `pytest` deferred |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pytest` 9.1.1 is the legitimate pytest-dev package | Standard Stack / Package Audit | Low — recommendation is to *not* install it. slopcheck was unavailable, so this is `[ASSUMED]` per protocol despite `pip index versions` confirming it |
| A2 | `python pipeline/X.py` is the only invocation form used by any human, script, or scheduled job | Architecture Patterns, Pitfall 4 | Medium — if some undiscovered caller uses `-m`, plain `common.*` imports break it. Mitigated: crontab/systemd/CI audited and clean; CI runs only `npm`, never Python |
| A3 | The Class-B non-idempotency (`2000326`/`2000390`/`2000416`/`2000595`) is entirely pre-existing and unrelated to the refactor | Pitfall 1 | Low — proven by reproducing it on a clean `HEAD` before any code change; the differential gate is immune to it either way |
| A4 | `laws/israel/index.md` is a hand-maintained index, not pipeline output | Runtime State Inventory | Low — `link_resolver.main()` explicitly skips `index`/`_index`/`placeholder`; the 112th file is `index.md` and no run touched it |
| A5 | Israel and UK will want the *same* `---`-fenced frontmatter block shape, making `render_frontmatter` genuinely shared rather than Israel-shaped | Pattern 2, criterion SC-1 | Medium — if Phase 9's UK renderer needs a different shape, `render_frontmatter` becomes a two-line function of near-zero value. Deliberately kept thin so that outcome costs nothing |
| A6 | `total_deployed: 111` reflects a real completed deploy rather than drift | Runtime State Inventory | Low — cosmetic; no gate depends on its semantics, only on its byte-stability |

---

## Open Questions (RESOLVED)

1. **RESOLVED (user decision, 2026-08-09): defer.** Should Phase 7 fix the Class-B idempotency bug?
   - What we know: it is reproducible, isolated to `link_resolver._STRIP_MG_INDEX` (lines 122-124) interacting with Pass 2's re-linkification of previously-emitted Sidenotes bullets, and it corrupts 4 law files a little more on every run.
   - What's unclear: whether the user wants it fixed now (it is live-site-visible content corruption on 4 pages) or tracked as v1.0 content work.
   - **Recommendation:** **do not fix it in Phase 7.** Fixing it changes `laws/israel/` content, which destroys the only property that makes this refactor verifiable. Add it to `STATE.md` Todos and to the v1.0 Phase 4 track. If the user wants it fixed first, do it as a **separate commit landed before Wave 0**, then re-capture the golden fingerprints.

2. **RESOLVED (planner, per research recommendation): extract now, land last.** Is `render_frontmatter` worth extracting now, or should it wait for Phase 9?
   - What we know: success criterion 1 names it explicitly; it is also the highest-risk extraction (111-file blast radius, 6 value styles) and the only one with no existing duplication to justify it.
   - What's unclear: the UK frontmatter field list is not frozen until Phase 9 (`ARCHITECTURE.md` build order, Phase 3 step 2).
   - **Recommendation:** extract it, but keep it deliberately thin (fence-wrapping + `quote()` only) and land it **last**, so a descope decision costs nothing already banked.

3. **RESOLVED (planner, per research recommendation): exact 6-line stdout is the golden fixture.** `--status` reports `Pending: 607` — is that the number the criterion means?
   - What we know: criterion 3 says "111/718 converted, 0 failed"; actual output is `Total laws: 1076 / With PDF: 718 / Converted: 111 / Failed: 0 / Pending: 607 / Total deployed: 111` (718 − 111 = 607 ✓, internally consistent).
   - **Recommendation:** treat the *exact 6-line stdout* as the golden fixture rather than paraphrasing individual numbers — that is both stricter and unambiguous.

---

## Sources

### Primary (HIGH confidence)
- **Direct execution of the repository's own code, this session** — the strongest available source for every structural and behavioural claim:
  - `link_resolver.py --all` run 4× from clean `HEAD` (non-idempotency + determinism proof)
  - `ast.parse`/`ast.dump` comparison of the two `split_frontmatter` implementations
  - differential execution of both splitters over all 112 `laws/israel/*.md` + 6 edge cases
  - `build_frontmatter` over all 111 converted manifest entries with a frozen clock
  - `get_next_batch` at counts 1/5/25/100
  - `save_progress` JSON round-trip byte comparison
  - `batch_import.py --status`
  - `/tmp/proto/` import-mechanics probe across 4 invocation modes
  - `crontab -l`, `~/.config/systemd/user/`, `git check-ignore -v`, `.github/workflows/deploy.yml`, `site/package.json` scripts, `find … -name __init__.py`, tool `--version` sweep
- `docs.python.org/3/library/sys_path_init.html` — `sys.path[0]` initialisation rules for script vs `-m` execution
- `/mnt/c/Dev/codex-civica/CLAUDE.md` — project constraints
- `/mnt/c/Dev/codex-civica/.planning/{REQUIREMENTS,ROADMAP,STATE}.md`
- `/mnt/c/Dev/codex-civica/.planning/research/ARCHITECTURE.md:96-115, 360-424` — milestone extraction targets and build order (line references independently re-verified against current source)

### Secondary (MEDIUM confidence)
- `pip index versions pytest` → 9.1.1 (registry existence confirmed; `[ASSUMED]` per package-provenance rule because slopcheck was unavailable)

### Tertiary (LOW confidence)
- None. No claim in this document rests on unverified web search.

---

## Metadata

**Confidence breakdown:**
- Extraction targets & line numbers: **HIGH** — every location re-read in the current working tree; all `ARCHITECTURE.md` references confirmed accurate
- Splitter-duplication claim: **HIGH** — AST-identical *and* differentially executed over the full corpus
- Non-idempotency blocker: **HIGH** — reproduced 4× with a minimal regex-level repro isolating the root cause
- Import mechanics: **HIGH** — empirically probed across 4 invocation modes and corroborated by official Python docs
- Extraction sequence & gate design: **MEDIUM-HIGH** — every gate was prototyped and produced a concrete fingerprint; sequencing is a judgement call
- `render_frontmatter` shape: **MEDIUM** — byte-fidelity requirement is verified; the *right* API shape depends on a UK field list not frozen until Phase 9 (see A5)
- Runtime state inventory: **HIGH** — all five categories probed with commands, negative results stated explicitly
- Security domain: **MEDIUM** — assessment is inapplicability-driven; no ASVS tooling was run (none warranted for an offline refactor)

**Research date:** 2026-08-09
**Valid until:** 2026-09-08 (30 days — stable, stdlib-only, no fast-moving dependencies). **Invalidated early by:** any commit touching `laws/israel/`, `pipeline/link_resolver.py`, `pipeline/reconcile.py`, or `data/raw/israel/import_progress.json` — all four golden fingerprints must then be re-captured.
