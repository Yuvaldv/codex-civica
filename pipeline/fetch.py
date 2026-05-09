#!/usr/bin/env python3
"""Fetch Knesset law metadata and PDFs from OData API and fs.knesset.gov.il."""

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
MANIFEST_PATH = DATA_DIR / "manifest.json"
STATUS_IN_EFFECT = 118        # StatusID for enacted/in-effect laws
GROUP_TYPE_RESHUMOT = 9       # GroupTypeID for official Reshumot publication
PAGE_SIZE = 100
REQUEST_TIMEOUT = 30          # seconds
RETRY_DELAY = 2               # seconds between retries
MAX_RETRIES = 3


def fetch_bills(session, skip=0, top=100, name_prefixes=None):
    """Fetch a page of enacted bills from the Knesset OData API.

    Optional ``name_prefixes`` is a list of strings; when given, the OData
    filter is extended with an OR of ``startswith(Name, '<prefix>')`` clauses
    so the server returns only bills whose Name begins with one of them.

    Returns a list of bill dicts or raises requests.HTTPError on failure.
    """
    filter_parts = [f"StatusID eq {STATUS_IN_EFFECT}"]
    if name_prefixes:
        # OData strings escape ' as '' (double single-quote)
        clauses = [f"startswith(Name, '{p.replace(chr(39), chr(39)*2)}')" for p in name_prefixes]
        filter_parts.append("(" + " or ".join(clauses) + ")")
    filter_str = " and ".join(filter_parts)
    params = {
        "$filter": filter_str,
        "$top": top,
        "$skip": skip,
        "$format": "json",
    }
    response = session.get(f"{ODATA_BASE}/KNS_Bill", params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()["value"]


def fetch_pdf_url(session, bill_id):
    """Fetch the official PDF URL for a bill from KNS_DocumentBill.

    Filters for GroupTypeID=9 (Reshumot) entries where ApplicationDesc is PDF.
    Returns the URL of the most recently updated PDF, or None if not found.
    Raises requests.HTTPError on non-200 response.

    Security: bill_id must be an integer — validated before use.
    """
    bill_id = int(bill_id)  # T-01-06: reject non-integer BillID (raises ValueError)

    url = (
        f"{ODATA_BASE}/KNS_DocumentBill"
        f"?$filter=BillID eq {bill_id} and GroupTypeID eq {GROUP_TYPE_RESHUMOT}"
        f"&$format=json"
    )
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    docs = response.json().get("value", [])
    # Filter for PDF entries (case-insensitive)
    pdf_docs = [
        d for d in docs
        if d.get("ApplicationDesc", "").upper() == "PDF"
    ]
    if not pdf_docs:
        return None

    # Pick the entry with the latest LastUpdatedDate
    pdf_docs.sort(key=lambda d: d.get("LastUpdatedDate") or "", reverse=True)
    file_path = pdf_docs[0].get("FilePath", "")
    if not file_path:
        return None

    # FilePath from OData is a relative path like //1/law/1_lsr_207874.PDF
    # Construct the full URL from FS_BASE
    if file_path.startswith("//"):
        return f"https:{file_path}"
    if file_path.startswith("/"):
        return f"{FS_BASE}{file_path}"
    return file_path


def download_pdf(session, url, dest_path):
    """Download a PDF from url to dest_path using chunked streaming.

    Returns True on success, False on any HTTP/IO error (logs the error).
    Skips the download if dest_path already exists (idempotent).
    """
    dest_path = Path(dest_path)
    if dest_path.exists():
        return True  # Already downloaded

    try:
        response = session.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout, OSError) as e:
        logging.warning("Failed to download PDF from %s: %s", url, e)
        # Remove partial file if it was created
        if dest_path.exists():
            try:
                dest_path.unlink()
            except OSError:
                pass
        return False


def load_manifest():
    """Load the existing manifest from disk.

    Returns a dict keyed by str(bill_id), or {} if no manifest exists.
    """
    if not MANIFEST_PATH.exists():
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    return {str(e["bill_id"]): e for e in entries}


