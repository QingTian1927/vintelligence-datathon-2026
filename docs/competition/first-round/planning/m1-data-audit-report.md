# Milestone 1 - Data Audit Report

## Scope
- Deep audit of provided competition CSV files only.
- Checks include schema, nulls, duplicates, date ranges, constraints, FK integrity, and cardinality.
- Date columns treated as date-only.

## Dataset Coverage
- Files audited: 14
- Total rows across files: 2960736
- Total columns audited: 96

## Null Quality Classification
- Columns with missing values: 3
- Expected-business-null columns: 3
- Suspicious-null columns: 0

## Duplicate and Key Checks
- Full-row duplicate checks executed on all files: 14
- Primary-key duplicate checks executed: 11

## Date Quality
- Date columns checked: 12
- Columns with parse failures: 0
- Columns with time components detected: 0

## Strict Integrity Check Results
- Constraint checks failed: 0 / 6
- FK checks failed: 0 / 15
- Cardinality checks failed: 1 / 8

### Failed Cardinality Checks
- orders_status_requires_shipments: missing_required_shipments=564

## Evidence Files
- outputs/tables/m1_schema_summary.csv
- outputs/tables/m1_missing_summary.csv
- outputs/tables/m1_duplicate_summary.csv
- outputs/tables/m1_date_range_summary.csv
- outputs/tables/m1_constraint_checks.csv
- outputs/tables/m1_fk_checks.csv
- outputs/tables/m1_cardinality_checks.csv
- outputs/tables/m1_leakage_watchlist.csv

## Competition-Rule Alignment
- Audit used only provided CSV files.
- Leakage watchlist was produced for forecasting and MCQ workflows.
- Strict checks are reported as PASS/FAIL for transparent reproducibility.