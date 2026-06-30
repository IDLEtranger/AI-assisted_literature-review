from pathlib import Path
import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv

"""
Enrich missing abstracts and authors after record deduplication.

Input:
    data/records_deduped.csv

Output:
    data/records_enriched.csv

Main processing steps:
    1. Load deduplicated literature records.
    2. Keep existing abstracts unchanged.
    3. For records with an empty abstract and a valid scopus_id,
       request the abstract from the Scopus Abstract Retrieval API.
    4. Save enriched records to records_enriched.csv.

Why this runs after deduplication:
    The same publication may appear in multiple databases.
    Enriching only unique records avoids unnecessary API requests.

Important:
    Records without retrievable abstracts are retained.
    ASReview can still screen records using titles only, although abstracts
    generally improve screening quality.
"""

load_dotenv()

API_KEY = os.getenv("ELSEVIER_API_KEY")

INPUT_PATH = Path("data/records_deduped.csv")
OUTPUT_PATH = Path("data/records_enriched.csv")


def as_list(value) -> list:
    if not value:
        return []

    if isinstance(value, list):
        return value

    return [value]


def count_authors(value: str) -> int:
    authors = [
        author.strip()
        for author in str(value or "").split(";")
        if author.strip()
    ]
    return len(authors)


def split_scopus_ids(value: str) -> list[str]:
    scopus_ids = []

    for item in str(value or "").split(";"):
        scopus_id = item.strip().replace("SCOPUS_ID:", "").strip()
        if scopus_id:
            scopus_ids.append(scopus_id)

    return scopus_ids


def get_author_name(author: dict) -> str:
    if not isinstance(author, dict):
        return ""

    preferred_name = author.get("preferred-name", {}) or {}

    name = (
        author.get("ce:indexed-name")
        or preferred_name.get("ce:indexed-name")
        or ""
    )

    if name:
        return name.strip()

    surname = (
        author.get("ce:surname")
        or preferred_name.get("ce:surname")
        or ""
    )
    initials = (
        author.get("ce:initials")
        or preferred_name.get("ce:initials")
        or ""
    )

    return f"{surname} {initials}".strip()


def fetch_scopus_metadata(scopus_id: str) -> dict:
    if not API_KEY:
        raise RuntimeError(
            "ELSEVIER_API_KEY is missing. Add it to your .env file."
        )

    url = (
        "https://api.elsevier.com/content/"
        f"abstract/scopus_id/{scopus_id}"
    )

    response = requests.get(
        url,
        headers={
            "X-ELS-APIKey": API_KEY,
            "Accept": "application/json",
        },
        params={"view": "META_ABS"},
        timeout=60,
    )

    if response.status_code in {401, 403, 404}:
        response.raise_for_status()
        return {
            "abstract": "",
            "authors": "",
        }

    response.raise_for_status()

    payload = response.json()

    record = payload.get("abstracts-retrieval-response", {})

    abstract = (
        record.get("coredata", {})
        .get("dc:description", "")
        or ""
    )

    authors = record.get("authors", {}) or {}
    author_items = as_list(authors.get("author", []))

    author_names = []
    seen_author_names = set()

    for author in author_items:
        name = get_author_name(author)

        if name and name not in seen_author_names:
            author_names.append(name)
            seen_author_names.add(name)

    return {
        "abstract": abstract.strip(),
        "authors": "; ".join(author_names),
    }


def main() -> None:
    df = pd.read_csv(INPUT_PATH, dtype=str).fillna("")

    if "abstract" not in df.columns:
        df["abstract"] = ""

    if "authors" not in df.columns:
        df["authors"] = ""

    if "scopus_id" not in df.columns:
        df["scopus_id"] = ""

    for index, row in df.iterrows():
        need_abstract = not row["abstract"].strip()
        need_authors = count_authors(row["authors"]) <= 1

        if not need_abstract and not need_authors:
            continue

        scopus_ids = split_scopus_ids(row["scopus_id"])

        if not scopus_ids:
            continue

        metadata = {
            "abstract": "",
            "authors": "",
        }

        for scopus_id in scopus_ids:
            try:
                print(f"Fetching metadata for {scopus_id}")
                fetched = fetch_scopus_metadata(scopus_id)

                metadata["abstract"] = (
                    metadata["abstract"]
                    or fetched["abstract"]
                )
                metadata["authors"] = (
                    metadata["authors"]
                    or fetched["authors"]
                )

                has_needed_abstract = (
                    not need_abstract
                    or bool(metadata["abstract"])
                )
                has_needed_authors = (
                    not need_authors
                    or bool(metadata["authors"])
                )

                if has_needed_abstract and has_needed_authors:
                    break

            except requests.RequestException as error:
                print(f"Failed for {scopus_id}: {error}")

            time.sleep(0.3)

        if need_abstract and metadata["abstract"]:
            df.at[index, "abstract"] = metadata["abstract"]

        if need_authors and metadata["authors"]:
            df.at[index, "authors"] = metadata["authors"]

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