def save_manifest(manifest):
    """Write the manifest dict values as a JSON list to MANIFEST_PATH.

    Creates DATA_DIR if it does not exist.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(list(manifest.values()), f, ensure_ascii=False, indent=2)


def main(limit=None, name_prefixes=None):
    """Main entry point: fetch all enacted laws and download their PDFs."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    session = requests.Session()

    # Load existing manifest for crash recovery
    manifest = load_manifest()
    logging.info("Loaded %d existing manifest entries.", len(manifest))

    # Paginate through KNS_Bill to collect all enacted laws
    if name_prefixes:
        logging.info("Filtering bills by name prefixes: %s", name_prefixes)
    logging.info("Fetching bill list from OData API...")
    all_bills = []
    skip = 0
    while True:
        try:
            page = fetch_bills(session, skip=skip, top=PAGE_SIZE, name_prefixes=name_prefixes)
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
            logging.error("Failed to fetch bills at skip=%d: %s", skip, e)
            break
        if not page:
            break
        all_bills.extend(page)
        logging.info("Fetched %d bills so far (skip=%d).", len(all_bills), skip)
        skip += PAGE_SIZE
        if limit and len(all_bills) >= limit:
            all_bills = all_bills[:limit]
            break
        time.sleep(0.1)  # T-01-05: polite delay to avoid hammering the server

    logging.info("Total bills to process: %d", len(all_bills))

    # Download PDFs for each bill
    page_counter = 0
    with tqdm(all_bills, desc="Downloading PDFs") as progress:
        for bill in progress:
            try:
                bill_id = int(bill["BillID"])  # T-01-06: ensure integer
            except (ValueError, TypeError) as e:
                logging.warning("Skipping bill with invalid BillID %r: %s", bill.get("BillID"), e)
                continue

            str_id = str(bill_id)

            # Skip if already in manifest and PDF exists on disk
            if str_id in manifest and manifest[str_id].get("pdf_path") and Path(manifest[str_id]["pdf_path"]).exists():
                continue

            # Fetch PDF URL with retry logic
            pdf_url = None
            for attempt in range(MAX_RETRIES):
                try:
                    pdf_url = fetch_pdf_url(session, bill_id)
                    break
                except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
                    if attempt < MAX_RETRIES - 1:
                        logging.warning(
                            "Attempt %d/%d: could not fetch doc list for bill %d: %s",
                            attempt + 1, MAX_RETRIES, bill_id, e,
                        )
                        time.sleep(RETRY_DELAY)
                    else:
                        logging.warning("All retries exhausted for bill %d: %s", bill_id, e)
                except ValueError as e:
                    logging.warning("Invalid BillID %r: %s", bill_id, e)
                    break

            # Download PDF if URL was found
            pdf_path = None
            if pdf_url:
                dest = DATA_DIR / f"{int(bill_id)}.pdf"  # T-01-06: int cast for path safety
                success = download_pdf(session, pdf_url, dest)
                if success:
                    pdf_path = str(dest)

            manifest[str_id] = {
                "bill_id": bill_id,
                "name_he": bill.get("Name", ""),
                "publication_date": bill.get("PublicationDate"),
                "sub_type_id": bill.get("SubTypeID"),
                "pdf_path": pdf_path,
                "pdf_url": pdf_url,
            }

            page_counter += 1
            # Save manifest after each page boundary (every PAGE_SIZE bills)
            if page_counter % PAGE_SIZE == 0:
                save_manifest(manifest)
                logging.info("Checkpoint: manifest saved (%d entries).", len(manifest))

    # Final save
    save_manifest(manifest)
    pdf_count = sum(1 for v in manifest.values() if v.get("pdf_path"))
    print(f"Done. {len(manifest)} laws in manifest. PDFs downloaded: {pdf_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Fetch only first N laws (for testing)",
    )
    parser.add_argument(
        "--name-prefix", action="append", default=None, dest="name_prefixes",
        help="Server-side filter: keep only bills whose Name starts with this string. "
             "Repeat the flag for multiple prefixes (OR'd). Example: "
             "--name-prefix 'חוק-יסוד' --name-prefix 'חוק יסוד'",
    )
    args = parser.parse_args()
    main(limit=args.limit, name_prefixes=args.name_prefixes)
