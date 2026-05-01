from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TABLE_DIR = ROOT / "outputs" / "tables"
FIG_DIR = ROOT / "reports" / "assets" / "figures"
PLAN_DIR = ROOT / "docs" / "competition" / "first-round" / "planning"


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, low_memory=False)


def setup_style() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams["figure.figsize"] = (12, 6)
    plt.rcParams["axes.titleweight"] = "bold"


def save_table(df: pd.DataFrame, name: str) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLE_DIR / name, index=False)


def save_fig(name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIG_DIR / name, dpi=160)
    plt.close()


def build_revenue_tables(sales: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    s = sales.copy()
    s["Date"] = pd.to_datetime(s["Date"], errors="coerce")
    s = s.dropna(subset=["Date"]).sort_values("Date")

    daily = s[["Date", "Revenue", "COGS"]].copy()
    daily["gross_profit"] = daily["Revenue"] - daily["COGS"]
    daily["revenue_30d_ma"] = daily["Revenue"].rolling(30, min_periods=1).mean()

    monthly = (
        daily.assign(month=daily["Date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)
        .agg(
            revenue=("Revenue", "sum"),
            cogs=("COGS", "sum"),
            gross_profit=("gross_profit", "sum"),
            avg_daily_revenue=("Revenue", "mean"),
        )
    )

    seasonality = (
        daily.assign(month_num=daily["Date"].dt.month)
        .groupby("month_num", as_index=False)
        .agg(avg_revenue=("Revenue", "mean"), median_revenue=("Revenue", "median"))
        .sort_values("month_num")
    )

    return daily, monthly, seasonality


def plot_revenue_charts(daily: pd.DataFrame, monthly: pd.DataFrame) -> None:
    plt.figure()
    sns.lineplot(data=daily, x="Date", y="Revenue", alpha=0.25, label="Daily Revenue")
    sns.lineplot(data=daily, x="Date", y="revenue_30d_ma", linewidth=2.2, label="30D Moving Avg")
    plt.title("M3-01 Daily Revenue With 30-Day Trend")
    plt.xlabel("Date")
    plt.ylabel("Revenue")
    save_fig("m3_01_daily_revenue_trend.png")

    plt.figure()
    sns.lineplot(data=monthly, x="month", y="revenue", marker="o")
    plt.title("M3-02 Monthly Revenue")
    plt.xlabel("Month")
    plt.ylabel("Revenue")
    save_fig("m3_02_monthly_revenue.png")


def build_order_tables(orders: pd.DataFrame, customers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    o = orders.copy()
    o["order_date"] = pd.to_datetime(o["order_date"], errors="coerce")
    o = o.dropna(subset=["order_date"])

    monthly_orders = (
        o.assign(month=o["order_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)
        .agg(order_count=("order_id", "nunique"))
    )

    order_source_mix = (
        o.assign(order_source=o["order_source"].fillna("unknown"))
        .groupby("order_source", as_index=False)
        .agg(order_count=("order_id", "nunique"))
        .sort_values("order_count", ascending=False)
    )
    total_orders = order_source_mix["order_count"].sum()
    order_source_mix["share_pct"] = (order_source_mix["order_count"] / total_orders * 100).round(4)

    c = customers.copy()
    c["acquisition_channel"] = c["acquisition_channel"].fillna("unknown")
    acq_mix = (
        c.groupby("acquisition_channel", as_index=False)
        .agg(customer_count=("customer_id", "nunique"))
        .sort_values("customer_count", ascending=False)
    )
    total_customers = acq_mix["customer_count"].sum()
    acq_mix["share_pct"] = (acq_mix["customer_count"] / total_customers * 100).round(4)

    return monthly_orders, order_source_mix, acq_mix


def plot_order_charts(monthly_orders: pd.DataFrame, order_source_mix: pd.DataFrame, acq_mix: pd.DataFrame) -> None:
    plt.figure()
    sns.lineplot(data=monthly_orders, x="month", y="order_count", marker="o")
    plt.title("M3-03 Monthly Order Volume")
    plt.xlabel("Month")
    plt.ylabel("Unique Orders")
    save_fig("m3_03_monthly_order_volume.png")

    plt.figure()
    top = order_source_mix.head(10)
    sns.barplot(data=top, x="order_count", y="order_source")
    plt.title("M3-06 Order Source Mix (Top 10)")
    plt.xlabel("Order Count")
    plt.ylabel("Order Source")
    save_fig("m3_06_order_source_mix.png")

    plt.figure()
    top = acq_mix.head(10)
    sns.barplot(data=top, x="customer_count", y="acquisition_channel")
    plt.title("M3-07 Customer Acquisition Channel Mix (Top 10)")
    plt.xlabel("Customer Count")
    plt.ylabel("Acquisition Channel")
    save_fig("m3_07_acquisition_channel_mix.png")


def build_product_tables(order_items: pd.DataFrame, products: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    oi = order_items.copy()
    p = products.copy()

    oi["line_revenue"] = oi["unit_price"] * oi["quantity"]
    merged = oi.merge(p[["product_id", "category", "segment", "price", "cogs"]], on="product_id", how="left")

    category_rev = (
        merged.groupby("category", as_index=False)
        .agg(total_revenue=("line_revenue", "sum"), total_units=("quantity", "sum"))
        .sort_values("total_revenue", ascending=False)
    )

    p["gross_margin_rate"] = (p["price"] - p["cogs"]) / p["price"]
    segment_margin = (
        p.groupby("segment", as_index=False)
        .agg(avg_margin_rate=("gross_margin_rate", "mean"), n_products=("product_id", "nunique"))
        .sort_values("avg_margin_rate", ascending=False)
    )

    return category_rev, segment_margin


def plot_product_charts(category_rev: pd.DataFrame, segment_margin: pd.DataFrame) -> None:
    plt.figure()
    top = category_rev.head(10)
    sns.barplot(data=top, x="total_revenue", y="category")
    plt.title("M3-04 Top Categories by Revenue")
    plt.xlabel("Total Revenue")
    plt.ylabel("Category")
    save_fig("m3_04_category_revenue_top10.png")

    plt.figure()
    sns.barplot(data=segment_margin, x="segment", y="avg_margin_rate")
    plt.title("M3-05 Average Gross Margin Rate by Segment")
    plt.xlabel("Segment")
    plt.ylabel("Avg Gross Margin Rate")
    save_fig("m3_05_segment_margin_rate.png")


def build_return_quality_tables(
    returns: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame, reviews: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    r = returns.copy()
    oi = order_items.copy()
    p = products[["product_id", "category"]].copy()

    return_reason = (
        r.groupby("return_reason", as_index=False)
        .agg(return_records=("return_id", "count"))
        .sort_values("return_records", ascending=False)
    )

    num = (
        r.merge(p, on="product_id", how="left")
        .groupby("category", as_index=False)
        .agg(return_records=("return_id", "count"))
    )
    den = (
        oi.merge(p, on="product_id", how="left")
        .groupby("category", as_index=False)
        .agg(order_item_rows=("order_id", "count"))
    )
    return_rate = num.merge(den, on="category", how="outer").fillna(0)
    return_rate["return_rate"] = (
        return_rate["return_records"] / return_rate["order_item_rows"].replace({0: pd.NA})
    ).fillna(0)
    return_rate = return_rate.sort_values("return_rate", ascending=False)

    rv = reviews.copy()
    rating_dist = (
        rv.groupby("rating", as_index=False)
        .agg(review_count=("review_id", "count"))
        .sort_values("rating")
    )

    return return_reason, return_rate, rating_dist


def plot_return_quality_charts(return_reason: pd.DataFrame, return_rate: pd.DataFrame, rating_dist: pd.DataFrame) -> None:
    plt.figure()
    sns.barplot(data=return_reason, x="return_records", y="return_reason")
    plt.title("M3-08 Return Reasons Distribution")
    plt.xlabel("Return Records")
    plt.ylabel("Return Reason")
    save_fig("m3_08_return_reason_distribution.png")

    plt.figure()
    top = return_rate.head(10)
    sns.barplot(data=top, x="return_rate", y="category")
    plt.title("M3-09 Return Rate by Category (Top 10)")
    plt.xlabel("Return Rate")
    plt.ylabel("Category")
    save_fig("m3_09_return_rate_by_category.png")

    plt.figure()
    sns.barplot(data=rating_dist, x="rating", y="review_count")
    plt.title("M3-10 Review Rating Distribution")
    plt.xlabel("Rating")
    plt.ylabel("Review Count")
    save_fig("m3_10_review_rating_distribution.png")


def build_ops_tables(inventory: pd.DataFrame, web: pd.DataFrame, orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    inv = inventory.copy()
    inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"], errors="coerce")

    inv_monthly = (
        inv.assign(month=inv["snapshot_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)
        .agg(
            stockout_rate=("stockout_flag", "mean"),
            avg_fill_rate=("fill_rate", "mean"),
            avg_days_of_supply=("days_of_supply", "mean"),
        )
        .sort_values("month")
    )

    w = web.copy()
    w["date"] = pd.to_datetime(w["date"], errors="coerce")

    # Build a daily conversion proxy from observed orders over sessions.
    daily_orders = orders.copy()
    daily_orders["order_date"] = pd.to_datetime(daily_orders["order_date"], errors="coerce")
    daily_orders = (
        daily_orders.groupby("order_date", as_index=False)
        .agg(order_count=("order_id", "nunique"))
        .rename(columns={"order_date": "date"})
    )

    web_daily = (
        w.groupby("date", as_index=False)
        .agg(
            sessions=("sessions", "sum"),
            unique_visitors=("unique_visitors", "sum"),
            page_views=("page_views", "sum"),
            bounce_rate=("bounce_rate", "mean"),
        )
        .merge(daily_orders, on="date", how="left")
    )
    web_daily["order_count"] = web_daily["order_count"].fillna(0)
    web_daily["conversion_proxy"] = web_daily["order_count"] / web_daily["sessions"].replace({0: pd.NA})
    web_daily["conversion_proxy"] = web_daily["conversion_proxy"].fillna(0)
    web_daily = web_daily.sort_values("date")
    web_daily["sessions_30d_ma"] = web_daily["sessions"].rolling(30, min_periods=1).mean()
    web_daily["conversion_proxy_30d_ma"] = web_daily["conversion_proxy"].rolling(30, min_periods=1).mean()

    return inv_monthly, web_daily


def plot_ops_charts(inv_monthly: pd.DataFrame, web_daily: pd.DataFrame) -> None:
    plt.figure()
    sns.lineplot(data=inv_monthly, x="month", y="stockout_rate", marker="o")
    plt.title("M3-11 Monthly Stockout Rate")
    plt.xlabel("Month")
    plt.ylabel("Stockout Rate")
    save_fig("m3_11_monthly_stockout_rate.png")

    fig, ax1 = plt.subplots(figsize=(12, 6))
    sns.lineplot(data=web_daily, x="date", y="sessions_30d_ma", ax=ax1, color="#1f77b4", label="Sessions 30D MA")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Sessions (30D MA)", color="#1f77b4")

    ax2 = ax1.twinx()
    sns.lineplot(
        data=web_daily,
        x="date",
        y="conversion_proxy_30d_ma",
        ax=ax2,
        color="#d62728",
        label="Orders per Session (30D MA)",
    )
    ax2.set_ylabel("Orders per Session (30D MA)", color="#d62728")
    ax1.set_title("M3-12 Traffic Sessions and Conversion Proxy Trend")
    save_fig("m3_12_traffic_conversion_trend.png")


def write_report() -> None:
    report_path = PLAN_DIR / "m3-descriptive-eda-report.md"
    lines = [
        "# Milestone 3 - Descriptive EDA Report",
        "",
        "## Scope",
        "- This milestone focuses on descriptive analytics only (What happened?).",
        "- All analysis uses only official competition CSV files.",
        "- Since web_traffic.csv has no conversion_rate column, conversion is represented by a proxy: daily unique orders / daily sessions.",
        "- Figures are exported to reports/assets/figures for direct report reuse.",
        "",
        "## Generated Figure Set (12 Charts)",
        "1. m3_01_daily_revenue_trend.png",
        "2. m3_02_monthly_revenue.png",
        "3. m3_03_monthly_order_volume.png",
        "4. m3_04_category_revenue_top10.png",
        "5. m3_05_segment_margin_rate.png",
        "6. m3_06_order_source_mix.png",
        "7. m3_07_acquisition_channel_mix.png",
        "8. m3_08_return_reason_distribution.png",
        "9. m3_09_return_rate_by_category.png",
        "10. m3_10_review_rating_distribution.png",
        "11. m3_11_monthly_stockout_rate.png",
        "12. m3_12_traffic_conversion_trend.png",
        "",
        "## Summary Tables",
        "- outputs/tables/m3_daily_revenue_table.csv",
        "- outputs/tables/m3_monthly_revenue_table.csv",
        "- outputs/tables/m3_revenue_seasonality_table.csv",
        "- outputs/tables/m3_monthly_order_volume.csv",
        "- outputs/tables/m3_order_source_mix.csv",
        "- outputs/tables/m3_acquisition_channel_mix.csv",
        "- outputs/tables/m3_category_revenue.csv",
        "- outputs/tables/m3_segment_margin_rate.csv",
        "- outputs/tables/m3_return_reason_distribution.csv",
        "- outputs/tables/m3_return_rate_by_category.csv",
        "- outputs/tables/m3_review_rating_distribution.csv",
        "- outputs/tables/m3_inventory_monthly_ops.csv",
        "- outputs/tables/m3_web_daily_trend.csv",
        "",
        "## Key Descriptive Findings Snapshot",
        "- Revenue and order volumes exhibit visible monthly fluctuation and trend regimes.",
        "- Category-level revenue concentration is strong in top categories.",
        "- Segment margins are structurally different across product segments.",
        "- Return behavior is uneven by category and dominated by specific reason codes.",
        "- Stockout rate varies over time, indicating operational volatility.",
        "- Traffic and conversion trends do not move uniformly, suggesting funnel efficiency shifts.",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    setup_style()

    sales = load_csv("sales.csv")
    orders = load_csv("orders.csv")
    customers = load_csv("customers.csv")
    products = load_csv("products.csv")
    order_items = load_csv("order_items.csv")
    returns = load_csv("returns.csv")
    reviews = load_csv("reviews.csv")
    inventory = load_csv("inventory.csv")
    web = load_csv("web_traffic.csv")

    daily, monthly, seasonality = build_revenue_tables(sales)
    save_table(daily, "m3_daily_revenue_table.csv")
    save_table(monthly, "m3_monthly_revenue_table.csv")
    save_table(seasonality, "m3_revenue_seasonality_table.csv")
    plot_revenue_charts(daily, monthly)

    monthly_orders, order_source_mix, acq_mix = build_order_tables(orders, customers)
    save_table(monthly_orders, "m3_monthly_order_volume.csv")
    save_table(order_source_mix, "m3_order_source_mix.csv")
    save_table(acq_mix, "m3_acquisition_channel_mix.csv")
    plot_order_charts(monthly_orders, order_source_mix, acq_mix)

    category_rev, segment_margin = build_product_tables(order_items, products)
    save_table(category_rev, "m3_category_revenue.csv")
    save_table(segment_margin, "m3_segment_margin_rate.csv")
    plot_product_charts(category_rev, segment_margin)

    return_reason, return_rate, rating_dist = build_return_quality_tables(returns, order_items, products, reviews)
    save_table(return_reason, "m3_return_reason_distribution.csv")
    save_table(return_rate, "m3_return_rate_by_category.csv")
    save_table(rating_dist, "m3_review_rating_distribution.csv")
    plot_return_quality_charts(return_reason, return_rate, rating_dist)

    inv_monthly, web_daily = build_ops_tables(inventory, web, orders)
    save_table(inv_monthly, "m3_inventory_monthly_ops.csv")
    save_table(web_daily, "m3_web_daily_trend.csv")
    plot_ops_charts(inv_monthly, web_daily)

    write_report()
    print("Milestone 3 descriptive EDA outputs generated.")


if __name__ == "__main__":
    main()
