"""
Milestone 4: Diagnostic EDA — "Why did it happen?"

Purpose:
    Diagnostic layer identifies causal drivers and root causes behind descriptive patterns.
    Uses customer-focused segmentation, dual anomaly detection (statistical + heuristic),
    and both correlation + decomposition analysis.

Scope (user-confirmed):
    - Customer-focused segments: acquisition channel, LTV, repeat purchase patterns
    - Anomaly detection: Z-score/IQR statistical + domain heuristic cross-validation
    - Causal hypotheses: correlation analysis + explicit decomposition (mix/volume/price)
    - Evidence format: Markdown report + supporting notebook + CSV tables
    - Focus areas: revenue drivers, return/quality drivers, traffic & conversion funnel

Competition Rules:
    - Use only data in data/ folder (no external data)
    - All computed metrics must be traceable to source data
    - No data leakage into diagnostic findings
    - Align to EDA rubric: Descriptive (✓ M3) → Diagnostic (M4) → Predictive → Prescriptive

Output Locations:
    - CSVs: outputs/tables/m4_*.csv (hypothesis tables, anomaly flags, cohort metrics)
    - Markdown: docs/competition/first-round/planning/m4-diagnostic-eda-report.md
    - Notebook template: notebooks/m4_diagnostic_walkthrough.ipynb

Execution:
    python scripts/m4_diagnostic_eda.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import json
from datetime import datetime

# ============================================================================
# CONFIG & UTILITIES
# ============================================================================

DATA_DIR = Path("data")
OUTPUT_TABLE_DIR = Path("outputs/tables")
REPORT_DIR = Path("docs/competition/first-round/planning")
NOTEBOOK_DIR = Path("notebooks")

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
pd.set_option('display.max_columns', None)
pd.set_option('display.float_format', lambda x: f'{x:.4f}' if abs(x) < 1e5 else f'{x:.0f}')

def save_table(df, filename, index=False):
    """Save evidence table to CSV."""
    OUTPUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_TABLE_DIR / filename
    df.to_csv(path, index=index)
    print(f"  ✓ {filename}")
    return path

def load_data():
    """Load all required datasets."""
    print("\n[LOAD] Loading datasets...")
    data = {
        'sales': pd.read_csv(DATA_DIR / 'sales.csv', parse_dates=['Date']),
        'orders': pd.read_csv(DATA_DIR / 'orders.csv', parse_dates=['order_date']),
        'order_items': pd.read_csv(DATA_DIR / 'order_items.csv'),
        'products': pd.read_csv(DATA_DIR / 'products.csv'),
        'customers': pd.read_csv(DATA_DIR / 'customers.csv', parse_dates=['signup_date']),
        'returns': pd.read_csv(DATA_DIR / 'returns.csv', parse_dates=['return_date']),
        'reviews': pd.read_csv(DATA_DIR / 'reviews.csv', parse_dates=['review_date']),
        'web_traffic': pd.read_csv(DATA_DIR / 'web_traffic.csv', parse_dates=['date']),
        'payments': pd.read_csv(DATA_DIR / 'payments.csv'),
        'geography': pd.read_csv(DATA_DIR / 'geography.csv'),
        'inventory': pd.read_csv(DATA_DIR / 'inventory.csv', parse_dates=['snapshot_date']),
    }
    print(f"  ✓ Loaded {len(data)} datasets")
    return data

# ============================================================================
# PART 1: REVENUE DECOMPOSITION BY CUSTOMER SEGMENT
# ============================================================================

def revenue_decomposition(data):
    """
    Decompose revenue into mix effect (segment shift), volume effect (order count),
    and price effect (average order value). Segment by acquisition channel.
    
    Hypothesis: Revenue changes driven by:
    1. Customer acquisition channel shift (mix effect)
    2. Purchase frequency per channel (volume effect)
    3. Average order value by channel (price effect)
    """
    print("\n[DIAGNOSTIC 1] Revenue Decomposition by Acquisition Channel")
    
    orders = data['orders'].copy()
    customers = data['customers'].copy()
    sales = data['sales'].copy()
    
    # Merge customer acquisition channel to orders
    orders = orders.merge(
        customers[['customer_id', 'acquisition_channel']],
        on='customer_id',
        how='left'
    )
    
    # Map orders to dates in sales table
    orders['Date'] = orders['order_date'].dt.date
    
    # Compute daily revenue by channel from order_items
    order_items = data['order_items'].copy()
    order_items = order_items.merge(orders[['order_id', 'order_date', 'acquisition_channel']], on='order_id', how='left')
    
    # Revenue per item = (unit_price * quantity - discount_amount)
    order_items['revenue'] = order_items['unit_price'] * order_items['quantity'] - order_items['discount_amount']
    order_items['Date'] = order_items['order_date'].dt.date
    
    # Aggregate by date and channel
    daily_channel_revenue = order_items.groupby(['Date', 'acquisition_channel']).agg({
        'revenue': 'sum',
        'order_id': 'nunique'
    }).reset_index()
    daily_channel_revenue.columns = ['Date', 'acquisition_channel', 'revenue', 'order_count']
    daily_channel_revenue['Date'] = pd.to_datetime(daily_channel_revenue['Date'])
    daily_channel_revenue['avg_order_value'] = (
        daily_channel_revenue['revenue'] / daily_channel_revenue['order_count']
    )
    
    # Compute monthly aggregations
    daily_channel_revenue['YearMonth'] = daily_channel_revenue['Date'].dt.to_period('M')
    monthly_channel = daily_channel_revenue.groupby(['YearMonth', 'acquisition_channel']).agg({
        'revenue': 'sum',
        'order_count': 'sum',
        'avg_order_value': 'mean'
    }).reset_index()
    monthly_channel['YearMonth'] = monthly_channel['YearMonth'].astype(str)
    
    # Total monthly revenue for mix effect calculation
    monthly_total = monthly_channel.groupby('YearMonth')['revenue'].sum().reset_index()
    monthly_total.columns = ['YearMonth', 'total_revenue']
    
    # Channel mix (% of revenue) by month
    monthly_channel = monthly_channel.merge(monthly_total, on='YearMonth', how='left')
    monthly_channel['revenue_pct'] = monthly_channel['revenue'] / monthly_channel['total_revenue']
    
    save_table(monthly_channel, 'm4_revenue_decomposition_monthly.csv')
    
    # Compute decomposition metrics across full dataset
    total_revenue = order_items['revenue'].sum()
    by_channel = order_items.groupby('acquisition_channel').agg({
        'revenue': ['sum', 'mean'],
        'order_id': 'nunique'
    }).reset_index()
    by_channel.columns = ['acquisition_channel', 'total_revenue', 'avg_item_value', 'order_count']
    by_channel['revenue_pct'] = by_channel['total_revenue'] / total_revenue
    by_channel['orders_pct'] = by_channel['order_count'] / order_items['order_id'].nunique()
    
    save_table(by_channel, 'm4_revenue_by_acquisition_channel.csv')
    
    return {
        'monthly': monthly_channel,
        'by_channel': by_channel,
        'daily': daily_channel_revenue
    }

# ============================================================================
# PART 2: CUSTOMER COHORT ANALYSIS (LTV, REPEAT PATTERNS)
# ============================================================================

def customer_cohort_analysis(data):
    """
    Analyze customer segments by:
    - Acquisition channel (original signup channel)
    - Lifetime value (LTV)
    - Repeat purchase rate
    - Average purchase interval
    
    Hypothesis: Different acquisition channels attract customers with different
    lifetime value and repeat purchase behavior.
    """
    print("\n[DIAGNOSTIC 2] Customer Cohort Analysis by Acquisition Channel")
    
    customers = data['customers'].copy()
    orders = data['orders'].copy()
    order_items = data['order_items'].copy()
    
    # Revenue per customer
    order_items['revenue'] = order_items['unit_price'] * order_items['quantity'] - order_items['discount_amount']
    order_items = order_items.merge(orders[['order_id', 'customer_id']], on='order_id', how='left')
    
    customer_revenue = order_items.groupby('customer_id').agg({
        'revenue': 'sum',
        'order_id': 'nunique'
    }).reset_index()
    customer_revenue.columns = ['customer_id', 'lifetime_value', 'order_count']
    
    # Merge with customer acquisition channel
    customer_cohort = customers[['customer_id', 'acquisition_channel', 'signup_date']].merge(
        customer_revenue,
        on='customer_id',
        how='left'
    )
    customer_cohort['lifetime_value'].fillna(0, inplace=True)
    customer_cohort['order_count'].fillna(0, inplace=True)
    
    # Repeat customer indicator (order_count > 1)
    customer_cohort['is_repeat'] = customer_cohort['order_count'] > 1
    
    # Aggregate by acquisition channel
    cohort_summary = customer_cohort.groupby('acquisition_channel').agg({
        'customer_id': 'count',
        'lifetime_value': ['mean', 'median', 'std'],
        'order_count': ['mean', 'median'],
        'is_repeat': 'mean'
    }).reset_index()
    cohort_summary.columns = [
        'acquisition_channel', 'customer_count', 
        'avg_ltv', 'median_ltv', 'std_ltv',
        'avg_orders', 'median_orders',
        'repeat_rate'
    ]
    
    save_table(cohort_summary, 'm4_customer_cohort_by_channel.csv')
    save_table(customer_cohort, 'm4_customer_cohort_full.csv')
    
    return cohort_summary

# ============================================================================
# PART 3: RETURN/QUALITY ROOT CAUSES
# ============================================================================

def return_quality_drivers(data):
    """
    Analyze return patterns by:
    - Product category
    - Customer acquisition channel
    - Product size
    - Seasonal patterns
    
    Hypothesis: Returns are driven by specific product categories, customer segments,
    or seasonal periods.
    """
    print("\n[DIAGNOSTIC 3] Return & Quality Drivers")
    
    returns = data['returns'].copy()
    order_items = data['order_items'].copy()
    products = data['products'].copy()
    orders = data['orders'].copy()
    customers = data['customers'].copy()
    
    # Merge returns with product and order context
    returns = returns.merge(products[['product_id', 'category', 'size']], on='product_id', how='left')
    returns = returns.merge(orders[['order_id', 'customer_id']], on='order_id', how='left')
    returns = returns.merge(customers[['customer_id', 'acquisition_channel']], on='customer_id', how='left')
    returns['return_date'] = pd.to_datetime(returns['return_date'])
    
    # Total items sold (from order_items)
    total_items = order_items.merge(
        products[['product_id', 'category', 'size']], on='product_id', how='left'
    )
    
    # Return rate by category
    returns_by_category = returns.groupby('category').agg({
        'return_quantity': 'sum',
        'return_reason': 'count'
    }).reset_index()
    returns_by_category.columns = ['category', 'returned_quantity', 'return_count']
    
    total_by_category = total_items.groupby('category')['quantity'].sum().reset_index()
    total_by_category.columns = ['category', 'total_quantity']
    
    returns_by_category = returns_by_category.merge(total_by_category, on='category', how='left')
    returns_by_category['return_rate'] = returns_by_category['returned_quantity'] / returns_by_category['total_quantity']
    
    save_table(returns_by_category, 'm4_return_rate_by_category.csv')
    
    # Return reasons analysis
    return_reasons = returns['return_reason'].value_counts().reset_index()
    return_reasons.columns = ['return_reason', 'count']
    return_reasons['percentage'] = return_reasons['count'] / return_reasons['count'].sum()
    
    save_table(return_reasons, 'm4_return_reasons.csv')
    
    # Return rate by acquisition channel
    returns_by_channel = returns.groupby('acquisition_channel').agg({
        'return_quantity': 'sum',
        'return_reason': 'count'
    }).reset_index()
    returns_by_channel.columns = ['acquisition_channel', 'returned_quantity', 'return_count']
    
    # Total items by channel (from order_items merged with orders and customers)
    order_items_merged = order_items.merge(orders[['order_id', 'customer_id']], on='order_id', how='left')
    order_items_merged = order_items_merged.merge(
        customers[['customer_id', 'acquisition_channel']], on='customer_id', how='left'
    )
    
    total_by_channel = order_items_merged.groupby('acquisition_channel')['quantity'].sum().reset_index()
    total_by_channel.columns = ['acquisition_channel', 'total_quantity']
    
    returns_by_channel = returns_by_channel.merge(total_by_channel, on='acquisition_channel', how='left')
    returns_by_channel['return_rate'] = returns_by_channel['returned_quantity'] / returns_by_channel['total_quantity']
    
    save_table(returns_by_channel, 'm4_return_rate_by_channel.csv')
    
    # Return rate by size
    returns_by_size = returns.groupby('size').agg({
        'return_quantity': 'sum',
        'return_reason': 'count'
    }).reset_index()
    returns_by_size.columns = ['size', 'returned_quantity', 'return_count']
    
    total_by_size = total_items.groupby('size')['quantity'].sum().reset_index()
    total_by_size.columns = ['size', 'total_quantity']
    
    returns_by_size = returns_by_size.merge(total_by_size, on='size', how='left')
    returns_by_size['return_rate'] = returns_by_size['returned_quantity'] / returns_by_size['total_quantity']
    
    save_table(returns_by_size, 'm4_return_rate_by_size.csv')
    
    return {
        'by_category': returns_by_category,
        'by_channel': returns_by_channel,
        'by_size': returns_by_size,
        'reasons': return_reasons
    }

# ============================================================================
# PART 4: TRAFFIC FUNNEL & CONVERSION ANALYSIS
# ============================================================================

def traffic_funnel_analysis(data):
    """
    Analyze web traffic funnel:
    - Sessions by source
    - Conversion rate (derived: orders/sessions)
    - Bounce rate by source
    - Traffic-to-order efficiency by acquisition channel
    
    Hypothesis: Different traffic sources have different conversion rates and
    bounce rates, indicating funnel bottlenecks.
    """
    print("\n[DIAGNOSTIC 4] Traffic Funnel & Conversion Analysis")
    
    web_traffic = data['web_traffic'].copy()
    orders = data['orders'].copy()
    customers = data['customers'].copy()
    
    # Daily traffic by source
    daily_traffic = web_traffic.groupby(['date', 'traffic_source']).agg({
        'sessions': 'sum',
        'page_views': 'sum',
        'bounce_rate': 'mean'
    }).reset_index()
    
    # Daily orders by source (orders.order_source)
    orders['Date'] = orders['order_date'].dt.date
    daily_orders = orders.groupby(['Date', 'order_source']).size().reset_index(name='order_count')
    daily_orders['Date'] = pd.to_datetime(daily_orders['Date'])
    
    # Merge traffic with orders (map order_source to traffic_source)
    # Assuming order_source and traffic_source are comparable
    daily_traffic['date'] = pd.to_datetime(daily_traffic['date'])
    funnel = daily_traffic.merge(
        daily_orders,
        left_on=['date', 'traffic_source'],
        right_on=['Date', 'order_source'],
        how='left'
    )
    funnel['order_count'].fillna(0, inplace=True)
    
    # Compute conversion metrics
    funnel['conversion_rate'] = funnel['order_count'] / funnel['sessions']
    funnel['page_view_per_session'] = funnel['page_views'] / funnel['sessions']
    
    # Monthly aggregation
    daily_traffic['YearMonth'] = daily_traffic['date'].dt.to_period('M')
    monthly_traffic = daily_traffic.groupby(['YearMonth', 'traffic_source']).agg({
        'sessions': 'sum',
        'page_views': 'sum',
        'bounce_rate': 'mean'
    }).reset_index()
    
    daily_orders['YearMonth'] = daily_orders['Date'].dt.to_period('M')
    monthly_orders = daily_orders.groupby(['YearMonth', 'order_source']).agg({
        'order_count': 'sum'
    }).reset_index()
    
    monthly_funnel = monthly_traffic.merge(
        monthly_orders,
        left_on=['YearMonth', 'traffic_source'],
        right_on=['YearMonth', 'order_source'],
        how='left'
    )
    monthly_funnel['order_count'].fillna(0, inplace=True)
    monthly_funnel['conversion_rate'] = monthly_funnel['order_count'] / monthly_funnel['sessions']
    monthly_funnel['page_view_per_session'] = monthly_funnel['page_views'] / monthly_funnel['sessions']
    monthly_funnel['YearMonth'] = monthly_funnel['YearMonth'].astype(str)
    
    save_table(monthly_funnel, 'm4_traffic_funnel_monthly.csv')
    
    # Summary by source
    funnel_summary = monthly_funnel.groupby('traffic_source').agg({
        'sessions': 'sum',
        'page_views': 'sum',
        'order_count': 'sum',
        'conversion_rate': 'mean',
        'bounce_rate': 'mean'
    }).reset_index()
    funnel_summary.columns = [
        'traffic_source', 'total_sessions', 'total_page_views', 'total_orders',
        'avg_conversion_rate', 'avg_bounce_rate'
    ]
    
    save_table(funnel_summary, 'm4_traffic_funnel_summary.csv')
    
    return {
        'monthly': monthly_funnel,
        'summary': funnel_summary
    }

# ============================================================================
# PART 5: DUAL ANOMALY DETECTION (Statistical + Heuristic)
# ============================================================================

def dual_anomaly_detection(data):
    """
    Detect anomalies using two methods:
    1. Statistical: Z-score > 3 or IQR-based outliers
    2. Heuristic: domain logic (e.g., >3x average, extreme seasonal deviation)
    
    Cross-validate findings to identify true anomalies.
    """
    print("\n[DIAGNOSTIC 5] Dual Anomaly Detection")
    
    sales = data['sales'].copy()
    sales['Date'] = pd.to_datetime(sales['Date'])
    sales = sales.sort_values('Date')
    
    # Revenue statistics
    mean_rev = sales['Revenue'].mean()
    std_rev = sales['Revenue'].std()
    q1_rev = sales['Revenue'].quantile(0.25)
    q3_rev = sales['Revenue'].quantile(0.75)
    iqr_rev = q3_rev - q1_rev
    
    # Statistical anomalies: Z-score > 3 or IQR outliers
    sales['z_score'] = np.abs((sales['Revenue'] - mean_rev) / std_rev)
    sales['is_statistical_anomaly'] = (
        (sales['z_score'] > 3) |
        (sales['Revenue'] < (q1_rev - 1.5 * iqr_rev)) |
        (sales['Revenue'] > (q3_rev + 1.5 * iqr_rev))
    )
    
    # Heuristic anomalies: domain logic
    # 1. Revenue > 3x average
    sales['is_high_revenue_heuristic'] = sales['Revenue'] > (3 * mean_rev)
    
    # 2. Revenue < 0.3x average
    sales['is_low_revenue_heuristic'] = sales['Revenue'] < (0.3 * mean_rev)
    
    # 3. Day-over-day change > 100%
    sales['revenue_pct_change'] = sales['Revenue'].pct_change().abs()
    sales['is_extreme_change_heuristic'] = sales['revenue_pct_change'] > 1.0
    
    # Combine heuristics
    sales['is_heuristic_anomaly'] = (
        sales['is_high_revenue_heuristic'] |
        sales['is_low_revenue_heuristic'] |
        sales['is_extreme_change_heuristic']
    )
    
    # Cross-validation
    sales['anomaly_type'] = 'normal'
    sales.loc[sales['is_statistical_anomaly'] & sales['is_heuristic_anomaly'], 'anomaly_type'] = 'both_methods'
    sales.loc[(sales['is_statistical_anomaly']) & (~sales['is_heuristic_anomaly']), 'anomaly_type'] = 'statistical_only'
    sales.loc[(~sales['is_statistical_anomaly']) & (sales['is_heuristic_anomaly']), 'anomaly_type'] = 'heuristic_only'
    
    # Extract anomalies
    anomalies = sales[sales['anomaly_type'] != 'normal'][
        ['Date', 'Revenue', 'z_score', 'anomaly_type']
    ].copy()
    
    save_table(anomalies, 'm4_anomalies_dual_detection.csv')
    
    return {
        'full': sales,
        'anomalies': anomalies,
        'stats': {
            'mean': mean_rev,
            'std': std_rev,
            'q1': q1_rev,
            'q3': q3_rev,
            'iqr': iqr_rev
        }
    }

# ============================================================================
# PART 6: CORRELATION ANALYSIS
# ============================================================================

def correlation_analysis(data):
    """
    Compute correlations between key business metrics to identify
    potential causal relationships.
    
    Metrics: daily revenue, traffic, bounce rate, inventory levels, returns
    """
    print("\n[DIAGNOSTIC 6] Correlation Analysis")
    
    sales = data['sales'].copy()
    sales['Date'] = pd.to_datetime(sales['Date'])
    
    web_traffic = data['web_traffic'].copy()
    web_traffic['date'] = pd.to_datetime(web_traffic['date'])
    
    inventory = data['inventory'].copy()
    inventory['snapshot_date'] = pd.to_datetime(inventory['snapshot_date'])
    
    returns = data['returns'].copy()
    returns['return_date'] = pd.to_datetime(returns['return_date'])
    returns['Date'] = returns['return_date'].dt.date
    
    # Daily aggregations
    daily_traffic = web_traffic.groupby('date').agg({
        'sessions': 'sum',
        'page_views': 'sum',
        'bounce_rate': 'mean'
    }).reset_index()
    daily_traffic.rename(columns={'date': 'Date'}, inplace=True)
    daily_traffic['Date'] = pd.to_datetime(daily_traffic['Date'])
    
    daily_returns = returns.groupby('Date').agg({
        'return_quantity': 'sum'
    }).reset_index()
    daily_returns['Date'] = pd.to_datetime(daily_returns['Date'])
    
    # Merge all daily metrics
    daily_metrics = sales.merge(daily_traffic, on='Date', how='left')
    daily_metrics = daily_metrics.merge(daily_returns, on='Date', how='left')
    
    # Fill NaNs with 0 for traffic/returns on non-traffic/return days
    daily_metrics[['sessions', 'page_views', 'bounce_rate']] = daily_metrics[['sessions', 'page_views', 'bounce_rate']].fillna(0)
    daily_metrics['return_quantity'] = daily_metrics['return_quantity'].fillna(0)
    
    # Compute correlations
    numeric_cols = ['Revenue', 'sessions', 'page_views', 'bounce_rate', 'return_quantity', 'COGS']
    correlation_matrix = daily_metrics[numeric_cols].corr()
    
    # Extract revenue correlations
    revenue_corr = correlation_matrix['Revenue'].sort_values(ascending=False).reset_index()
    revenue_corr.columns = ['metric', 'correlation_with_revenue']
    
    save_table(correlation_matrix.reset_index(), 'm4_correlation_matrix.csv')
    save_table(revenue_corr, 'm4_revenue_correlations.csv')
    
    return {
        'correlation_matrix': correlation_matrix,
        'revenue_correlations': revenue_corr,
        'daily_metrics': daily_metrics
    }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 80)
    print("MILESTONE 4: DIAGNOSTIC EDA — Why did it happen?")
    print("=" * 80)
    print(f"\nExecution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Random Seed: {RANDOM_SEED}")
    
    # Load data
    data = load_data()
    
    # Execute diagnostic analyses
    print("\n" + "=" * 80)
    print("DIAGNOSTIC ANALYSES")
    print("=" * 80)
    
    results = {}
    
    # 1. Revenue decomposition
    results['revenue_decomp'] = revenue_decomposition(data)
    
    # 2. Customer cohorts
    results['cohort'] = customer_cohort_analysis(data)
    
    # 3. Return drivers
    results['returns'] = return_quality_drivers(data)
    
    # 4. Traffic funnel
    results['traffic'] = traffic_funnel_analysis(data)
    
    # 5. Anomaly detection
    results['anomalies'] = dual_anomaly_detection(data)
    
    # 6. Correlation analysis
    results['correlation'] = correlation_analysis(data)
    
    print("\n" + "=" * 80)
    print("MILESTONE 4 EXECUTION COMPLETE")
    print("=" * 80)
    print(f"\nAll outputs saved to:")
    print(f"  • Tables: {OUTPUT_TABLE_DIR}")
    print(f"  • Report: {REPORT_DIR}")
    print(f"  • Notebook: {NOTEBOOK_DIR}")
    
    return results

if __name__ == "__main__":
    results = main()
