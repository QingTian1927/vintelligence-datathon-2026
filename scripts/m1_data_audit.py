from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd


@dataclass
class CheckResult:
    check_group: str
    check_name: str
    status: str
    details: str


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs" / "tables"
REPORT_PATH = (
    ROOT
    / "docs"
    / "competition"
    / "first-round"
    / "planning"
    / "m1-data-audit-report.md"
)

DATE_COLUMNS: Dict[str, List[str]] = {
    "customers.csv": ["signup_date"],
    "promotions.csv": ["start_date", "end_date"],
    "orders.csv": ["order_date"],
    "shipments.csv": ["ship_date", "delivery_date"],
    "returns.csv": ["return_date"],
    "reviews.csv": ["review_date"],
    "sales.csv": ["Date"],
    "inventory.csv": ["snapshot_date"],
    "web_traffic.csv": ["date"],
    "sample_submission.csv": ["Date"],
}

EXPECTED_NULL_COLUMNS = {
    ("customers.csv", "gender"),
    ("customers.csv", "age_group"),
    ("customers.csv", "acquisition_channel"),
    ("promotions.csv", "applicable_category"),
    ("promotions.csv", "promo_channel"),
    ("promotions.csv", "min_order_value"),
    ("order_items.csv", "promo_id"),
    ("order_items.csv", "promo_id_2"),
}

PRIMARY_KEYS = {
    "products.csv": ["product_id"],
    "customers.csv": ["customer_id"],
    "promotions.csv": ["promo_id"],
    "geography.csv": ["zip"],
    "orders.csv": ["order_id"],
    "payments.csv": ["order_id"],
    "shipments.csv": ["order_id"],
    "returns.csv": ["return_id"],
    "reviews.csv": ["review_id"],
    "sales.csv": ["Date"],
    "inventory.csv": ["snapshot_date", "product_id"],
}

FK_CHECKS = [
    ("customers.csv", "zip", "geography.csv", "zip", True),
    ("orders.csv", "customer_id", "customers.csv", "customer_id", True),
    ("orders.csv", "zip", "geography.csv", "zip", True),
    ("order_items.csv", "order_id", "orders.csv", "order_id", True),
    ("order_items.csv", "product_id", "products.csv", "product_id", True),
    ("order_items.csv", "promo_id", "promotions.csv", "promo_id", False),
    ("order_items.csv", "promo_id_2", "promotions.csv", "promo_id", False),
    ("payments.csv", "order_id", "orders.csv", "order_id", True),
    ("shipments.csv", "order_id", "orders.csv", "order_id", True),
    ("returns.csv", "order_id", "orders.csv", "order_id", True),
    ("returns.csv", "product_id", "products.csv", "product_id", True),
    ("reviews.csv", "order_id", "orders.csv", "order_id", True),
    ("reviews.csv", "product_id", "products.csv", "product_id", True),
    ("reviews.csv", "customer_id", "customers.csv", "customer_id", True),
    ("inventory.csv", "product_id", "products.csv", "product_id", True),
]


def load_tables() -> Dict[str, pd.DataFrame]:
    tables: Dict[str, pd.DataFrame] = {}
    for file in sorted(DATA_DIR.glob("*.csv")):
        tables[file.name] = pd.read_csv(file, low_memory=False)
    return tables


def date_only_has_time_component(series: pd.Series) -> bool:
    s = series.dropna().astype(str)
    if s.empty:
        return False
    return s.str.contains(r"\d{2}:\d{2}|T\d{2}", regex=True).any()


