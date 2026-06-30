import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("ELSEVIER_API_KEY")
BASE_URL = "https://api.elsevier.com/content/search/scopus"

OUTPUT_PATH = Path("data/raw/scopus.csv")

QUERY = 'TITLE-ABS-KEY(("active learning" OR "machine learning") AND ("systematic review" OR "evidence synthesis") AND (screening OR "study selection")) AND PUBYEAR > 2014 AND PUBYEAR < 2027'

PAGE_SIZE = 10
MAX_RECORDS = 20


def get_value(record: dict, key: str) -> str:
    value = record.get(key, "")
    if value is None:
        return ""
    return str(value)


def fetch_page(start: int) -> dict:
    headers = {
        "X-ELS-APIKey": API_KEY,
        "Accept": "application/json",
    }

    params = {
        "query": QUERY,
        "count": PAGE_SIZE,
        "start": start,
        "view": "STANDARD",
    }

    response = requests.get(
        BASE_URL,
        headers=headers,
        params=params,
        timeout=60,
    )

    if not response.ok:
        print("Status:", response.status_code)
        print("Request URL:", response.url)
        print("Response body:", response.text)
        response.raise_for_status()

    return response.json()


def parse_record(record: dict) -> dict:
    authors = get_value(record, "dc:creator")

    doi = get_value(record, "prism:doi").lower()
    title = get_value(record, "dc:title")
    journal = get_value(record, "prism:publicationName")

    return {
        "title": title,
        "abstract": "",
        "doi": doi,
        "year": get_value(record, "prism:coverDate")[:4],
        "authors": authors,
        "journal": journal,
        "document_type": get_value(record, "subtypeDescription"),
        "scopus_id": get_value(record, "dc:identifier").replace("SCOPUS_ID:", ""),
        "eid": get_value(record, "eid"),
        "cited_by_count": get_value(record, "citedby-count"),
        "source": "scopus",
        "source_url": get_value(record, "prism:url"),
    }


if __name__ == "__main__":
    if not API_KEY:
        raise RuntimeError(
            "ELSEVIER_API_KEY is missing. Add it to your .env file."
        )

    all_records = []
    start = 0
    total_results = None

    while start < MAX_RECORDS:
        print(f"Fetching Scopus records {start} to {start + PAGE_SIZE - 1}...")

        payload = fetch_page(start)
        search_results = payload.get("search-results", {})

        if total_results is None:
            total_results = int(search_results.get("opensearch:totalResults", 0))
            print(f"Scopus reports {total_results} matching records.")

        entries = search_results.get("entry", [])

        if not entries:
            break

        all_records.extend(parse_record(entry) for entry in entries)

        start += len(entries)

        if start >= total_results:
            break

        time.sleep(0.3)

    df = pd.DataFrame(all_records)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print(f"Saved {len(df)} records to: {OUTPUT_PATH}")