from pathlib import Path
import re

import pandas as pd
from rapidfuzz import fuzz

"""
Merge raw literature exports and remove duplicate records.

Input:
    data/raw/*.csv

Output:
    data/records.csv
        Combined records from all raw source files.
        Includes duplicate records for traceability.

    data/records_deduped.csv
        Canonical candidate record set after deduplication.

Main processing steps:
    1. Read all CSV files from data/raw/.
    2. Map source-specific column names into a shared schema.
    3. Assign an internal record_id to every imported row.
    4. Normalise DOI, title, and publication year fields.
    5. Detect duplicates using:
        - Exact DOI matches.
        - Highly similar titles with the same or nearby year.
    6. Keep one canonical record for each duplicate group.
    7. Preserve source provenance in all_sources.

Important:
    Raw files should not be modified by this script.
    The generated record_id should remain stable for later ASReview matching.
"""

RAW_DIR = Path("data/raw")
OUTPUT_PATH = Path("data/records_deduped.csv")
ALL_RECORDS_PATH = Path("data/records.csv")

TITLE_SIMILARITY_THRESHOLD = 93


COLUMN_ALIASES = {
    "title": [
        "title",
        "dc:title",
        "document title",
        "document_title",
    ],
    "abstract": [
        "abstract",
        "description",
        "dc:description",
    ],
    "doi": [
        "doi",
        "prism:doi",
    ],
    "year": [
        "year",
        "publication_year",
        "pubyear",
        "prism:coverdate",
        "publication_date",
    ],
    "authors": [
        "authors",
        "author",
        "dc:creator",
        "author_names",
    ],
    "journal": [
        "journal",
        "source title",
        "source_title",
        "publicationname",
        "prism:publicationname",
    ],
    "scopus_id": [
        "scopus_id",
        "scopus id",
        "dc:identifier",
    ],
}


def normalise_column_name(name: str) -> str:
    return str(name).strip().lower().replace("_", " ")


def find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    normalised_columns = {
        normalise_column_name(column): column
        for column in df.columns
    }

    for alias in aliases:
        key = normalise_column_name(alias)
        if key in normalised_columns:
            return normalised_columns[key]

    return None


def get_series(df: pd.DataFrame, aliases: list[str]) -> pd.Series:
    column = find_column(df, aliases)

    if column is None:
        return pd.Series([""] * len(df), index=df.index)

    return df[column].fillna("").astype(str)


def normalise_doi(value: str) -> str:
    value = str(value or "").strip().lower()
    value = value.replace("https://doi.org/", "")
    value = value.replace("http://doi.org/", "")
    value = value.replace("doi:", "")
    return value.strip()


def normalise_title(value: str) -> str:
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalise_year(value: str) -> str:
    match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
    return match.group(0) if match else ""


def clean_scopus_id(value: str) -> str:
    value = str(value or "").strip()
    return value.replace("SCOPUS_ID:", "").strip()


def load_raw_files() -> pd.DataFrame:
    files = list(RAW_DIR.glob("*.csv")) + list(RAW_DIR.glob("*.xlsx"))

    if not files:
        raise FileNotFoundError(
            "No CSV or XLSX files found in data/raw/"
        )

    frames = []

    for file_path in files:
        print(f"Reading: {file_path.name}")

        if file_path.suffix.lower() == ".csv":
            raw_df = pd.read_csv(file_path, dtype=str)
        else:
            raw_df = pd.read_excel(file_path, dtype=str)

        standardised = pd.DataFrame(
            {
                "title": get_series(raw_df, COLUMN_ALIASES["title"]),
                "abstract": get_series(raw_df, COLUMN_ALIASES["abstract"]),
                "doi": get_series(raw_df, COLUMN_ALIASES["doi"]),
                "year": get_series(raw_df, COLUMN_ALIASES["year"]),
                "authors": get_series(raw_df, COLUMN_ALIASES["authors"]),
                "journal": get_series(raw_df, COLUMN_ALIASES["journal"]),
                "scopus_id": (
                    get_series(raw_df, COLUMN_ALIASES["scopus_id"])
                    .apply(clean_scopus_id)
                ),
            }
        )

        standardised["source"] = file_path.stem
        standardised["source_file"] = file_path.name

        frames.append(standardised)

    return pd.concat(frames, ignore_index=True)