def make_schema_summary(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for file_name, df in tables.items():
        for col in df.columns:
            non_null = int(df[col].notna().sum())
            null_count = int(df[col].isna().sum())
            rows.append(
                {
                    "file": file_name,
                    "column": col,
                    "dtype": str(df[col].dtype),
                    "rows": len(df),
                    "non_null": non_null,
                    "null_count": null_count,
                    "null_pct": round(null_count / len(df) * 100, 4) if len(df) else 0.0,
                    "nunique": int(df[col].nunique(dropna=True)),
                }
            )
    return pd.DataFrame(rows)


def make_missing_summary(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for file_name, df in tables.items():
        for col in df.columns:
            null_count = int(df[col].isna().sum())
            if null_count == 0:
                continue
            rows.append(
                {
                    "file": file_name,
                    "column": col,
                    "null_count": null_count,
                    "null_pct": round(null_count / len(df) * 100, 4),
                    "classification": "expected_business_null"
                    if (file_name, col) in EXPECTED_NULL_COLUMNS
                    else "suspicious_null",
                }
            )
    return pd.DataFrame(rows)


def make_duplicate_summary(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for file_name, df in tables.items():
        rows.append(
            {
                "file": file_name,
                "duplicate_type": "full_row_duplicate",
                "columns": "*",
                "duplicate_count": int(df.duplicated().sum()),
            }
        )
        if file_name in PRIMARY_KEYS:
            key_cols = PRIMARY_KEYS[file_name]
            dup_count = int(df.duplicated(subset=key_cols).sum())
            rows.append(
                {
                    "file": file_name,
                    "duplicate_type": "primary_key_duplicate",
                    "columns": ",".join(key_cols),
                    "duplicate_count": dup_count,
                }
            )
    return pd.DataFrame(rows)


def make_date_summary(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for file_name, date_cols in DATE_COLUMNS.items():
        if file_name not in tables:
            continue
        df = tables[file_name]
        for col in date_cols:
            if col not in df.columns:
                continue
            parsed = pd.to_datetime(df[col], errors="coerce")
            rows.append(
                {
                    "file": file_name,
                    "column": col,
                    "min_date": parsed.min().date().isoformat() if parsed.notna().any() else "",
                    "max_date": parsed.max().date().isoformat() if parsed.notna().any() else "",
                    "parse_fail_count": int(parsed.isna().sum() - df[col].isna().sum()),
                    "has_time_component": bool(date_only_has_time_component(df[col])),
                }
            )
    return pd.DataFrame(rows)


def add_check(results: List[CheckResult], group: str, name: str, passed: bool, details: str) -> None:
    results.append(
        CheckResult(
            check_group=group,
            check_name=name,
            status="PASS" if passed else "FAIL",
            details=details,
        )
    )


def run_constraint_checks(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    results: List[CheckResult] = []

    products = tables["products.csv"]
    invalid_margin = int((products["cogs"] >= products["price"]).sum())
    add_check(
        results,
        "constraint",
        "products.cogs_lt_price",
        invalid_margin == 0,
        f"invalid_rows={invalid_margin}",
    )

    promotions = tables["promotions.csv"]
    promo_start = pd.to_datetime(promotions["start_date"], errors="coerce")
    promo_end = pd.to_datetime(promotions["end_date"], errors="coerce")
    invalid_dates = int((promo_start > promo_end).sum())
    add_check(
        results,
        "constraint",
        "promotions.start_le_end",
        invalid_dates == 0,
        f"invalid_rows={invalid_dates}",
    )

    shipments = tables["shipments.csv"]
    ship_date = pd.to_datetime(shipments["ship_date"], errors="coerce")
    delivery_date = pd.to_datetime(shipments["delivery_date"], errors="coerce")
    invalid_ship = int((delivery_date < ship_date).sum())
    add_check(
        results,
        "constraint",
        "shipments.delivery_ge_ship",
        invalid_ship == 0,
        f"invalid_rows={invalid_ship}",
    )

    reviews = tables["reviews.csv"]
    invalid_rating = int((~reviews["rating"].between(1, 5, inclusive="both")).sum())
    add_check(
        results,
        "constraint",
        "reviews.rating_1_to_5",
        invalid_rating == 0,
        f"invalid_rows={invalid_rating}",
    )

    inventory = tables["inventory.csv"]
    invalid_fill_rate = int(((inventory["fill_rate"] < 0) | (inventory["fill_rate"] > 1)).sum())
    add_check(
        results,
        "constraint",
        "inventory.fill_rate_0_to_1",
        invalid_fill_rate == 0,
        f"invalid_rows={invalid_fill_rate}",
    )

    web = tables["web_traffic.csv"]
    invalid_bounce = int(((web["bounce_rate"] < 0) | (web["bounce_rate"] > 1)).sum())
    add_check(
        results,
        "constraint",
        "web_traffic.bounce_rate_0_to_1",
        invalid_bounce == 0,
        f"invalid_rows={invalid_bounce}",
    )

    if "conversion_rate" in web.columns:
        invalid_conversion = int(((web["conversion_rate"] < 0) | (web["conversion_rate"] > 1)).sum())
        add_check(
            results,
            "constraint",
            "web_traffic.conversion_rate_0_to_1",
            invalid_conversion == 0,
            f"invalid_rows={invalid_conversion}",
        )

    return pd.DataFrame([r.__dict__ for r in results])


def run_fk_checks(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for src_file, src_col, tgt_file, tgt_col, required in FK_CHECKS:
        src = tables[src_file][src_col]
        tgt_values = set(tables[tgt_file][tgt_col].dropna().astype(str))
        src_series = src.dropna() if not required else src
        src_values = src_series.astype(str)
        invalid_mask = ~src_values.isin(tgt_values)
        invalid_count = int(invalid_mask.sum())
        checked_rows = int(src_values.shape[0])
        rows.append(
            {
                "src_file": src_file,
                "src_column": src_col,
                "tgt_file": tgt_file,
                "tgt_column": tgt_col,
                "required_fk": required,
                "checked_rows": checked_rows,
                "invalid_fk_count": invalid_count,
                "status": "PASS" if invalid_count == 0 else "FAIL",
            }
        )
    return pd.DataFrame(rows)


def run_cardinality_checks(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    results: List[CheckResult] = []

    orders = tables["orders.csv"]
    payments = tables["payments.csv"]
    shipments = tables["shipments.csv"]
    returns = tables["returns.csv"]
    reviews = tables["reviews.csv"]

    # orders <-> payments: 1:1
    order_ids = set(orders["order_id"].astype(str))
    payment_ids = set(payments["order_id"].astype(str))
    missing_payments = len(order_ids - payment_ids)
    extra_payments = len(payment_ids - order_ids)
    payment_dup = int(payments.duplicated(subset=["order_id"]).sum())
    pass_1to1 = missing_payments == 0 and extra_payments == 0 and payment_dup == 0
    add_check(
        results,
        "cardinality",
        "orders_payments_1_to_1",
        pass_1to1,
        f"missing_payments={missing_payments}; extra_payments={extra_payments}; payment_duplicates={payment_dup}",
    )

    # orders <-> shipments: 1:0/1
    shipment_dup = int(shipments.duplicated(subset=["order_id"]).sum())
    invalid_ship_links = int((~shipments["order_id"].astype(str).isin(order_ids)).sum())
    pass_ship = shipment_dup == 0 and invalid_ship_links == 0
    add_check(
        results,
        "cardinality",
        "orders_shipments_1_to_0_or_1",
        pass_ship,
        f"shipment_duplicates={shipment_dup}; invalid_links={invalid_ship_links}",
    )

    # shipped/delivered/returned should exist in shipments
    expected_status = {"shipped", "delivered", "returned"}
    status_mask = orders["order_status"].astype(str).str.lower().isin(expected_status)
    required_ship_orders = set(orders.loc[status_mask, "order_id"].astype(str))
    ship_ids = set(shipments["order_id"].astype(str))
    missing_required_shipments = len(required_ship_orders - ship_ids)
    add_check(
        results,
        "cardinality",
        "orders_status_requires_shipments",
        missing_required_shipments == 0,
        f"missing_required_shipments={missing_required_shipments}",
    )

    # orders <-> returns: 1:0+ and usually returned status
    invalid_return_links = int((~returns["order_id"].astype(str).isin(order_ids)).sum())
    returned_status_ids = set(
        orders.loc[orders["order_status"].astype(str).str.lower() == "returned", "order_id"].astype(str)
    )
    non_returned_with_return = int((~returns["order_id"].astype(str).isin(returned_status_ids)).sum())
    add_check(
        results,
        "cardinality",
        "orders_returns_1_to_0_or_many",
        invalid_return_links == 0,
        f"invalid_links={invalid_return_links}",
    )
    add_check(
        results,
        "cardinality",
        "returns_should_map_to_returned_orders",
        non_returned_with_return == 0,
        f"mismatch_count={non_returned_with_return}",
    )

    # orders <-> reviews: 1:0+ and should be delivered
    invalid_review_links = int((~reviews["order_id"].astype(str).isin(order_ids)).sum())
    delivered_status_ids = set(
        orders.loc[orders["order_status"].astype(str).str.lower() == "delivered", "order_id"].astype(str)
    )
    non_delivered_with_review = int((~reviews["order_id"].astype(str).isin(delivered_status_ids)).sum())
    add_check(
        results,
        "cardinality",
        "orders_reviews_1_to_0_or_many",
        invalid_review_links == 0,
        f"invalid_links={invalid_review_links}",
    )
    add_check(
        results,
        "cardinality",
        "reviews_should_map_to_delivered_orders",
        non_delivered_with_review == 0,
        f"mismatch_count={non_delivered_with_review}",
    )

    # products <-> inventory: one row per product per month
    inventory = tables["inventory.csv"]
    inv_dup = int(inventory.duplicated(subset=["snapshot_date", "product_id"]).sum())
    add_check(
        results,
        "cardinality",
        "products_inventory_one_row_per_product_month",
        inv_dup == 0,
        f"duplicate_rows={inv_dup}",
    )

    return pd.DataFrame([r.__dict__ for r in results])


def leakage_watchlist() -> pd.DataFrame:
    rows = [
        {
            "risk_id": "L1",
            "applies_to": "forecasting",
            "risk": "Using future dates in lag/rolling features during CV or train.",
            "prevention": "Use strictly time-ordered folds and feature generation with cutoff date guards.",
            "severity": "critical",
        },
        {
            "risk_id": "L2",
            "applies_to": "forecasting",
            "risk": "Using target columns Revenue/COGS from hidden test period in feature engineering.",
            "prevention": "Generate features only from training horizon; never ingest hidden test targets.",
            "severity": "critical",
        },
        {
            "risk_id": "L3",
            "applies_to": "forecasting",
            "risk": "Random CV instead of time-based CV causing lookahead bias.",
            "prevention": "Use temporal backtesting windows with expanding or rolling origin.",
            "severity": "critical",
        },
        {
            "risk_id": "L4",
            "applies_to": "forecasting",
            "risk": "Aggregates built with full-table data including future periods.",
            "prevention": "Build cumulative statistics using only data available up to prediction date.",
            "severity": "high",
        },
        {
            "risk_id": "L5",
            "applies_to": "mcq",
            "risk": "Incorrect joins multiplying rows and distorting denominators.",
            "prevention": "Validate join cardinality and aggregate at intended grain before computing answer.",
            "severity": "high",
        },
        {
            "risk_id": "L6",
            "applies_to": "mcq",
            "risk": "Using nullable promo columns as mandatory relationships.",
            "prevention": "Treat nullable promotion fields as optional and exclude nulls only when required.",
            "severity": "medium",
        },
        {
            "risk_id": "L7",
            "applies_to": "all",
            "risk": "Schema drift assumptions between brief and actual CSV files.",
            "prevention": "Run schema checks at script start and fail fast on missing/renamed columns.",
            "severity": "high",
        },
        {
            "risk_id": "L8",
            "applies_to": "all",
            "risk": "Violating competition rule by using external data.",
            "prevention": "Restrict inputs to provided CSV files only and document file lineage.",
            "severity": "critical",
        },
    ]
    return pd.DataFrame(rows)


def write_markdown_report(
    schema_df: pd.DataFrame,
    missing_df: pd.DataFrame,
    duplicate_df: pd.DataFrame,
    date_df: pd.DataFrame,
    constraint_df: pd.DataFrame,
    fk_df: pd.DataFrame,
    card_df: pd.DataFrame,
) -> None:
    fail_constraints = constraint_df[constraint_df["status"] == "FAIL"]
    fail_fk = fk_df[fk_df["status"] == "FAIL"]
    fail_card = card_df[card_df["status"] == "FAIL"]

    suspicious_nulls = missing_df[missing_df["classification"] == "suspicious_null"]

    lines = [
        "# Milestone 1 - Data Audit Report",
        "",
        "## Scope",
        "- Deep audit of provided competition CSV files only.",
        "- Checks include schema, nulls, duplicates, date ranges, constraints, FK integrity, and cardinality.",
        "- Date columns treated as date-only.",
        "",
        "## Dataset Coverage",
        f"- Files audited: {schema_df['file'].nunique()}",
        f"- Total rows across files: {int(schema_df.groupby('file')['rows'].max().sum())}",
        f"- Total columns audited: {len(schema_df)}",
        "",
        "## Null Quality Classification",
        f"- Columns with missing values: {missing_df[['file','column']].drop_duplicates().shape[0]}",
        f"- Expected-business-null columns: {int((missing_df['classification'] == 'expected_business_null').sum())}",
        f"- Suspicious-null columns: {int((missing_df['classification'] == 'suspicious_null').sum())}",
        "",
    ]

    if not suspicious_nulls.empty:
        lines.append("### Suspicious Null Findings")
        for _, r in suspicious_nulls.sort_values(["file", "column"]).iterrows():
            lines.append(
                f"- {r['file']}::{r['column']} -> {int(r['null_count'])} nulls ({r['null_pct']}%)"
            )
        lines.append("")

    lines.extend(
        [
            "## Duplicate and Key Checks",
            f"- Full-row duplicate checks executed on all files: {duplicate_df[duplicate_df['duplicate_type'] == 'full_row_duplicate'].shape[0]}",
            f"- Primary-key duplicate checks executed: {duplicate_df[duplicate_df['duplicate_type'] == 'primary_key_duplicate'].shape[0]}",
            "",
            "## Date Quality",
            f"- Date columns checked: {len(date_df)}",
            f"- Columns with parse failures: {int((date_df['parse_fail_count'] > 0).sum())}",
            f"- Columns with time components detected: {int(date_df['has_time_component'].sum())}",
            "",
            "## Strict Integrity Check Results",
            f"- Constraint checks failed: {len(fail_constraints)} / {len(constraint_df)}",
            f"- FK checks failed: {len(fail_fk)} / {len(fk_df)}",
            f"- Cardinality checks failed: {len(fail_card)} / {len(card_df)}",
            "",
        ]
    )

    if not fail_constraints.empty:
        lines.append("### Failed Constraint Checks")
        for _, r in fail_constraints.iterrows():
            lines.append(f"- {r['check_name']}: {r['details']}")
        lines.append("")

    if not fail_fk.empty:
        lines.append("### Failed FK Checks")
        for _, r in fail_fk.iterrows():
            lines.append(
                f"- {r['src_file']}::{r['src_column']} -> {r['tgt_file']}::{r['tgt_column']}: invalid_fk_count={int(r['invalid_fk_count'])}"
            )
        lines.append("")

    if not fail_card.empty:
        lines.append("### Failed Cardinality Checks")
        for _, r in fail_card.iterrows():
            lines.append(f"- {r['check_name']}: {r['details']}")
        lines.append("")

    lines.extend(
        [
            "## Evidence Files",
            "- outputs/tables/m1_schema_summary.csv",
            "- outputs/tables/m1_missing_summary.csv",
            "- outputs/tables/m1_duplicate_summary.csv",
            "- outputs/tables/m1_date_range_summary.csv",
            "- outputs/tables/m1_constraint_checks.csv",
            "- outputs/tables/m1_fk_checks.csv",
            "- outputs/tables/m1_cardinality_checks.csv",
            "- outputs/tables/m1_leakage_watchlist.csv",
            "",
            "## Competition-Rule Alignment",
            "- Audit used only provided CSV files.",
            "- Leakage watchlist was produced for forecasting and MCQ workflows.",
            "- Strict checks are reported as PASS/FAIL for transparent reproducibility.",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tables = load_tables()

    schema_df = make_schema_summary(tables)
    missing_df = make_missing_summary(tables)
    duplicate_df = make_duplicate_summary(tables)
    date_df = make_date_summary(tables)
    constraint_df = run_constraint_checks(tables)
    fk_df = run_fk_checks(tables)
    card_df = run_cardinality_checks(tables)
    leakage_df = leakage_watchlist()

    schema_df.to_csv(OUT_DIR / "m1_schema_summary.csv", index=False)
    missing_df.to_csv(OUT_DIR / "m1_missing_summary.csv", index=False)
    duplicate_df.to_csv(OUT_DIR / "m1_duplicate_summary.csv", index=False)
    date_df.to_csv(OUT_DIR / "m1_date_range_summary.csv", index=False)
    constraint_df.to_csv(OUT_DIR / "m1_constraint_checks.csv", index=False)
    fk_df.to_csv(OUT_DIR / "m1_fk_checks.csv", index=False)
    card_df.to_csv(OUT_DIR / "m1_cardinality_checks.csv", index=False)
    leakage_df.to_csv(OUT_DIR / "m1_leakage_watchlist.csv", index=False)

    write_markdown_report(
        schema_df=schema_df,
        missing_df=missing_df,
        duplicate_df=duplicate_df,
        date_df=date_df,
        constraint_df=constraint_df,
        fk_df=fk_df,
        card_df=card_df,
    )

    total_failures = int((constraint_df["status"] == "FAIL").sum())
    total_failures += int((fk_df["status"] == "FAIL").sum())
    total_failures += int((card_df["status"] == "FAIL").sum())

    print(f"Milestone 1 audit completed. Total strict-check failures: {total_failures}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
