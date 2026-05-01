from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs" / "tables"
PLAN_DIR = ROOT / "docs" / "competition" / "first-round" / "planning"


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, low_memory=False)


def nearest_option(value: float, options: dict[str, float]) -> tuple[str, float]:
    distances = {k: abs(value - v) for k, v in options.items()}
    best = min(distances, key=distances.get)
    return best, distances[best]


def q1(orders: pd.DataFrame) -> dict:
    d = orders[["customer_id", "order_date"]].copy()
    d["order_date"] = pd.to_datetime(d["order_date"], errors="coerce")
    d = d.sort_values(["customer_id", "order_date"])
    d["gap_days"] = d.groupby("customer_id")["order_date"].diff().dt.days
    multi_customers = d.groupby("customer_id").size()
    multi_customers = set(multi_customers[multi_customers > 1].index)
    gaps = d.loc[d["customer_id"].isin(multi_customers), "gap_days"].dropna()
    value = float(gaps.median())
    options = {"A": 30.0, "B": 90.0, "C": 144.0, "D": 365.0}
    chosen, dist = nearest_option(value, options)
    return {
        "question": "Q1",
        "metric": "median_inter_order_gap_days",
        "value": round(value, 4),
        "option": chosen,
        "distance": round(dist, 4),
        "detail": f"num_gaps={len(gaps)}",
    }


