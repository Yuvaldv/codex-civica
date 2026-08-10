from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

def load_progress(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"done": [], "failed": [], "total_deployed": 0, "priority": []}


def save_progress(path: Path, progress: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def get_next_batch(
    manifest: list[dict],
    progress: dict,
    count: int,
    id_keys: tuple[str, ...] = ("law_id", "bill_id"),
    source_key: str = "pdf_path",
) -> list[dict]:
    """Return next N unprocessed laws that have PDFs. Priority queue is drained first."""
    done_set = set(str(x) for x in progress.get("done", []))
    failed_set = set(str(x) for x in progress.get("failed", []))
    priority_ids = [str(x) for x in progress.get("priority", [])
                    if str(x) not in done_set and str(x) not in failed_set]

    # Build a lookup by law_id for fast access
    by_id = {str(_get_id(e, id_keys)): e for e in manifest}

    batch: list[dict] = []

    # Drain priority queue first
    for pid in priority_ids:
        if len(batch) >= count:
            break
        entry = by_id.get(pid)
        if not entry:
            continue
        if not entry.get(source_key) or not Path(entry[source_key]).exists():
            continue
        batch.append(entry)

    # Fill remaining slots from manifest in order
    for entry in manifest:
        if len(batch) >= count:
            break
        law_id = _get_id(entry, id_keys)
        if not law_id:
            continue
        if str(law_id) in done_set or str(law_id) in failed_set:
            continue
        if any(e is entry for e in batch):
            continue
        if not entry.get(source_key) or not Path(entry[source_key]).exists():
            continue
        batch.append(entry)

    return batch


def _get_id(entry: dict, id_keys: tuple[str, ...]):
    for key in id_keys:
        value = entry.get(key)
        if value:
            return value
    return None


def print_status(manifest: list[dict], progress: dict, source_label: str = "With PDF") -> None:
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
    print(f"{source_label}:".ljust(17) + f"{with_pdf}")
    print(f"Converted:       {len(done)}")
    print(f"Failed:          {len(failed)}")
    print(f"Pending:         {pending}")
    print(f"Total deployed:  {progress.get('total_deployed', 0)}")
