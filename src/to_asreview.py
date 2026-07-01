from pathlib import Path

import pandas as pd

"""
Prepare a clean screening dataset for ASReview.

Input:
    data/records_with_abstracts.csv

Output:
    data/asreview_input.csv

Main processing steps:
    1. Load the enriched deduplicated dataset.
    2. Keep fields useful for title-and-abstract screening:
        - record_id
        - title
        - abstract
        - doi
        - year
        - authors
        - journal
    3. Remove records without titles.
    4. Export a UTF-8 CSV file for upload into ASReview LAB.

Important:
    Do not modify record_id values.
    record_id is required to match ASReview decisions back to internal records.
"""

INPUT_PATH = Path("data/records_enriched.csv")
OUTPUT_PATH = Path("data/asreview_input.csv")


def main() -> None:
    df = pd.read_csv(INPUT_PATH, dtype=str).fillna("")

    required_columns = [
        "record_id",
        "title",
        "abstract",
        "doi",
        "year",
        "authors",
        "journal",
    ]

    for column in required_columns:
        if column not in df.columns:
            df[column] = ""

    asreview_df = df[required_columns].copy()

    asreview_df = asreview_df[
        asreview_df["title"].str.strip() != ""
    ].copy()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    asreview_df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    records_without_abstract = (
        asreview_df["abstract"].str.strip() == ""
    ).sum()

    print(f"Exported {len(asreview_df)} records to {OUTPUT_PATH}")
    print(
        f"Records without abstracts: "
        f"{records_without_abstract}"
    )


if __name__ == "__main__":
    main()