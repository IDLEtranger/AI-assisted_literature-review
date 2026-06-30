# Literature Review Tool

A minimal local workflow for collecting, deduplicating, enriching, screening, and exporting literature records.

## Project Structure

```text
lit-review-tool/
├── data/
│   ├── raw/
│   ├── records.csv
│   ├── records_deduped.csv
│   ├── records_with_abstracts.csv
│   ├── asreview_input.csv
│   ├── asreview_results.csv
│   ├── records_screened.csv
│   └── included_records.csv
├── src/
│   ├── merge_and_dedupe.py
│   ├── enrich_abstracts.py
│   ├── export_asreview.py
│   ├── import_asreview.py
│   └── export_analysis.py
├── .env
└── .gitignore

Raw search results
(data/raw/*.csv)
        ↓
        ↓   merge_and_dedupe.py
        ↓
records.csv
All imported records, including duplicates.
records_deduped.csv
Unique candidate records after DOI and title-based deduplication.
        ↓
        ↓   enrich_raw.py
        ↓
records_enriched.csv
Deduplicated records with missing columns enriched when possible.
        ↓
        ↓   export_asreview.py
        ↓
asreview_input.csv
Clean screening dataset uploaded to ASReview.
        ↓
        ↓   Manual screening in ASReview
        ↓
asreview_results.csv
Screening decisions exported from ASReview.
        ↓
        ↓   import_asreview.py
        ↓
records_screened.csv
All records with screening decisions.
        ↓
included_records.csv
Records marked as included and ready for full-text review or analysis.
        ↓
        ↓   export_analysis.py
        ↓
Biblium / VOSviewer / Python analysis outputs
```

| File                         | Purpose                                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------------------------ |
| `data/raw/`                  | Original exports from Scopus, OpenAlex, PubMed, ScholarFlux, or other sources. Do not modify manually. |
| `records.csv`                | Combined raw records, including duplicates.                                                            |
| `records_deduped.csv`        | Unique records after deduplication.                                                                    |
| `records_with_abstracts.csv` | Deduplicated records with abstracts enriched where possible.                                           |
| `asreview_input.csv`         | Input file uploaded to ASReview.                                                                       |
| `asreview_results.csv`       | Manual screening results exported from ASReview.                                                       |
| `records_screened.csv`       | All records with include/exclude decisions.                                                            |
| `included_records.csv`       | Included records for full-text review and bibliometric analysis.                                       |

## table format

**scopus.csv**
title,abstract,doi,year,authors,journal,document_type,scopus_id,eid,cited_by_count,source,source_url

**record.csv**
title,abstract,doi,year,authors,journal,scopus_id,source,source_file,record_id,doi_normalised,title_normalised,year_normalised,duplicate_of,dedupe_reason,all_sources

**record_deduped.csv**
record_id,title,abstract,doi,year,authors,journal,scopus_id,all_sources,screen_status,screen_decision,notes

**record_enriched.csv**
record_id,title,abstract,doi,year,authors,journal,scopus_id,all_sources,screen_status,screen_decision,notes
