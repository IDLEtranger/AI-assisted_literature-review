"""
Export ASReview relevant records for bibliometric analysis.

Input:
    data/asreview_results.csv

Output:
    data/included_records.csv

The first column in the ASReview export is treated as an extra row index.
Only records marked as included are exported.
"""

from pathlib import Path

import pandas as pd


INPUT_PATH = Path("data/asreview_results.csv")
OUTPUT_PATH = Path("data/included_records.csv")


def main() -> None:
    results = pd.read_csv(
        INPUT_PATH,
        dtype=str,
        encoding="utf-8-sig",
    ).fillna("")

    # Remove the first extra index column exported by ASReview.
    results = results.iloc[:, 1:]

    # Remove BOM and whitespace from column names.
    results.columns = (
        results.columns
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    required_columns = [
        "title",
        "abstract",
        "doi",
        "year",
        "authors",
        "journal",
        "included",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in results.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Keep records marked as included by ASReview.
    included_values = {
        "1",
        "true",
        "yes",
        "relevant",
        "include",
        "included",
    }

    included_records = results[
        results["included"]
        .str.strip()
        .str.lower()
        .isin(included_values)
    ].copy()

    output_columns = [
        "title",
        "abstract",
        "doi",
        "year",
        "authors",
        "journal",
    ]

    included_records = included_records[output_columns]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    included_records.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Included records: {len(included_records)}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()