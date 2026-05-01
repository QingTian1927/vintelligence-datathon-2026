from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs" / "tables"
PLAN_DIR = ROOT / "docs" / "competition" / "first-round" / "planning"


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, low_memory=False)


def main() -> None:
    primary = pd.read_csv(OUT_DIR / "m2_mcq_summary_primary.csv")

    orders = load("orders.csv")
    products = load("products.csv")
    returns = load("returns.csv")
    web = load("web_traffic.csv")
    order_items = load("order_items.csv")
    customers = load("customers.csv")
    geography = load("geography.csv")
    payments = load("payments.csv")

    cross = {}

    # Q1
    o = orders.copy()
    o["order_date"] = pd.to_datetime(o["order_date"], errors="coerce")
    o = o.sort_values(["customer_id", "order_date"])
    o["gap"] = o.groupby("customer_id")["order_date"].diff().dt.days
    q1_val = float(o["gap"].dropna().median())
    cross["Q1"] = "A" if abs(q1_val - 30) < abs(q1_val - 90) and abs(q1_val - 30) < abs(q1_val - 144) else (
        "B" if abs(q1_val - 90) < abs(q1_val - 144) and abs(q1_val - 90) < abs(q1_val - 365) else (
            "C" if abs(q1_val - 144) < abs(q1_val - 365) else "D"
        )
    )

    # Q2
    p = products.assign(margin=(products["price"] - products["cogs"]) / products["price"])
    seg = p.groupby("segment")["margin"].mean().sort_values(ascending=False)
    top_seg = seg.index[0]
    cross["Q2"] = {"Premium": "A", "Performance": "B", "Activewear": "C", "Standard": "D"}[top_seg]

    # Q3
    r = returns.merge(products[["product_id", "category"]], on="product_id", how="left")
    top_reason = (
        r[r["category"] == "Streetwear"]["return_reason"]
        .value_counts()
        .sort_values(ascending=False)
        .index[0]
    )
    cross["Q3"] = {
        "defective": "A",
        "wrong_size": "B",
        "changed_mind": "C",
        "not_as_described": "D",
    }[top_reason]

    # Q4
    src = web.groupby("traffic_source")["bounce_rate"].mean().sort_values(ascending=True)
    cross["Q4"] = {
        "organic_search": "A",
        "paid_search": "B",
        "email_campaign": "C",
        "social_media": "D",
    }[src.index[0]]

    # Q5
    pct = float(order_items["promo_id"].notna().mean() * 100)
    opts = {"A": 12, "B": 25, "C": 39, "D": 54}
    cross["Q5"] = min(opts, key=lambda k: abs(pct - opts[k]))

    # Q6
    c = customers[customers["age_group"].notna()][["customer_id", "age_group"]].copy()
    cnt = orders.groupby("customer_id").size().rename("n_orders")
    c = c.join(cnt, on="customer_id").fillna({"n_orders": 0})
    g = c.groupby("age_group")["n_orders"].mean().sort_values(ascending=False)
    top_age = g.index[0]
    if str(top_age).startswith("55"):
        cross["Q6"] = "A"
    elif str(top_age).startswith("25"):
        cross["Q6"] = "B"
    elif str(top_age).startswith("35"):
        cross["Q6"] = "C"
    else:
        cross["Q6"] = "D"

    # Q7 (payment-based interpretation)
    og = orders[["order_id", "zip"]].merge(geography[["zip", "region"]], on="zip", how="left")
    rg = og.merge(payments[["order_id", "payment_value"]], on="order_id", how="left")
    top_region = rg.groupby("region")["payment_value"].sum().sort_values(ascending=False).index[0]
    cross["Q7"] = {"West": "A", "Central": "B", "East": "C"}.get(top_region, "D")

    # Q8
    pm = (
        orders[orders["order_status"].astype(str).str.lower() == "cancelled"]["payment_method"]
        .value_counts()
        .index[0]
    )
    cross["Q8"] = {"credit_card": "A", "cod": "B", "paypal": "C", "bank_transfer": "D"}[pm]

    # Q9
    size_map = products[["product_id", "size"]]
    num = returns.merge(size_map, on="product_id", how="left")["size"].value_counts()
    den = order_items.merge(size_map, on="product_id", how="left")["size"].value_counts()
    rr = (num / den).sort_values(ascending=False)
    top_size = rr.index[0]
    cross["Q9"] = {"S": "A", "M": "B", "L": "C", "XL": "D"}[top_size]

    # Q10
    inst = (
        payments[payments["installments"].isin([1, 3, 6, 12])]
        .groupby("installments")["payment_value"]
        .mean()
        .sort_values(ascending=False)
        .index[0]
    )
    cross["Q10"] = {1: "A", 3: "B", 6: "C", 12: "D"}[int(inst)]

    cross_df = pd.DataFrame(sorted(cross.items()), columns=["question", "crosscheck_option"])
    comparison = primary[["question", "option"]].merge(cross_df, on="question", how="inner")
    comparison["match"] = comparison["option"] == comparison["crosscheck_option"]

    cross_df.to_csv(OUT_DIR / "m2_mcq_crosscheck_answers.csv", index=False)
    comparison.to_csv(OUT_DIR / "m2_mcq_crosscheck_comparison.csv", index=False)

    mismatch = comparison[~comparison["match"]]
    lines = [
        "# Milestone 2 - Cross-check Summary",
        "",
        f"- Questions checked: {len(comparison)}",
        f"- Matches: {int(comparison['match'].sum())}",
        f"- Mismatches: {len(mismatch)}",
        "",
    ]

    if mismatch.empty:
        lines.append("All cross-check answers match primary outputs.")
    else:
        lines.append("## Mismatches")
        for _, r in mismatch.iterrows():
            lines.append(
                f"- {r['question']}: primary={r['option']} vs crosscheck={r['crosscheck_option']}"
            )

    (PLAN_DIR / "m2-mcq-crosscheck.md").write_text("\n".join(lines), encoding="utf-8")

    print("Milestone 2 cross-check complete.")


if __name__ == "__main__":
    main()
