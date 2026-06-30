import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("OPENALEX_API_KEY")
BASE_URL = "https://api.openalex.org/works"

OUTPUT_PATH = Path("data/raw/openalex.csv")

SEARCH_QUERY = (
    '"active learning" systematic review screening'
)

FILTER = (
    "from_publication_date:2015-01-01,"
    "to_publication_date:2026-12-31,"
    "has_abstract:true"
)

MAX_RECORDS = 30
PER_PAGE = 10


def normalise_doi(value: str | None) -> str:
    if not value:
        return ""

    return (
        value.lower()
        .replace("https://doi.org/", "")
        .replace("http://doi.org/", "")
        .strip()
    )


def reconstruct_abstract(inverted_index: dict | None) -> str:
    """
    OpenAlex often stores abstracts as an inverted index:
    {"machine": [0, 5], "learning": [1], ...}
    This function reconstructs normal text.
    """
    if not inverted_index:
        return ""

    positions = {}

    for word, indexes in inverted_index.items():
        for index in indexes:
            positions[index] = word

    return " ".join(
        positions[position]
        for position in sorted(positions)
    )


def parse_work(work: dict) -> dict:
    authors = []

    for authorship in work.get("authorships", []):
        author_name = (
            authorship.get("author", {})
            .get("display_name", "")
        )

        if author_name:
            authors.append(author_name)

    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}

    best_oa_location = work.get("best_oa_location") or {}

    return {
        "title": work.get("title", "") or work.get("display_name", ""),
        "abstract": reconstruct_abstract(
            work.get("abstract_inverted_index")
        ),
        "doi": normalise_doi(work.get("doi")),
        "year": work.get("publication_year", ""),
        "publication_date": work.get("publication_date", ""),
        "authors": "; ".join(authors),
        "journal": source.get("display_name", ""),
        "document_type": work.get("type", ""),
        "language": work.get("language", ""),
        "openalex_id": work.get("id", "").replace(
            "https://openalex.org/",
            ""
        ),
        "pmid": (
            work.get("ids", {})
            .get("pmid", "")
            .replace("https://pubmed.ncbi.nlm.nih.gov/", "")
        ),
        "cited_by_count": work.get("cited_by_count", 0),
        "is_oa": work.get("open_access", {}).get("is_oa", False),
        "oa_url": work.get("open_access", {}).get("oa_url", ""),
        "pdf_url": best_oa_location.get("pdf_url", ""),
        "source": "openalex",
    }


def fetch_page(cursor: str) -> dict:
    params = {
        "search": SEARCH_QUERY,
        "filter": FILTER,
        "per_page": PER_PAGE,
        "cursor": cursor,
    }

    if API_KEY:
        params["api_key"] = API_KEY

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=60,
    )

    if response.status_code == 429:
        raise RuntimeError(
            "OpenAlex rate limit or daily budget reached."
        )

    response.raise_for_status()
    return response.json()
    


if __name__ == "__main__":
    cursor = "*"
    all_records = []

    while len(all_records) < MAX_RECORDS:
        print(
            f"Fetching OpenAlex records. "
            f"Current total: {len(all_records)}"
        )

        payload = fetch_page(cursor)
        results = payload.get("results", [])

        if not results:
            break

        all_records.extend(
            parse_work(work)
            for work in results
        )

        cursor = payload.get("meta", {}).get("next_cursor")

        if not cursor:
            break

        time.sleep(0.2)

    df = pd.DataFrame(all_records[:MAX_RECORDS])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    print(f"Saved {len(df)} records to {OUTPUT_PATH}")