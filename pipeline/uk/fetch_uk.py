#!/usr/bin/env python3
"""Fetch the UK (England) CLML starter batch from legislation.gov.uk.

Downloads a hardcoded 10-item Tier A batch of `ukpga`/`aep` Acts as CLML XML,
gated on two hard checks before anything is written to disk:
  1. Not a PDF-only stub (NumberOfProvisions > 0, Body or Schedules present)
  2. Genuinely the revised (never /enacted) version

Respects legislation.gov.uk's fair-use rules: a mandatory identifying
User-Agent and a 5-second crawl-delay between requests, sequential only.

Output:
  data/raw/uk/xml/<slug>.xml    one file per item that passes both gates
  data/raw/uk/manifest_uk.json  one row per item, including skipped stubs
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import time
from pathlib import Path

import requests
from lxml import etree

BASE_URL = "https://www.legislation.gov.uk"
USER_AGENT = "CodexCivica (https://github.com/Yuvaldv/codex-civica)"
CRAWL_DELAY = 5
REQUEST_TIMEOUT = 30
RETRY_DELAY = 2
MAX_RETRIES = 3

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "uk"
XML_DIR = DATA_DIR / "xml"
MANIFEST_PATH = DATA_DIR / "manifest_uk.json"

NS = {
    "leg": "http://www.legislation.gov.uk/namespaces/legislation",
    "ukm": "http://www.legislation.gov.uk/namespaces/metadata",
    "dc": "http://purl.org/dc/elements/1.1/",
}

# The 20-item England batch (13 aep, 7... see per-row comments), grown from the
# original 10-item Tier A starter batch on 2026-08-10 with an explicit user
# go-ahead ("fetch 10 new laws for england"). Hardcoded, not discovered: any
# further growth needs the same explicit go-ahead. The extension 10 were
# chosen from a live-verified probe of 15 candidates (see manifest_uk.json
# history / STATE.md decision log) — 3 are Tier A Acts originally dropped as
# redundant-with-a-kept-Act (now added back since "redundant" was a batch-of-10
# constraint, not a quality judgment), the other 7 are new small/medium Acts
# (22KB-162KB XML) picked to stay well clear of the >1MB page-splitting
# blocker documented in STATE.md's Known Constraints.
BATCH = [
    {"uri": "ukpga/Geo6/12-13-14/103", "type": "ukpga"},  # Parliament Act 1949
    {"uri": "ukpga/2011/14", "type": "ukpga"},              # Fixed-term Parliaments Act 2011
    {"uri": "aep/WillandMarSess2/1/2", "type": "aep"},       # Bill of Rights [1688]
    {"uri": "aep/Edw1cc1929/25/9", "type": "aep"},           # Magna Carta (1297)
    {"uri": "aep/Ann/6/11", "type": "aep"},                  # Union with Scotland Act 1706
    {"uri": "ukpga/2013/26", "type": "ukpga"},               # Defamation Act 2013
    {"uri": "ukpga/2010/23", "type": "ukpga"},               # Bribery Act 2010
    {"uri": "ukpga/1990/18", "type": "ukpga"},               # Computer Misuse Act 1990
    {"uri": "ukpga/1998/42", "type": "ukpga"},               # Human Rights Act 1998
    {"uri": "ukpga/1978/30", "type": "ukpga"},               # Interpretation Act 1978
    # -- extension batch, added 2026-08-10 --
    {"uri": "ukpga/Geo5/1-2/13", "type": "ukpga"},           # Parliament Act 1911 (20KB)
    {"uri": "aep/Will3/12-13/2", "type": "aep"},             # Act of Settlement 1700 (41KB)
    {"uri": "aep/Cha2/31/2", "type": "aep"},                 # Habeas Corpus Act 1679 (57KB)
    {"uri": "aep/Cha2/29/3", "type": "aep"},                 # Statute of Frauds 1677 (22KB)
    {"uri": "ukpga/1988/27", "type": "ukpga"},               # Malicious Communications Act 1988 (31KB)
    {"uri": "ukpga/1961/60", "type": "ukpga"},               # Suicide Act 1961 (39KB)
    {"uri": "ukpga/1911/6", "type": "ukpga"},                # Perjury Act 1911 (78KB)
    {"uri": "ukpga/1959/66", "type": "ukpga"},               # Obscene Publications Act 1959 (83KB)
    {"uri": "ukpga/2000/44", "type": "ukpga"},               # Sexual Offences (Amendment) Act 2000 (98KB)
    {"uri": "ukpga/1989/6", "type": "ukpga"},                # Official Secrets Act 1989 (162KB)
]


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def fetch_raw(session: requests.Session, uri: str) -> tuple[bytes, str] | None:
    url = f"{BASE_URL}/{uri}/data.xml"
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.content, response.url
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                logging.error("fetch failed for %s: %s", uri, e)
                return None
    return None


def parse_gates(xml_bytes: bytes, uri: str) -> dict | None:
    """Apply the two hard gates. Returns parsed metadata dict on pass, None on reject."""
    root = etree.fromstring(xml_bytes)

    n_provisions = root.get("NumberOfProvisions")
    document_uri = root.get("DocumentURI")

    has_body = (
        root.find(".//leg:Primary/leg:Body", NS) is not None
        or root.find(".//leg:Primary/leg:Schedules", NS) is not None
        or root.find(".//leg:Secondary/leg:Body", NS) is not None
        or root.find(".//leg:Secondary/leg:Schedules", NS) is not None
    )

    if n_provisions is None:
        logging.warning("stub gate: %s has no NumberOfProvisions attribute — skipping", uri)
        return None
    if n_provisions == "0":
        logging.warning("stub gate: %s has NumberOfProvisions=0 — skipping (PDF-only)", uri)
        return None
    if not has_body:
        logging.warning("stub gate: %s has no Body or Schedules — skipping (PDF-only)", uri)
        return None

    status_el = root.find(".//ukm:DocumentStatus", NS)
    doc_status = status_el.get("Value") if status_el is not None else None
    if doc_status != "revised":
        logging.error(
            "version gate: %s resolved doc_status=%r (expected 'revised') — rejecting", uri, doc_status
        )
        return None

    year_el = root.find(".//ukm:Year", NS)
    number_el = root.find(".//ukm:Number", NS)
    title_el = root.find(".//dc:title", NS)

    return {
        "document_uri": document_uri,
        "doc_status": doc_status,
        "year": year_el.get("Value") if year_el is not None else None,
        "number": number_el.get("Value") if number_el is not None else None,
        "title": title_el.text if title_el is not None else None,
        "number_of_provisions": int(n_provisions),
    }


def derive_slug(item_type: str, year: str, number: str) -> str:
    return f"{item_type}-{year}-{number}"


def fetch_item(session: requests.Session, uri: str, item_type: str) -> dict:
    base_row = {"uri": uri, "type": item_type, "requested_url": f"{BASE_URL}/{uri}/data.xml"}

    fetched = fetch_raw(session, uri)
    if fetched is None:
        return {
            **base_row,
            "status": "fetch_failed",
            "xml_path": None,
            "skip_reason": "request failed after retries",
        }
    xml_bytes, resolved_url = fetched

    meta = parse_gates(xml_bytes, uri)
    if meta is None:
        # Distinguish the two gates for the manifest by re-checking NumberOfProvisions
        # cheaply — parse_gates already logged the precise reason.
        try:
            root = etree.fromstring(xml_bytes)
            n_provisions = root.get("NumberOfProvisions")
            status_el = root.find(".//ukm:DocumentStatus", NS)
            doc_status = status_el.get("Value") if status_el is not None else None
        except etree.XMLSyntaxError:
            n_provisions, doc_status = None, None

        if n_provisions in (None, "0"):
            status, reason = "pdf_only", "NumberOfProvisions=0 or absent, or no Body/Schedules"
        else:
            status, reason = "wrong_version", f"doc_status={doc_status!r}, expected 'revised'"

        return {**base_row, "status": status, "xml_path": None, "skip_reason": reason}

    slug = derive_slug(item_type, meta["year"], meta["number"])
    xml_path = XML_DIR / f"{slug}.xml"

    if not xml_path.exists():
        XML_DIR.mkdir(parents=True, exist_ok=True)
        xml_path.write_bytes(xml_bytes)

    return {
        **base_row,
        "slug": slug,
        "resolved_document_uri": meta["document_uri"],
        "doc_status": meta["doc_status"],
        "title": meta["title"],
        "year": meta["year"],
        "number": meta["number"],
        "number_of_provisions": meta["number_of_provisions"],
        "xml_path": str(xml_path.relative_to(Path(__file__).parent.parent.parent)),
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "fetched",
    }


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_manifest(rows: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cached_by_uri = {
        row["uri"]: row
        for row in load_manifest()
        if row.get("status") == "fetched" and row.get("xml_path") and Path(row["xml_path"]).exists()
    }

    session = make_session()
    rows: list[dict] = []
    fetched_this_run = 0

    for i, item in enumerate(BATCH):
        cached = cached_by_uri.get(item["uri"])
        if cached is not None:
            logging.info("[%d/%d] %s (%s) -> cached, skipping fetch", i + 1, len(BATCH), item["uri"], item["type"])
            rows.append(cached)
            continue

        if fetched_this_run:
            time.sleep(CRAWL_DELAY)

        logging.info("[%d/%d] fetching %s (%s)...", i + 1, len(BATCH), item["uri"], item["type"])
        row = fetch_item(session, item["uri"], item["type"])
        rows.append(row)
        logging.info("  -> status=%s", row["status"])
        fetched_this_run += 1

    save_manifest(rows)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    logging.info(
        "done: %s",
        ", ".join(f"{status}={n}" for status, n in sorted(counts.items())),
    )

    return 0 if all(row["status"] == "fetched" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
