"""
Import manual screening decisions exported from ASReview.

Input:
    data/records_with_abstracts.csv
    data/asreview_results.csv

Output:
    data/records_screened.csv
        All candidate records with screening status and decision.

    data/included_records.csv
        Subset of records marked as included.

Main processing steps:
    1. Load the internal candidate dataset.
    2. Load the ASReview export file.
    3. Match records using record_id.
    4. Update screening fields such as:
        - screen_status
        - screen_decision
        - screening_notes
    5. Save the complete screening audit table.
    6. Export included records for full-text review or analysis.

Important:
    ASReview export column names may vary by version.
    This script may need to map fields such as label, decision,
    relevant, or included into screen_decision.
"""