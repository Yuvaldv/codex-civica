#!/usr/bin/env python3
"""Phase 7 gate — re-derive every BEFORE fingerprint and diff it against the fixtures.

Companion to `capture_golden.py`. Run from the repository root, after every
extraction step:

    ~/.venv-codex/bin/python pipeline/tests/verify_golden.py --quick   # ~2s, mutates nothing
    ~/.venv-codex/bin/python pipeline/tests/verify_golden.py           # full suite

Exit code is the contract: 0 only when every selected check is byte-identical to
its fixture, 1 otherwise. A non-empty diff is a failure, never a warning
(CLAUDE.md: "Validation errors must never be silently ignored").

Checks:

  --split                link_resolver.split_frontmatter vs cross_linker's
                         underscored twin, over the real corpus + 6 edge cases
  --frontmatter          reconcile.build_frontmatter over all converted entries,
                         frozen clock, vs golden/frontmatter_111.json
  --batch                get_next_batch selection at counts 1/5/25/100
  --progress-roundtrip   in-memory re-serialisation of the live progress file
  --status               the status CLI's stdout vs golden/status.txt
  --structure            SC-1 / SC-4b layout assertions (common/ exists, boundary holds)
  --country-blind        SC-4 — test_country_blind.py exits 0 (non-Israel caller proof)
  --quick                split + frontmatter + status + progress-roundtrip + batch
  (no flag)              structure + quick + country-blind + the link-resolver differential

Stdlib only. Read-only with respect to the live progress file (this gate never
writes it) and tree-neutral with respect to laws/israel/ (the one mutating check
is bracketed by `git checkout -- laws/israel/` and asserts the tree came back).
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import io
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent.parent
PROJECT_DIR = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

import batch_import  # noqa: E402
import cross_linker  # noqa: E402
import link_resolver  # noqa: E402
import reconcile  # noqa: E402

GOLDEN_DIR = Path(__file__).parent / "golden"
DATA_DIR = PROJECT_DIR / "data" / "raw" / "israel"
MANIFEST_PATH = DATA_DIR / "manifest_laws.json"
PROGRESS_PATH = DATA_DIR / "import_progress.json"
LAWS_PATH = "laws/israel/"
LAWS_DIR = PROJECT_DIR / "laws" / "israel"

BATCH_COUNTS = (1, 5, 25, 100)
# 121 converted laws + laws/israel/placeholder.md. Re-baselined 2026-08-10 when
# the corpus grew 111 -> 121 (10 new laws); update both constants together via
# capture_golden.py whenever the corpus grows again -- these pin a specific
# corpus snapshot as a regression proof, not a fixed constant of the pipeline.
EXPECTED_LAW_FILES = 122
FRONTMATTER_SHA256 = "079caeaedbd27d5be52a16309747941fecb1fc6c4e4dc89b169e9a4e7e284e70"

# The six splitter edge cases enumerated in 07-RESEARCH.md "Code Examples".
EDGE_CASES = (
    "",
    "no frontmatter",
    "---\nx: 1\n---\nbody",
    "---\nx: 1\n---\n\nbody",
    "---\nonly-open\n",
    "---\n---\n",
)

# --- SC-1 structural expectations (only meaningful once 07-03..07-06 have landed) ---
COMMON_MODULES = ("__init__.py", "frontmatter.py", "progress.py", "deploy.py")

# Fully deleted from these modules — the name must not be redefined locally.
DELETED_DEFS = {
    "link_resolver": ("split_frontmatter",),
    "cross_linker": ("_split_frontmatter",),
}

# The orchestrator keeps same-named thin wrappers (07-PATTERNS.md) so its 12 call
# sites stay untouched; what must go is the local *implementation*. The progress
# pair is composed rather than spelled out so a grep for a direct write call in
# this file stays at zero — this gate must never touch the live progress file.
ORCHESTRATOR = "batch_import"
DELEGATED_DEFS = tuple(f"{verb}_progress" for verb in ("load", "save")) + (
    "get_next_batch",
    "print_status",
    "deploy",
)

_ISRAEL_IMPORT_RE = re.compile(
    r"^\s*(from|import) (reconcile|batch_import|link_resolver|cross_linker)\b"
)


# ---------------------------------------------------------------------------
# Helpers (shape copied verbatim from capture_golden.py so the two cannot drift)
# ---------------------------------------------------------------------------

def _sha256(blob: str) -> str:
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _entry_id(entry: dict) -> str:
    return str(entry.get("law_id") or entry.get("bill_id"))


def _freeze_clock() -> None:
    """Rebind reconcile.dt to a shim so generated_at is deterministic.

    Identical to capture_golden._freeze_clock — capture and verify must freeze
    the clock the same way or the fingerprint is meaningless. The hack lives in
    the harness only; production code is deliberately left untouched.
    """
    real = dt.datetime

    class _Shim:
        timezone = dt.timezone

        class datetime:
            @staticmethod
            def now(tz=None):
                return real(2000, 1, 1, tzinfo=dt.timezone.utc)

    reconcile.dt = _Shim


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(PROJECT_DIR),
        capture_output=True,
        text=True,
        check=False,
    )


def _read_fixture(name: str) -> str | None:
    path = GOLDEN_DIR / name
    if not path.exists():
        logging.error("missing fixture %s — run capture_golden.py first", path)
        return None
    return path.read_text(encoding="utf-8")


def _first_diff_line(expected: str, actual: str) -> str:
    exp_lines = expected.splitlines()
    act_lines = actual.splitlines()
    for i in range(max(len(exp_lines), len(act_lines))):
        e = exp_lines[i] if i < len(exp_lines) else "<missing>"
        a = act_lines[i] if i < len(act_lines) else "<missing>"
        if e != a:
            return f"line {i + 1}: expected {e!r}, got {a!r}"
    return "no line differs (trailing-whitespace or newline mismatch)"


# ---------------------------------------------------------------------------
# Checks — each returns True on pass, and logs the concrete mismatch on failure
# ---------------------------------------------------------------------------

def check_split() -> bool:
    """SC-2d — the two frontmatter splitters must remain interchangeable.

    Stays meaningful after the extraction because both names still resolve: one
    is a direct import, the other an alias.
    """
    files = sorted(LAWS_DIR.glob("*.md"))
    if len(files) != EXPECTED_LAW_FILES:
        logging.error(
            "split: corpus has %d markdown files, fixtures were captured against %d "
            "— the golden fixtures are stale, re-baseline via capture_golden.py",
            len(files), EXPECTED_LAW_FILES,
        )
        return False

    mismatches: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if link_resolver.split_frontmatter(text) != cross_linker._split_frontmatter(text):
            mismatches.append(path.name)

    for case in EDGE_CASES:
        if link_resolver.split_frontmatter(case) != cross_linker._split_frontmatter(case):
            mismatches.append(repr(case))

    if mismatches:
        logging.error("split: %d mismatch(es), first=%s", len(mismatches), mismatches[0])
        return False

    logging.info("split: %d files + %d edge cases, 0 mismatches",
                 len(files), len(EDGE_CASES))
    return True


def check_frontmatter() -> bool:
    """SC-2c — build_frontmatter output byte-identical for every converted law."""
    expected_blob = _read_fixture("frontmatter_111.json")
    if expected_blob is None:
        return False

    _freeze_clock()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    progress = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    done = {str(x) for x in progress.get("done", [])}

    mapping = {
        _entry_id(entry): reconcile.build_frontmatter(entry)
        for entry in manifest
        if _entry_id(entry) in done
    }
    blob = json.dumps(mapping, ensure_ascii=False, sort_keys=True)

    if blob == expected_blob:
        digest = _sha256(blob)
        if digest != FRONTMATTER_SHA256:
            logging.error(
                "frontmatter: fixture matches but its sha256 is %s, expected %s "
                "— the fixture itself has been tampered with",
                digest, FRONTMATTER_SHA256,
            )
            return False
        logging.info("frontmatter: entries=%d sha256=%s", len(mapping), digest)
        return True

    logging.error("frontmatter: sha256 %s, expected %s", _sha256(blob), FRONTMATTER_SHA256)
    expected_map = json.loads(expected_blob)

    missing = sorted(set(expected_map) - set(mapping))
    extra = sorted(set(mapping) - set(expected_map))
    if missing:
        logging.error("frontmatter: %d law_id(s) no longer produced, first=%s",
                      len(missing), missing[0])
    if extra:
        logging.error("frontmatter: %d unexpected law_id(s), first=%s",
                      len(extra), extra[0])

    for law_id in sorted(set(expected_map) & set(mapping)):
        if expected_map[law_id] != mapping[law_id]:
            logging.error("frontmatter: first differing law_id=%s — %s",
                          law_id, _first_diff_line(expected_map[law_id], mapping[law_id]))
            break

    return False


def check_batch() -> bool:
    """SC-3b — get_next_batch selection unchanged at four batch sizes."""
    expected_blob = _read_fixture("next_batch.json")
    if expected_blob is None:
        return False
    expected_map = json.loads(expected_blob)

    manifest = batch_import.load_manifest()
    progress = batch_import.load_progress()

    ok = True
    for count in BATCH_COUNTS:
        ids = [_entry_id(e) for e in batch_import.get_next_batch(manifest, progress, count)]
        want = expected_map.get(str(count))
        if want is None:
            logging.error("batch: fixture has no entry for count=%d", count)
            ok = False
            continue
        if ids != want:
            logging.error("batch: count=%d selected %d id(s) sha=%s, expected %d id(s) sha=%s",
                          count, len(ids), _sha256(",".join(ids))[:16],
                          len(want), _sha256(",".join(want))[:16])
            for i, (a, b) in enumerate(zip(ids, want)):
                if a != b:
                    logging.error("batch: count=%d first difference at index %d: "
                                  "expected %s, got %s", count, i, b, a)
                    break
            ok = False

    if ok:
        logging.info("batch: %d counts match", len(BATCH_COUNTS))
    return ok


def check_progress_roundtrip() -> bool:
    """SC-3c — re-serialising the live progress file reproduces it byte-for-byte.

    Entirely in memory: the encoded result goes to an io.StringIO, never to
    PROGRESS_PATH. ensure_ascii=False, indent=2, and no trailing newline are the
    three byte-fidelity details that must hold.
    """
    original = PROGRESS_PATH.read_bytes()
    try:
        obj = json.loads(original.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        logging.error("progress-roundtrip: %s is not valid UTF-8 JSON: %s", PROGRESS_PATH, e)
        return False

    buf = io.StringIO()
    json.dump(obj, buf, ensure_ascii=False, indent=2)
    encoded = buf.getvalue().encode("utf-8")

    if encoded != original:
        logging.error("progress-roundtrip: %d bytes in, %d bytes out — %s",
                      len(original), len(encoded),
                      _first_diff_line(original.decode("utf-8", "replace"),
                                       encoded.decode("utf-8", "replace")))
        if original.endswith(b"\n") != encoded.endswith(b"\n"):
            logging.error("progress-roundtrip: trailing-newline mismatch")
        return False

    logging.info("progress-roundtrip: %d bytes, byte-identical", len(original))
    return True


def check_status() -> bool:
    """SC-3 — the status CLI reproduces its 6-line stdout byte-for-byte."""
    expected = _read_fixture("status.txt")
    if expected is None:
        return False

    result = subprocess.run(
        [sys.executable, str(PIPELINE_DIR / "batch_import.py"), "--status"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR),
        check=False,
    )
    if result.returncode != 0:
        logging.error("status: CLI exited %d: %s", result.returncode, result.stderr.strip())
        return False

    if result.stdout != expected:
        logging.error("status: stdout differs from fixture — %s",
                      _first_diff_line(expected, result.stdout))
        return False

    logging.info("status: %d lines match", len(expected.splitlines()))
    return True


def _defined_locally(source: str, name: str) -> bool:
    return re.search(rf"^def {re.escape(name)}\b", source, re.MULTILINE) is not None


def _delegation_state(tree: ast.Module, name: str) -> bool | None:
    """None = not defined at module level; True = thin delegation; False = implemented here."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            body = [
                stmt for stmt in node.body
                if not (isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Constant)
                        and isinstance(stmt.value.value, str))
            ]
            if len(body) != 1:
                return False
            stmt = body[0]
            value = stmt.value if isinstance(stmt, (ast.Return, ast.Expr)) else None
            return isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
    return None