def assign_record_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["record_id"] = [
        f"R{i:06d}"
        for i in range(1, len(df) + 1)
    ]
    return df


def mark_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["doi_normalised"] = df["doi"].apply(normalise_doi)
    df["title_normalised"] = df["title"].apply(normalise_title)
    df["year_normalised"] = df["year"].apply(normalise_year)

    df["duplicate_of"] = ""
    df["dedupe_reason"] = ""

    doi_to_canonical_id = {}
    canonical_records = []

    for index, row in df.iterrows():
        doi = row["doi_normalised"]
        title = row["title_normalised"]
        year = row["year_normalised"]
        record_id = row["record_id"]

        if doi:
            if doi in doi_to_canonical_id:
                df.at[index, "duplicate_of"] = doi_to_canonical_id[doi]
                df.at[index, "dedupe_reason"] = "same_doi"
                continue

            doi_to_canonical_id[doi] = record_id
            canonical_records.append(
                {
                    "record_id": record_id,
                    "title": title,
                    "year": year,
                }
            )
            continue

        for canonical in canonical_records:
            similarity = fuzz.token_set_ratio(
                title,
                canonical["title"],
            )

            same_or_close_year = (
                not year
                or not canonical["year"]
                or abs(int(year) - int(canonical["year"])) <= 1
            )

            if (
                similarity >= TITLE_SIMILARITY_THRESHOLD
                and same_or_close_year
            ):
                df.at[index, "duplicate_of"] = canonical["record_id"]
                df.at[index, "dedupe_reason"] = (
                    f"title_similarity_{similarity:.0f}"
                )
                break

        if not df.at[index, "duplicate_of"]:
            canonical_records.append(
                {
                    "record_id": record_id,
                    "title": title,
                    "year": year,
                }
            )

    return df


def merge_source_information(df: pd.DataFrame) -> pd.DataFrame:
    """
    For records with the same DOI, preserve source provenance
    by joining source names onto the canonical record.
    """
    df = df.copy()

    canonical_sources = {}
    canonical_scopus_ids = {}

    for _, row in df.iterrows():
        canonical_id = row["duplicate_of"] or row["record_id"]

        canonical_sources.setdefault(canonical_id, set())
        canonical_sources[canonical_id].add(row["source"])

        scopus_id = str(row.get("scopus_id", "") or "").strip()
        if scopus_id:
            canonical_scopus_ids.setdefault(canonical_id, set())
            canonical_scopus_ids[canonical_id].add(scopus_id)

    df["all_sources"] = df["record_id"].apply(
        lambda record_id: "; ".join(
            sorted(canonical_sources.get(record_id, []))
        )
    )

    df["scopus_id"] = df["record_id"].apply(
        lambda record_id: "; ".join(
            sorted(canonical_scopus_ids.get(record_id, []))
        )
    )

    return df


def main() -> None:
    all_records = load_raw_files()
    all_records = assign_record_ids(all_records)
    all_records = mark_duplicates(all_records)
    all_records = merge_source_information(all_records)

    ALL_RECORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_records.to_csv(
        ALL_RECORDS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    deduped = all_records[
        all_records["duplicate_of"] == ""
    ].copy()

    deduped["screen_status"] = "unscreened"
    deduped["screen_decision"] = ""
    deduped["notes"] = ""

    deduped = deduped[
        [
            "record_id",
            "title",
            "abstract",
            "doi",
            "year",
            "authors",
            "journal",
            "scopus_id",
            "all_sources",
        ]
    ]

    deduped.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    duplicate_count = len(all_records) - len(deduped)

    print()
    print(f"Raw records: {len(all_records)}")
    print(f"Unique records: {len(deduped)}")
    print(f"Duplicates removed: {duplicate_count}")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