def q2(products: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    d = products[["segment", "price", "cogs"]].copy()
    d["margin_rate"] = (d["price"] - d["cogs"]) / d["price"]
    ranking = (
        d.groupby("segment", as_index=False)
        .agg(avg_margin_rate=("margin_rate", "mean"), n_products=("margin_rate", "size"))
        .sort_values("avg_margin_rate", ascending=False)
    )
    top = str(ranking.iloc[0]["segment"])
    option_map = {"Premium": "A", "Performance": "B", "Activewear": "C", "Standard": "D"}
    chosen = option_map[top]
    return (
        {
            "question": "Q2",
            "metric": "highest_avg_margin_segment",
            "value": round(float(ranking.iloc[0]["avg_margin_rate"]), 4),
            "option": chosen,
            "distance": 0.0,
            "detail": top,
        },
        ranking,
    )


def q3(returns: pd.DataFrame, products: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    d = returns.merge(products[["product_id", "category"]], on="product_id", how="inner")
    d = d[d["category"].astype(str) == "Streetwear"]
    freq = d.groupby("return_reason", as_index=False).size().sort_values("size", ascending=False)
    top = str(freq.iloc[0]["return_reason"])
    option_map = {
        "defective": "A",
        "wrong_size": "B",
        "changed_mind": "C",
        "not_as_described": "D",
    }
    chosen = option_map[top]
    return (
        {
            "question": "Q3",
            "metric": "most_common_streetwear_return_reason",
            "value": float(freq.iloc[0]["size"]),
            "option": chosen,
            "distance": 0.0,
            "detail": top,
        },
        freq,
    )


def q4(web: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    d = (
        web.groupby("traffic_source", as_index=False)
        .agg(avg_bounce_rate=("bounce_rate", "mean"), n_days=("bounce_rate", "size"))
        .sort_values("avg_bounce_rate", ascending=True)
    )
    top = str(d.iloc[0]["traffic_source"])
    option_map = {
        "organic_search": "A",
        "paid_search": "B",
        "email_campaign": "C",
        "social_media": "D",
    }
    chosen = option_map[top]
    return (
        {
            "question": "Q4",
            "metric": "lowest_avg_bounce_source",
            "value": round(float(d.iloc[0]["avg_bounce_rate"]), 4),
            "option": chosen,
            "distance": 0.0,
            "detail": top,
        },
        d,
    )


def q5(order_items: pd.DataFrame) -> dict:
    pct = float(order_items["promo_id"].notna().mean() * 100.0)
    options = {"A": 12.0, "B": 25.0, "C": 39.0, "D": 54.0}
    chosen, dist = nearest_option(pct, options)
    return {
        "question": "Q5",
        "metric": "pct_rows_with_promo_id",
        "value": round(pct, 4),
        "option": chosen,
        "distance": round(dist, 4),
        "detail": "promo_id is not null",
    }


def q6(customers: pd.DataFrame, orders: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    c = customers[["customer_id", "age_group"]].copy()
    c = c[c["age_group"].notna()].copy()
    order_counts = orders.groupby("customer_id", as_index=False).size().rename(columns={"size": "n_orders"})

    strict = c.merge(order_counts, on="customer_id", how="left")
    strict["n_orders"] = strict["n_orders"].fillna(0)
    strict_rank = (
        strict.groupby("age_group", as_index=False)
        .agg(avg_orders_per_customer=("n_orders", "mean"), n_customers=("customer_id", "nunique"))
        .sort_values("avg_orders_per_customer", ascending=False)
    )

    alt = c.merge(order_counts, on="customer_id", how="inner")
    alt_rank = (
        alt.groupby("age_group", as_index=False)
        .agg(avg_orders_per_customer=("n_orders", "mean"), n_customers=("customer_id", "nunique"))
        .sort_values("avg_orders_per_customer", ascending=False)
    )

    top = str(strict_rank.iloc[0]["age_group"])

    def to_option(age_group: str) -> str:
        s = age_group.strip()
        if s.startswith("55"):
            return "A"
        if s.startswith("25"):
            return "B"
        if s.startswith("35"):
            return "C"
        if s.startswith("45"):
            return "D"
        raise ValueError(f"Unexpected age_group value: {age_group}")

    chosen = to_option(top)
    return (
        {
            "question": "Q6",
            "metric": "highest_avg_orders_per_customer_by_age_group",
            "value": round(float(strict_rank.iloc[0]["avg_orders_per_customer"]), 4),
            "option": chosen,
            "distance": 0.0,
            "detail": f"strict_top={top}; alt_top={alt_rank.iloc[0]['age_group']}",
        },
        strict_rank,
        alt_rank,
    )


def q7(orders: pd.DataFrame, geography: pd.DataFrame, payments: pd.DataFrame, order_items: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    og = orders[["order_id", "zip"]].merge(geography[["zip", "region"]], on="zip", how="left")

    pay_based = og.merge(payments[["order_id", "payment_value"]], on="order_id", how="inner")
    pay_rank = pay_based.groupby("region", as_index=False).agg(total_revenue=("payment_value", "sum"))
    pay_rank = pay_rank.sort_values("total_revenue", ascending=False)

    item_agg = order_items.groupby("order_id", as_index=False).agg(order_item_revenue=("unit_price", "sum"))
    item_based = og.merge(item_agg, on="order_id", how="inner")
    item_rank = item_based.groupby("region", as_index=False).agg(total_revenue=("order_item_revenue", "sum"))
    item_rank = item_rank.sort_values("total_revenue", ascending=False)

    top_pay = str(pay_rank.iloc[0]["region"])
    top_item = str(item_rank.iloc[0]["region"])

    option_map = {"West": "A", "Central": "B", "East": "C"}

    pay_vals = pay_rank["total_revenue"].values
    approximately_equal = False
    if len(pay_vals) >= 3:
        approximately_equal = (float(pay_vals.max()) - float(pay_vals.min())) / float(pay_vals.max()) < 0.01

    if approximately_equal:
        chosen = "D"
        detail = "pay_based regions are approximately equal (<1% spread)"
    elif top_pay == top_item and top_pay in option_map:
        chosen = option_map[top_pay]
        detail = f"strict ambiguous; pay_top={top_pay}; item_top={top_item}; chose consensus"
    elif top_pay in option_map:
        chosen = option_map[top_pay]
        detail = f"strict ambiguous; pay_top={top_pay}; item_top={top_item}; chose payment-based"
    else:
        chosen = "D"
        detail = f"strict ambiguous; unexpected region labels: pay_top={top_pay}, item_top={top_item}"

    combined = pay_rank.rename(columns={"total_revenue": "pay_total_revenue"}).merge(
        item_rank.rename(columns={"total_revenue": "item_total_revenue"}), on="region", how="outer"
    )

    top_value = float(pay_rank.iloc[0]["total_revenue"])
    return (
        {
            "question": "Q7",
            "metric": "highest_total_revenue_region_ambiguous_definition",
            "value": round(top_value, 4),
            "option": chosen,
            "distance": 0.0,
            "detail": detail,
        },
        combined.sort_values("pay_total_revenue", ascending=False),
    )


def q8(orders: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    d = orders[orders["order_status"].astype(str).str.lower() == "cancelled"].copy()
    freq = d.groupby("payment_method", as_index=False).size().sort_values("size", ascending=False)
    top = str(freq.iloc[0]["payment_method"]) if not freq.empty else ""
    option_map = {"credit_card": "A", "cod": "B", "paypal": "C", "bank_transfer": "D"}
    chosen = option_map[top]
    return (
        {
            "question": "Q8",
            "metric": "most_used_payment_method_in_cancelled_orders",
            "value": float(freq.iloc[0]["size"]),
            "option": chosen,
            "distance": 0.0,
            "detail": top,
        },
        freq,
    )


def q9(returns: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    p = products[["product_id", "size"]].copy()

    num = (
        returns.merge(p, on="product_id", how="left")
        .groupby("size")
        .size()
        .reset_index(name="return_records")
    )
    den = (
        order_items.merge(p, on="product_id", how="left")
        .groupby("size")
        .size()
        .reset_index(name="order_item_rows")
    )

    merged = num.merge(den, on="size", how="outer").fillna(0)
    merged["return_rate"] = np.where(
        merged["order_item_rows"] > 0, merged["return_records"] / merged["order_item_rows"], np.nan
    )
    merged = merged.sort_values("return_rate", ascending=False)

    top_size = str(merged.iloc[0]["size"])
    option_map = {"S": "A", "M": "B", "L": "C", "XL": "D"}
    chosen = option_map[top_size]
    return (
        {
            "question": "Q9",
            "metric": "highest_return_rate_by_size",
            "value": round(float(merged.iloc[0]["return_rate"]), 4),
            "option": chosen,
            "distance": 0.0,
            "detail": top_size,
        },
        merged,
    )


def q10(payments: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    d = (
        payments[payments["installments"].isin([1, 3, 6, 12])]
        .groupby("installments", as_index=False)
        .agg(avg_payment_value=("payment_value", "mean"), n_orders=("order_id", "size"))
        .sort_values("avg_payment_value", ascending=False)
    )
    top = int(d.iloc[0]["installments"])
    option_map = {1: "A", 3: "B", 6: "C", 12: "D"}
    chosen = option_map[top]
    return (
        {
            "question": "Q10",
            "metric": "highest_avg_payment_value_by_installment_plan",
            "value": round(float(d.iloc[0]["avg_payment_value"]), 4),
            "option": chosen,
            "distance": 0.0,
            "detail": str(top),
        },
        d,
    )


def write_report(summary: pd.DataFrame) -> None:
    answer_map = {
        "Q1": "A=30, B=90, C=144, D=365",
        "Q2": "A=Premium, B=Performance, C=Activewear, D=Standard",
        "Q3": "A=defective, B=wrong_size, C=changed_mind, D=not_as_described",
        "Q4": "A=organic_search, B=paid_search, C=email_campaign, D=social_media",
        "Q5": "A=12%, B=25%, C=39%, D=54%",
        "Q6": "A=55+, B=25-, C=35-, D=45-",
        "Q7": "A=West, B=Central, C=East, D=approximately equal",
        "Q8": "A=credit_card, B=cod, C=paypal, D=bank_transfer",
        "Q9": "A=S, B=M, C=L, D=XL",
        "Q10": "A=1, B=3, C=6, D=12 installments",
    }

    lines = [
        "# Milestone 2 - MCQ Computation Report",
        "",
        "## Method",
        "- All answers are computed directly from provided competition CSV files.",
        "- No external data is used.",
        "- Ambiguity handling is documented in the detail column, especially for Q7.",
        "- Values are reported at 4-decimal precision.",
        "",
        "## Final Answers",
    ]

    for _, r in summary.sort_values("question").iterrows():
        q = r["question"]
        lines.append(
            f"- {q}: option {r['option']} | value={r['value']} | metric={r['metric']} | detail={r['detail']} | choices: {answer_map[q]}"
        )

    lines.extend(
        [
            "",
            "## Output Files",
            "- outputs/tables/m2_mcq_summary_primary.csv",
            "- outputs/tables/m2_final_answers.csv",
            "- outputs/tables/m2_q2_segment_margin.csv",
            "- outputs/tables/m2_q3_streetwear_return_reason.csv",
            "- outputs/tables/m2_q4_bounce_by_source.csv",
            "- outputs/tables/m2_q6_age_group_strict.csv",
            "- outputs/tables/m2_q6_age_group_alt_active_only.csv",
            "- outputs/tables/m2_q7_region_revenue_alternatives.csv",
            "- outputs/tables/m2_q8_cancelled_payment_method.csv",
            "- outputs/tables/m2_q9_return_rate_by_size.csv",
            "- outputs/tables/m2_q10_installment_avg_payment.csv",
        ]
    )

    (PLAN_DIR / "m2-mcq-report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    orders = load("orders.csv")
    products = load("products.csv")
    returns = load("returns.csv")
    web = load("web_traffic.csv")
    order_items = load("order_items.csv")
    customers = load("customers.csv")
    geography = load("geography.csv")
    payments = load("payments.csv")

    results = []

    results.append(q1(orders))
    q2_res, q2_tbl = q2(products)
    results.append(q2_res)
    q3_res, q3_tbl = q3(returns, products)
    results.append(q3_res)
    q4_res, q4_tbl = q4(web)
    results.append(q4_res)
    results.append(q5(order_items))
    q6_res, q6_strict, q6_alt = q6(customers, orders)
    results.append(q6_res)
    q7_res, q7_tbl = q7(orders, geography, payments, order_items)
    results.append(q7_res)
    q8_res, q8_tbl = q8(orders)
    results.append(q8_res)
    q9_res, q9_tbl = q9(returns, order_items, products)
    results.append(q9_res)
    q10_res, q10_tbl = q10(payments)
    results.append(q10_res)

    summary = pd.DataFrame(results)
    summary["value"] = summary["value"].round(4)
    summary.to_csv(OUT_DIR / "m2_mcq_summary_primary.csv", index=False)

    final_answers = summary[["question", "option"]].sort_values("question")
    final_answers.to_csv(OUT_DIR / "m2_final_answers.csv", index=False)
    final_answers.to_csv(PLAN_DIR / "m2-final-answers.csv", index=False)

    q2_tbl.to_csv(OUT_DIR / "m2_q2_segment_margin.csv", index=False)
    q3_tbl.to_csv(OUT_DIR / "m2_q3_streetwear_return_reason.csv", index=False)
    q4_tbl.to_csv(OUT_DIR / "m2_q4_bounce_by_source.csv", index=False)
    q6_strict.to_csv(OUT_DIR / "m2_q6_age_group_strict.csv", index=False)
    q6_alt.to_csv(OUT_DIR / "m2_q6_age_group_alt_active_only.csv", index=False)
    q7_tbl.to_csv(OUT_DIR / "m2_q7_region_revenue_alternatives.csv", index=False)
    q8_tbl.to_csv(OUT_DIR / "m2_q8_cancelled_payment_method.csv", index=False)
    q9_tbl.to_csv(OUT_DIR / "m2_q9_return_rate_by_size.csv", index=False)
    q10_tbl.to_csv(OUT_DIR / "m2_q10_installment_avg_payment.csv", index=False)

    write_report(summary)

    print("Milestone 2 primary computation complete.")


if __name__ == "__main__":
    main()