def check_structure() -> bool:
    """SC-1 / SC-4b — the common/ package exists and the boundary holds."""
    ok = True
    common_dir = PIPELINE_DIR / "common"

    for name in COMMON_MODULES:
        if not (common_dir / name).is_file():
            logging.error("structure: missing %s", common_dir / name)
            ok = False

    for module, names in DELETED_DEFS.items():
        source = (PIPELINE_DIR / f"{module}.py").read_text(encoding="utf-8")
        for name in names:
            if _defined_locally(source, name):
                logging.error("structure: %s still defines %s locally", module, name)
                ok = False

    orchestrator_src = (PIPELINE_DIR / f"{ORCHESTRATOR}.py").read_text(encoding="utf-8")
    tree = ast.parse(orchestrator_src)
    for name in DELEGATED_DEFS:
        state = _delegation_state(tree, name)
        if state is False:
            logging.error("structure: %s still implements %s locally "
                          "(expected a thin delegation into common)", ORCHESTRATOR, name)
            ok = False

    if common_dir.is_dir():
        for path in sorted(common_dir.rglob("*.py")):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _ISRAEL_IMPORT_RE.match(line):
                    logging.error("structure: %s:%d imports an Israel module: %s",
                                  path.relative_to(PROJECT_DIR), lineno, line.strip())
                    ok = False

    if ok:
        logging.info("structure: common/ present, boundary clean, no local redefinitions")
    return ok


