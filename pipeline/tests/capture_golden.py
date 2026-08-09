#!/usr/bin/env python3
"""Capture the four BEFORE fingerprints of current pipeline behaviour.

Wave 0 of Phase 7 (shared pipeline core). Run ONCE, from the repository root,
before any production file is edited:

    ~/.venv-codex/bin/python pipeline/tests/capture_golden.py

Writes four fixtures into pipeline/tests/golden/:

  frontmatter_111.json     reconcile.build_frontmatter() over every converted
                           manifest entry, with a frozen clock
  next_batch.json          get_next_batch() selection at counts 1/5/25/100
  status.txt               verbatim stdout of `batch_import.py --status`
  link_resolver_all.diff   the diff `link_resolver.py --all` produces over
                           laws/israel/ starting from a clean HEAD

Stdlib only — no pytest, no PyYAML, no new dependency. Read-only with respect
to import_progress.json (save_progress is never called) and tree-neutral with
respect to laws/israel/ (every run is bracketed by `git checkout --`).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent.parent
PROJECT_DIR = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

import batch_import  # noqa: E402
import reconcile  # noqa: E402

GOLDEN_DIR = Path(__file__).parent / "golden"
DATA_DIR = PROJECT_DIR / "data" / "raw" / "israel"
MANIFEST_PATH = DATA_DIR / "manifest_laws.json"
PROGRESS_PATH = DATA_DIR / "import_progress.json"
LAWS_PATH = "laws/israel/"

BATCH_COUNTS = (1, 5, 25, 100)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(blob: str) -> str:
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _entry_id(entry: dict) -> str:
    return str(entry.get("law_id") or entry.get("bill_id"))


def _freeze_clock() -> None:
    """Rebind reconcile.dt to a shim so generated_at is deterministic.

    reconcile.build_frontmatter() calls dt.datetime.now(dt.timezone.utc); without
    this every capture would differ. The hack lives in the harness only —
    production code is deliberately left untouched.
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


# ---------------------------------------------------------------------------
# Capture functions
# ---------------------------------------------------------------------------

def capture_frontmatter() -> int:
    """Fingerprint build_frontmatter() over every converted manifest entry."""
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
    (GOLDEN_DIR / "frontmatter_111.json").write_text(blob, encoding="utf-8")
    logging.info("frontmatter: entries=%d sha256=%s", len(mapping), _sha256(blob))
    return 0


def capture_batch() -> int:
    """Fingerprint get_next_batch() selection at four batch sizes."""
    manifest = batch_import.load_manifest()
    progress = batch_import.load_progress()

    mapping = {}
    for count in BATCH_COUNTS:
        ids = [_entry_id(e) for e in batch_import.get_next_batch(manifest, progress, count)]
        mapping[str(count)] = ids
        logging.info("next_batch: count=%d selected=%d sha256=%s",
                     count, len(ids), _sha256(",".join(ids))[:16])

    blob = json.dumps(mapping, ensure_ascii=False, sort_keys=True)
    (GOLDEN_DIR / "next_batch.json").write_text(blob, encoding="utf-8")
    return 0


def capture_status() -> int:
    """Fingerprint the real CLI's status stdout (never re-implemented here)."""
    result = subprocess.run(
        [sys.executable, str(PIPELINE_DIR / "batch_import.py"), "--status"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR),
        check=False,
    )
    if result.returncode != 0:
        logging.error("status capture failed with exit code %d: %s",
                      result.returncode, result.stderr.strip())
        return 1

    (GOLDEN_DIR / "status.txt").write_text(result.stdout, encoding="utf-8")
    logging.info("status: %d lines captured", len(result.stdout.splitlines()))
    return 0


def capture_link_resolver() -> int:
    """Fingerprint the diff link_resolver.py --all produces over laws/israel/.

    A non-empty diff is expected and correct: it is pre-existing staleness plus
    the deferred _STRIP_MG_INDEX idempotency bug (07-RESEARCH.md Pitfall 1).
    The gate is a before/after differential, not a diff-against-HEAD test.
    """
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
        logging.error("link_resolver --all failed with exit code %d", run.returncode)
        _git("checkout", "--", LAWS_PATH)
        return 1

    diff = _git("diff", LAWS_PATH)
    if diff.returncode != 0:
        logging.error("git diff failed: %s", diff.stderr.strip())
        _git("checkout", "--", LAWS_PATH)
        return 1

    (GOLDEN_DIR / "link_resolver_all.diff").write_text(diff.stdout, encoding="utf-8")

    stat = _git("diff", "--stat", LAWS_PATH)
    logging.info("link_resolver: %s", (stat.stdout.strip().splitlines() or ["(empty)"])[-1])

    _git("checkout", "--", LAWS_PATH)

    dirty = _git("status", "--porcelain", LAWS_PATH).stdout.strip()
    if dirty:
        logging.error("laws/israel/ NOT restored after capture: %s", dirty)
        return 1

    logging.info("link_resolver: laws/israel/ restored, tree clean")
    return 0


CAPTURES = {
    "frontmatter": capture_frontmatter,
    "batch": capture_batch,
    "status": capture_status,
    "link_resolver": capture_link_resolver,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", dest="only", default=None,
                        help="Re-capture a single fixture "
                             "(frontmatter, batch, status, link_resolver)")
    only = parser.parse_args(argv).only

    if only is not None and only not in CAPTURES:
        logging.error("unknown capture %r — choose one of: %s",
                      only, ", ".join(sorted(CAPTURES)))
        return 1

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    names = [only] if only else list(CAPTURES)
    failed = 0
    for name in names:
        logging.info("capturing %s ...", name)
        if CAPTURES[name]() != 0:
            logging.error("capture failed: %s", name)
            failed += 1

    if failed:
        logging.error("%d of %d captures failed", failed, len(names))
        return 1

    logging.info("captured %d fixture(s) into %s", len(names), GOLDEN_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
