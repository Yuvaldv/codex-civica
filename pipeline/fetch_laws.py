#!/usr/bin/env python3
"""Fetch all Israeli laws with full metadata from Knesset OData API.

Uses KNS_IsraelLaw (consolidated laws) as canonical source, enriched with:
  - topic classifications (KNS_IsraelLawClassificiation)
  - responsible ministries (KNS_IsraelLawMinistry + KNS_GovMinistry)
  - PDF URLs via original enacting bill (KNS_LawBinding -> KNS_DocumentBill)

Output: data/raw/israel/manifest_laws.json
  [{"law_id": 2000001, "name_he": "...", "classifications": [...], ...}, ...]
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import requests
from tqdm import tqdm

ODATA_BASE = "https://knesset.gov.il/Odata/ParliamentInfo.svc"
FS_BASE = "https://fs.knesset.gov.il"
DATA_DIR = Path(__file__).parent.parent / "data" / "raw" / "israel"
MANIFEST_PATH = DATA_DIR / "manifest_laws.json"

LAW_VALIDITY_VALID = 6079   # תקף
BINDING_ORIGINAL = 6012     # החוק המקורי
GROUP_TYPE_RESHUMOT = 9     # Official Reshumot publication

PAGE_SIZE = 100
REQUEST_TIMEOUT = 30
RETRY_DELAY = 2
MAX_RETRIES = 3

CLASSIFICATION_SLUGS: dict[int, str] = {
    1: "citizenship",
    3: "defense",
    4: "public-security",
    5: "housing-construction",
    7: "health",
    9: "religion",
    10: "environment",
    11: "foreign-affairs",
    12: "economic-arrangements",
    13: "basic-laws",
    14: "education",
    15: "agriculture",
    16: "knesset",
    18: "holidays",
    19: "taxation",
    20: "commerce-industry",
    21: "personal-status",
    23: "real-estate",
    24: "civil-law",
    25: "administrative-law",
    26: "criminal-law",
    27: "asset-management",
    28: "sports",
    29: "maritime",
    30: "judiciary",
    33: "consumer-protection",
    34: "immigration",
    35: "evidence-procedure",
    36: "heads-of-state",
    37: "welfare",
    38: "local-authorities",
    41: "transportation",
    42: "tourism",
    44: "aviation",
    45: "employment",
    46: "budget",
    48: "communications",
    50: "infrastructure",
}


def paginate(session: requests.Session, url: str, params: dict | None = None) -> list[dict]:
    """Fetch all pages from an OData endpoint."""
    all_records: list[dict] = []
    skip = 0
    base_params = dict(params or {})
    base_params["$format"] = "json"

    while True:
        p = dict(base_params)
        p["$top"] = PAGE_SIZE
        p["$skip"] = skip
        for attempt in range(MAX_RETRIES):
            try:
                r = session.get(url, params=p, timeout=REQUEST_TIMEOUT)
                r.raise_for_status()
                break
            except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    logging.error("Failed to fetch %s at skip=%d: %s", url, skip, e)
                    return all_records
        page = r.json().get("value", [])
        if not page:
            break
        all_records.extend(page)
        skip += PAGE_SIZE
        time.sleep(0.05)

    return all_records


def fetch_lookup_tables(session: requests.Session) -> tuple[
    dict[int, list[dict]],   # israel_law_id -> [{id, desc}]
    dict[int, list[str]],    # israel_law_id -> [ministry_name]
    dict[int, int],          # israel_law_id -> bill_id (original enacting bill)
    dict[int, str],          # ministry_id -> name
]:
    """Bulk-fetch all classification, ministry, and binding lookup tables."""
    logging.info("Fetching classification table...")
    cls_raw = paginate(session, f"{ODATA_BASE}/KNS_IsraelLawClassificiation")
    cls_by_law: dict[int, list[dict]] = {}
    for r in cls_raw:
        lid = r.get("IsraelLawID")
        if lid:
            cls_by_law.setdefault(lid, []).append({
                "id": r.get("ClassificiationID"),
                "desc": r.get("ClassificiationDesc", ""),
            })
    logging.info("  %d classification records for %d laws", len(cls_raw), len(cls_by_law))

    logging.info("Fetching ministry name table...")
    min_raw = paginate(session, f"{ODATA_BASE}/KNS_GovMinistry")
    ministry_names: dict[int, str] = {
        r["GovMinistryID"]: r["Name"] for r in min_raw if r.get("GovMinistryID")
    }
    logging.info("  %d ministry names", len(ministry_names))

    logging.info("Fetching law-ministry links...")
    lmin_raw = paginate(session, f"{ODATA_BASE}/KNS_IsraelLawMinistry")
    # Note: GovMinistryID in this table uses a legacy ID range (1-50) that doesn't
    # map to KNS_GovMinistry IDs (490+). Store as raw IDs; name mapping is a TODO.
    min_by_law: dict[int, list[int]] = {}
    for r in lmin_raw:
        lid = r.get("IsraelLawID")
        mid = r.get("GovMinistryID")
        if lid and mid:
            min_by_law.setdefault(lid, []).append(mid)
    logging.info("  %d law-ministry links for %d laws", len(lmin_raw), len(min_by_law))

    logging.info("Fetching original law bindings...")
    bind_raw = paginate(
        session,
        f"{ODATA_BASE}/KNS_LawBinding",
        {"$filter": f"BindingType eq {BINDING_ORIGINAL}"},
    )
    # Keep only the first (lowest BillID) original per IsraelLaw
    bill_by_law: dict[int, int] = {}
    for r in bind_raw:
        lid = r.get("IsraelLawID")
        bill_id = r.get("LawID")
        if lid and bill_id:
            if lid not in bill_by_law or bill_id < bill_by_law[lid]:
                bill_by_law[lid] = bill_id
    logging.info("  %d original bindings for %d laws", len(bind_raw), len(bill_by_law))

    return cls_by_law, min_by_law, bill_by_law, {}


def fetch_pdf_url(session: requests.Session, bill_id: int) -> str | None:
    """Fetch the Reshumot PDF URL for a bill from KNS_DocumentBill."""
    url = (
        f"{ODATA_BASE}/KNS_DocumentBill"
        f"?$filter=BillID eq {int(bill_id)} and GroupTypeID eq {GROUP_TYPE_RESHUMOT}"
        f"&$format=json"
    )
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            break
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                logging.warning("DocumentBill fetch failed for bill %d: %s", bill_id, e)
                return None

    docs = r.json().get("value", [])
    pdf_docs = [d for d in docs if d.get("ApplicationDesc", "").upper() == "PDF"]
    if not pdf_docs:
        return None
    pdf_docs.sort(key=lambda d: d.get("LastUpdatedDate") or "", reverse=True)
    fp = pdf_docs[0].get("FilePath", "")
    if not fp:
        return None
    if fp.startswith("//"):
        return f"https:{fp}"
    if fp.startswith("/"):
        return f"{FS_BASE}{fp}"
    return fp


def download_pdf(session: requests.Session, url: str, dest: Path) -> bool:
    """Download PDF to dest. Returns True on success. Skips if exists."""
    if dest.exists():
        return True
    try:
        r = session.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout, OSError) as e:
        logging.warning("Download failed from %s: %s", url, e)
        if dest.exists():
            try:
                dest.unlink()
            except OSError:
                pass
        return False


def load_manifest() -> dict[int, dict]:
    """Load existing manifest keyed by law_id."""
    if not MANIFEST_PATH.exists():
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    return {e["law_id"]: e for e in entries}


def save_manifest(manifest: dict[int, dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(list(manifest.values()), f, ensure_ascii=False, indent=2)


def main(limit: int | None = None, skip_pdfs: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    session = requests.Session()

    manifest = load_manifest()
    logging.info("Loaded %d existing manifest entries.", len(manifest))

    cls_by_law, min_by_law, bill_by_law, _ = fetch_lookup_tables(session)

    logging.info("Fetching valid IsraelLaw records...")
    laws_raw = paginate(
        session,
        f"{ODATA_BASE}/KNS_IsraelLaw",
        {"$filter": f"LawValidityID eq {LAW_VALIDITY_VALID}"},
    )
    logging.info("Total valid laws: %d", len(laws_raw))
    if limit:
        laws_raw = laws_raw[:limit]

    with tqdm(laws_raw, desc="Processing laws") as progress:
        for law in progress:
            law_id: int = law["IsraelLawID"]
            str_id = str(law_id)

            classifications = cls_by_law.get(law_id, [])
            ministries = min_by_law.get(law_id, [])
            bill_id = bill_by_law.get(law_id)

            primary_cls = classifications[0] if classifications else None
            category_slug = (
                CLASSIFICATION_SLUGS.get(primary_cls["id"], "")
                if primary_cls
                else ("basic-laws" if law.get("IsBasicLaw") else "")
            )

            entry: dict = {
                "law_id": law_id,
                "name_he": law.get("Name", ""),
                "publication_date": (law.get("PublicationDate") or "")[:10],
                "latest_publication_date": (law.get("LatestPublicationDate") or "")[:10],
                "is_basic_law": bool(law.get("IsBasicLaw")),
                "is_budget_law": bool(law.get("IsBudgetLaw")),
                "law_validity": law.get("LawValidityDesc", ""),
                "classifications": classifications,
                "category": category_slug,
                "ministry_ids": ministries,  # raw GovMinistryIDs (legacy range, name mapping TODO)
                "bill_id": bill_id,
                "pdf_url": None,
                "pdf_path": None,
                "status": "pending",
            }

            # Preserve existing status (done/failed) and pdf_path
            if law_id in manifest:
                existing = manifest[law_id]
                entry["status"] = existing.get("status", "pending")
                entry["pdf_path"] = existing.get("pdf_path")
                entry["pdf_url"] = existing.get("pdf_url")

            if not skip_pdfs and entry["status"] == "pending" and bill_id:
                # Fetch PDF URL
                if not entry["pdf_url"]:
                    pdf_url = fetch_pdf_url(session, bill_id)
                    entry["pdf_url"] = pdf_url
                    time.sleep(0.05)

                # Download if we have URL and PDF not yet on disk
                if entry["pdf_url"] and not entry["pdf_path"]:
                    dest = DATA_DIR / f"{law_id}.pdf"
                    if download_pdf(session, entry["pdf_url"], dest):
                        entry["pdf_path"] = str(dest)
                    time.sleep(0.05)

            manifest[law_id] = entry

    save_manifest(manifest)
    pdf_count = sum(1 for e in manifest.values() if e.get("pdf_path"))
    pending = sum(1 for e in manifest.values() if e.get("status") == "pending")
    done = sum(1 for e in manifest.values() if e.get("status") == "done")
    print(f"Done. {len(manifest)} laws | {pdf_count} PDFs | {done} converted | {pending} pending")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Process only first N laws")
    parser.add_argument("--skip-pdfs", action="store_true", help="Fetch metadata only, skip PDF download")
    args = parser.parse_args()
    raise SystemExit(main(limit=args.limit, skip_pdfs=args.skip_pdfs))