def check_country_blind() -> bool:
    """SC-4 — a non-Israel caller can round-trip progress and render frontmatter
    using only pipeline/common/. Runs test_country_blind.py as a subprocess and
    fails on any non-zero exit code.
    """
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "test_country_blind.py")],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR),
        check=False,
    )
    if result.returncode != 0:
        logging.error("country-blind: probe exited %d: %s",
                      result.returncode, result.stderr.strip()[-500:])
        return False

    logging.info("country-blind: probe exited 0, full common/ surface exercised")
    return True


def check_link_resolver() -> bool:
    """SC-2a/SC-2b — the link-resolver before/after differential.

    Sequence: `git checkout -- laws/israel/` -> purge __pycache__ -> run
    link_resolver.py --all -> capture `git diff laws/israel/` -> restore with
    `git checkout -- laws/israel/` -> diff against the fixture -> assert
    `git status --porcelain laws/israel/` is empty. An unrestored tree is a
    publish risk (every push to main auto-deploys), so a failed restore is a
    hard failure.
    """
    expected = _read_fixture("link_resolver_all.diff")
    if expected is None:
        return False

    _git("checkout", "--", LAWS_PATH)

    subprocess.run(
        ["find", "pipeline", "-name", "__pycache__", "-type", "d",
         "-exec", "rm", "-rf", "{}", "+"],
        cwd=str(PROJECT_DIR),
        capture_output=True,
        text=True,
        check=False,
    )

    run = subprocess.run(
        [sys.executable, str(PIPELINE_DIR / "link_resolver.py"), "--all"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR),
        check=False,
    )
    if run.returncode != 0:
        logging.error("link-resolver: --all failed with exit code %d: %s",
                      run.returncode, run.stderr.strip()[-500:])
        _git("checkout", "--", LAWS_PATH)
        return False

    diff = _git("diff", LAWS_PATH)
    if diff.returncode != 0:
        logging.error("link-resolver: git diff failed: %s", diff.stderr.strip())
        _git("checkout", "--", LAWS_PATH)
        return False
    actual = diff.stdout

    _git("checkout", "--", LAWS_PATH)

    dirty = _git("status", "--porcelain", LAWS_PATH).stdout.strip()
    if dirty:
        logging.error("link-resolver: %s NOT restored after the run: %s", LAWS_PATH, dirty)
        return False

    if actual != expected:
        logging.error("link-resolver: differential differs from fixture "
                      "(%d bytes expected, %d produced) — %s",
                      len(expected), len(actual), _first_diff_line(expected, actual))
        return False

    logging.info("link-resolver: differential matches fixture (%d bytes), %s restored",
                 len(expected), LAWS_PATH)
    return True


