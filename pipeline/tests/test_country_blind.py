#!/usr/bin/env python3
"""SC-4 proof: a non-Israel caller can use pipeline/common/ without touching
Israel-specific code.

Imports ONLY from common.* plus stdlib — never reconcile, batch_import,
link_resolver, or cross_linker. Exercises the full country-blind surface with
synthetic UK-shaped data (doc_id/xml_path instead of law_id/bill_id/pdf_path),
entirely inside a tempfile.mkdtemp() sandbox.
"""
from __future__ import annotations

import inspect
import sys
import tempfile
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PIPELINE_DIR))

from common.deploy import deploy  # noqa: E402
from common.frontmatter import quote, render_frontmatter, split_frontmatter  # noqa: E402
from common.progress import get_next_batch, load_progress, print_status, save_progress  # noqa: E402


def check_progress_roundtrip(tmp: Path) -> None:
    p = tmp / "progress.json"
    assert load_progress(tmp / "nonexistent.json") == {
        "done": [], "failed": [], "total_deployed": 0, "priority": [],
    }
    original = {"done": ["uk1"], "failed": ["uk2"], "total_deployed": 3, "priority": ["uk3"]}
    save_progress(p, original)
    assert load_progress(p) == original
    print("progress round-trip OK (temp path, nonexistent-path default OK)")


def check_batch_selection(tmp: Path) -> None:
    (tmp / "uk1.xml").write_text("act one", encoding="utf-8")
    (tmp / "uk2.xml").write_text("act two", encoding="utf-8")
    (tmp / "uk3.xml").write_text("act three", encoding="utf-8")
    # uk4 deliberately has no xml file on disk — must be skipped like a missing pdf_path.

    manifest = [
        {"doc_id": "uk1", "xml_path": str(tmp / "uk1.xml")},
        {"doc_id": "uk2", "xml_path": str(tmp / "uk2.xml")},
        {"doc_id": "uk3", "xml_path": str(tmp / "uk3.xml")},
        {"doc_id": "uk4", "xml_path": str(tmp / "uk4.xml")},
    ]
    progress = {"done": ["uk1"], "failed": ["uk2"], "total_deployed": 0, "priority": ["uk3"]}

    batch = get_next_batch(manifest, progress, count=5, id_keys=("doc_id",), source_key="xml_path")
    ids = [e["doc_id"] for e in batch]
    assert ids == ["uk3"], f"expected priority-drained ['uk3'], got {ids}"
    print(f"batch selection OK — no Israel key names, priority drained first, "
          f"done/failed/missing-file skipped: {ids}")

    print_status(manifest, progress, source_label="With XML")


def check_frontmatter_render() -> None:
    lines = [
        "doc_id: uk-2024-c15",
        'title: "Some Act 2024"',
        "nation: england",
        'licence: "OGL-UK-3.0"',
    ]
    block = render_frontmatter(lines)
    rendered_lines = block.split("\n")
    assert rendered_lines[0] == "---", "block must open with a fence"
    assert rendered_lines[-2] == "---", "block must close with a fence"
    assert block.endswith("\n"), "block must end with a trailing newline"
    fm, body = split_frontmatter(block + "body text")
    assert fm == block
    assert body == "body text"
    print("render_frontmatter OK — UK-shaped fields, fenced, trailing newline, round-trips via split_frontmatter")

    quoted = quote('has "embedded" quotes')
    assert quoted == '"has \\"embedded\\" quotes"'
    print(f"quote OK — embedded double quote escaped: {quoted}")


def check_deploy_signature_only() -> None:
    sig = inspect.signature(deploy)
    assert list(sig.parameters) == ["site_dir", "env_overrides"]
    assert sig.parameters["site_dir"].default is inspect.Parameter.empty
    print("deploy signature OK — site_dir required, env_overrides optional; deploy() NEVER invoked")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="country_blind_"))
    check_progress_roundtrip(tmp)
    check_batch_selection(tmp)
    check_frontmatter_render()
    check_deploy_signature_only()
    print("COUNTRY_BLIND_OK — full common/ surface exercised with zero Israel code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