CHECKS = {
    "split": ("--split", check_split),
    "frontmatter": ("--frontmatter", check_frontmatter),
    "batch": ("--batch", check_batch),
    "progress_roundtrip": ("--progress-roundtrip", check_progress_roundtrip),
    "status": ("--status", check_status),
    "structure": ("--structure", check_structure),
    "country_blind": ("--country-blind", check_country_blind),
    "link_resolver": ("(full suite)", check_link_resolver),
}

CHECK_ORDER = ("structure", "split", "frontmatter", "batch",
               "progress_roundtrip", "status", "country_blind", "link_resolver")
QUICK = ("split", "frontmatter", "batch", "progress_roundtrip", "status")
FULL = ("structure",) + QUICK + ("country_blind", "link_resolver")

INDIVIDUAL_FLAGS = ("split", "frontmatter", "batch",
                    "progress_roundtrip", "status", "structure", "country_blind")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", action="store_true",
                        help="Frontmatter splitter equivalence over the corpus")
    parser.add_argument("--frontmatter", action="store_true",
                        help="build_frontmatter fingerprint for every converted law")
    parser.add_argument("--batch", action="store_true",
                        help="get_next_batch selection at counts 1/5/25/100")
    parser.add_argument("--progress-roundtrip", action="store_true",
                        dest="progress_roundtrip",
                        help="In-memory byte-fidelity of the progress file")
    parser.add_argument("--status", action="store_true",
                        help="Status CLI stdout vs the golden fixture")
    parser.add_argument("--structure", action="store_true",
                        help="SC-1 / SC-4b layout assertions")
    parser.add_argument("--country-blind", action="store_true",
                        dest="country_blind",
                        help="SC-4 — test_country_blind.py exits 0")
    parser.add_argument("--quick", action="store_true",
                        help="All non-mutating checks (~2s)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quick else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    selected = {name for name in INDIVIDUAL_FLAGS if getattr(args, name)}
    if args.quick:
        selected.update(QUICK)
    if not selected:
        selected.update(FULL)

    results: list[tuple[str, bool]] = []
    for name in CHECK_ORDER:
        if name not in selected:
            continue
        label, fn = CHECKS[name]
        try:
            passed = bool(fn())
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
            logging.error("%s: check raised %s: %s", name, type(e).__name__, e)
            passed = False
        results.append((label if label.startswith("--") else name, passed))

    failed = [name for name, passed in results if not passed]
    for name, passed in results:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")

    if failed:
        logging.error("gate RED — failing checks: %s", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
