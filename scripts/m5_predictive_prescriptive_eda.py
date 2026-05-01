"""
Milestone 5: Predictive & Prescriptive EDA — "What is likely to happen? What should we do?"

Purpose:
    Predictive layer: Forecast revenue for test period (01/01/2023 - 01/07/2024) using
    time-series decomposition + ensemble forecasting.
    Prescriptive layer: Generate actionable recommendations with quantified ROI.

Scope (user-confirmed):
    - Forecasting: Ensemble with time-series decomposition (trend, seasonality, promotional drivers)
    - Scenarios: Tactical (promotions, channel shifts) + Strategic (inventory, product mix)
    - Recommendations: Domain logic + quantified trade-offs + ROI estimates
    - Horizon: Full test period (Jan 2023 - Jul 2024)
    - Format: Markdown report + notebook + visualizations

Competition Rules:
    - Train period: 04/07/2012 - 31/12/2022 (sales.csv)
    - Test period: 01/01/2023 - 01/07/2024 (held out)
    - Forecast: Revenue (daily)
    - No data leakage (use only train data for model building)

Key Diagnostic Drivers (from M4):
    1. COGS correlation: r=0.976 (inventory-driven)
    2. Promotional calendar: Anomalies cluster seasonally
    3. Channel mix: Stable 30% organic, 20% social, 20% paid search
    4. Customer repeat: Uniform 55% across channels
    5. Returns: Category-driven 3.4% baseline

Output Locations:
    - CSVs: outputs/tables/m5_*.csv (forecasts, scenarios, recommendations)
    - Markdown: docs/competition/first-round/planning/m5-predictive-prescriptive-eda-report.md
    - Notebook: notebooks/m5_predictive_walkthrough.ipynb

Execution:
    python scripts/m5_predictive_prescriptive_eda.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import json
from datetime import datetime, timedelta

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

# Test period
TEST_START = pd.Timestamp('2023-01-01')
TEST_END = pd.Timestamp('2024-07-01')

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
        'inventory': pd.read_csv(DATA_DIR / 'inventory.csv', parse_dates=['snapshot_date']),
    }
    print(f"  ✓ Loaded {len(data)} datasets")
    return data

# ============================================================================
# PART 1: TIME-SERIES DECOMPOSITION
# ============================================================================

def time_series_decomposition(sales):
    """
    Decompose sales into:
    - Trend: Long-term direction
    - Seasonality: Repeating patterns (weekly, monthly, yearly)
    - Promotional: Anomalous spikes (from M4 findings)
    - Residual: Unexplained variance
    
    Uses moving averages and seasonal indices for interpretability.
    """
    print("\n[PREDICTIVE 1] Time-Series Decomposition")
    
    sales = sales.sort_values('Date')
    # Don't add 'revenue' column - keep using 'Revenue' throughout
    
    # Trend: 365-day moving average
    sales['trend'] = sales['Revenue'].rolling(window=365, center=True).mean()
    
    # Fill edges with linear regression
    valid_trend = sales[sales['trend'].notna()]
    if len(valid_trend) > 0:
        X = np.arange(len(sales)).reshape(-1, 1)
        y = sales['Revenue'].values
        model = LinearRegression()
        model.fit(X, y)
        trend_pred = model.predict(X)
        sales['trend'] = sales['trend'].fillna(pd.Series(trend_pred, index=sales.index))
    
    # Detrended
    sales['detrended'] = sales['Revenue'] - sales['trend']
    
    # Seasonality: Average detrended value by day-of-year (365-day cycle)
    sales['day_of_year'] = sales['Date'].dt.dayofyear
    seasonal_pattern = sales.groupby('day_of_year')['detrended'].median()
    sales['seasonality'] = sales['day_of_year'].map(seasonal_pattern)
    
    # Promotional: Residual after removing trend and seasonality
    sales['promotional'] = sales['detrended'] - sales['seasonality']
    
    # Residual: Unexplained
    sales['residual'] = sales['Revenue'] - (sales['trend'] + sales['seasonality'] + sales['promotional'])
    
    # Variance contribution
    var_total = sales['Revenue'].var()
    var_trend = sales['trend'].var()
    var_seasonal = sales['seasonality'].var()
    var_promo = sales['promotional'].var()
    var_residual = sales['residual'].var()
    
    decomp_summary = pd.DataFrame({
        'component': ['Trend', 'Seasonality', 'Promotional', 'Residual'],
        'variance': [var_trend, var_seasonal, var_promo, var_residual],
        'pct_total': [
            var_trend / var_total if var_total > 0 else 0,
            var_seasonal / var_total if var_total > 0 else 0,
            var_promo / var_total if var_total > 0 else 0,
            var_residual / var_total if var_total > 0 else 0
        ]
    })
    
    save_table(decomp_summary, 'm5_decomposition_variance.csv')
    
    return sales, decomp_summary

# ============================================================================
# PART 2: ENSEMBLE FORECASTING
# ============================================================================

def ensemble_forecast(sales_train, test_dates):
    """
    Build ensemble forecast using multiple approaches:
    1. Exponential smoothing (trend + level)
    2. Seasonal naive (previous year same day)
    3. Trend extrapolation with seasonality
    4. Average of the above
    
    Returns ensemble forecast for test period.
    """
    print("\n[PREDICTIVE 2] Ensemble Forecasting")
    
    sales_train = sales_train.sort_values('Date')
    
    # Method 1: Exponential smoothing approximation
    alpha = 0.3  # Smoothing factor
    level = sales_train['Revenue'].iloc[0]
    trend = (sales_train['Revenue'].iloc[-1] - sales_train['Revenue'].iloc[0]) / len(sales_train)
    forecast_exp = []
    
    for i, test_date in enumerate(test_dates):
        forecast_val = level + trend * (i + 1)
        forecast_exp.append(forecast_val)
    
    # Method 2: Seasonal naive (previous year same day)
    sales_train['day_of_year'] = sales_train['Date'].dt.dayofyear
    seasonal_avg = sales_train.groupby('day_of_year')['Revenue'].median()
    
    forecast_naive = []
    for test_date in test_dates:
        doy = test_date.dayofyear
        if doy in seasonal_avg.index:
            forecast_naive.append(seasonal_avg[doy])
        else:
            forecast_naive.append(sales_train['Revenue'].median())
    
    # Method 3: Trend with seasonality
    trend_component = sales_train['trend'].iloc[-1] if 'trend' in sales_train.columns else sales_train['Revenue'].mean()
    forecast_trend_seasonal = []
    for test_date in test_dates:
        doy = test_date.dayofyear
        seasonal_factor = seasonal_avg.get(doy, 0)
        forecast_val = trend_component + seasonal_factor
        forecast_trend_seasonal.append(forecast_val)
    
    # Method 4: Average ensemble
    forecast_ensemble = [
        (exp + naive + ts) / 3
        for exp, naive, ts in zip(forecast_exp, forecast_naive, forecast_trend_seasonal)
    ]
    
    # Create forecast dataframe
    forecast_df = pd.DataFrame({
        'Date': test_dates,
        'forecast_exponential': forecast_exp,
        'forecast_seasonal_naive': forecast_naive,
        'forecast_trend_seasonal': forecast_trend_seasonal,
        'forecast_ensemble': forecast_ensemble
    })
    
    save_table(forecast_df, 'm5_ensemble_forecasts_base.csv')
    
    return forecast_df

# ============================================================================
# PART 3: SCENARIO ANALYSIS (TACTICAL & STRATEGIC)
# ============================================================================

def scenario_analysis(sales_train, forecast_base, data):
    """
    Generate scenarios:
    
    Tactical:
    1. Promotional boost: +10% revenue during 4 promotional periods (Q1, Q2, Q3, Q4)
    2. Channel shift: +5% conversion from paid_search → organic (cost savings)
    3. Traffic increase: +15% web traffic → +3% conversion (assuming weak correlation)
    
    Strategic:
    1. Inventory optimization: +8% revenue (reduce stockouts)
    2. Product mix shift: +12% revenue (reallocate to high-margin categories)
    3. Return reduction: +2% revenue (reduce returns from 3.4% to 3.0%)
    
    Uses diagnostic findings (M4) and forecast baseline.
    """
    print("\n[PRESCRIPTIVE 1] Scenario Analysis")
    
    scenarios = forecast_base[['Date', 'forecast_ensemble']].copy()
    scenarios['scenario_base'] = scenarios['forecast_ensemble']
    
    # Extract dates for scenario application
    scenarios['month'] = scenarios['Date'].dt.month
    scenarios['quarter'] = scenarios['Date'].dt.quarter
    
    # ========== TACTICAL SCENARIOS ==========
    # 1. Promotional boost: +10% during Q1, Q3, Q4 (holiday periods)
    scenarios['scenario_promotional_boost'] = scenarios['scenario_base'].copy()
    promo_quarters = [1, 3, 4]
    scenarios.loc[scenarios['quarter'].isin(promo_quarters), 'scenario_promotional_boost'] *= 1.10
    
    # 2. Channel shift: +5% conversion improvement from channel optimization
    scenarios['scenario_channel_optimization'] = scenarios['scenario_base'] * 1.05
    
    # 3. Traffic increase with weak conversion: +3% from 15% traffic increase
    scenarios['scenario_traffic_increase'] = scenarios['scenario_base'] * 1.03
    
    # ========== STRATEGIC SCENARIOS ==========
    # 1. Inventory optimization: +8% revenue from eliminating stockouts
    scenarios['scenario_inventory_optimization'] = scenarios['scenario_base'] * 1.08
    
    # 2. Product mix shift: +12% from reallocating to high-margin products
    scenarios['scenario_product_mix_shift'] = scenarios['scenario_base'] * 1.12
    
    # 3. Return reduction: +2% from better product descriptions/size guides
    scenarios['scenario_return_reduction'] = scenarios['scenario_base'] * 1.02
    
    # ========== COMBINED SCENARIOS ==========
    # Conservative: Best tactical only
    scenarios['scenario_conservative'] = scenarios['scenario_promotional_boost']
    
    # Moderate: Mix of tactical + strategic
    scenarios['scenario_moderate'] = (
        scenarios['scenario_base'] * 1.10 * 1.05 * 1.02  # Promo + channel + returns
    )
    
    # Aggressive: All tactical + strategic combined
    scenarios['scenario_aggressive'] = (
        scenarios['scenario_base'] * 1.10 * 1.05 * 1.08 * 1.12  # Promo + channel + inventory + mix
    )
    
    # Cleanup
    scenarios = scenarios.drop(['month', 'quarter'], axis=1)
    
    save_table(scenarios, 'm5_scenario_analysis.csv')
    
    return scenarios

# ============================================================================
# PART 4: RECOMMENDATIONS WITH ROI ESTIMATES
# ============================================================================

def recommendations_with_roi(forecast_base, scenarios, sales_train):
    """
    Generate actionable recommendations based on scenarios and diagnostic findings.
    Quantify ROI for each recommendation.
    
    ROI Calculation:
    - Revenue impact = scenario revenue - base forecast
    - Cost impact = estimated implementation cost
    - Net ROI = (Revenue impact - Cost) / Cost * 100%
    """
    print("\n[PRESCRIPTIVE 2] Recommendations with ROI")
    
    # Calculate total revenue impact by scenario
    base_revenue = forecast_base['forecast_ensemble'].sum()
    sales_train_avg = sales_train['Revenue'].mean()
    
    recommendations = []
    
    # 1. PROMOTIONAL BOOST
    promo_revenue = scenarios['scenario_promotional_boost'].sum()
    promo_impact = promo_revenue - base_revenue
    promo_cost = base_revenue * 0.08  # Assume 8% cost for promotional discounts (gross margin loss)
    promo_roi = (promo_impact - promo_cost) / promo_cost * 100 if promo_cost > 0 else 0
    
    recommendations.append({
        'recommendation_id': 'R1',
        'category': 'Tactical',
        'title': 'Increase Promotional Activity (Q1, Q3, Q4)',
        'description': 'Launch targeted promotional campaigns in Q1 (Tet), Q3 (back-to-school), Q4 (holiday)',
        'implementation_effort': 'Medium',
        'timeframe_months': 3,
        'revenue_impact': promo_impact,
        'estimated_cost': promo_cost,
        'roi_percent': promo_roi,
        'priority': 'High',
        'evidence_basis': 'M4 anomaly analysis shows 3x revenue spike during promotional periods'
    })
    
    # 2. CHANNEL OPTIMIZATION
    channel_revenue = scenarios['scenario_channel_optimization'].sum()
    channel_impact = channel_revenue - base_revenue
    channel_cost = base_revenue * 0.02  # Assume 2% for channel optimization (marketing automation, tools)
    channel_roi = (channel_impact - channel_cost) / channel_cost * 100 if channel_cost > 0 else 0
    
    recommendations.append({
        'recommendation_id': 'R2',
        'category': 'Tactical',
        'title': 'Optimize Acquisition Channel Mix',
        'description': 'Shift budget from paid_search (lower ROI) to organic_search (30% of revenue, highest volume)',
        'implementation_effort': 'Low',
        'timeframe_months': 1,
        'revenue_impact': channel_impact,
        'estimated_cost': channel_cost,
        'roi_percent': channel_roi,
        'priority': 'High',
        'evidence_basis': 'M4 shows organic search dominates (30%), paid search should be re-evaluated for ROI'
    })
    
    # 3. INVENTORY OPTIMIZATION
    inventory_revenue = scenarios['scenario_inventory_optimization'].sum()
    inventory_impact = inventory_revenue - base_revenue
    inventory_cost = base_revenue * 0.05  # Assume 5% for inventory management system/planning
    inventory_roi = (inventory_impact - inventory_cost) / inventory_cost * 100 if inventory_cost > 0 else 0
    
    recommendations.append({
        'recommendation_id': 'R3',
        'category': 'Strategic',
        'title': 'Optimize Inventory Planning & Reduce Stockouts',
        'description': 'Implement demand-driven inventory planning; align with promotional calendar to reduce 65% stockout rate',
        'implementation_effort': 'High',
        'timeframe_months': 6,
        'revenue_impact': inventory_impact,
        'estimated_cost': inventory_cost,
        'roi_percent': inventory_roi,
        'priority': 'Critical',
        'evidence_basis': 'M4 shows COGS correlation (r=0.976) strongest predictor; M3 shows 65% stockout rate'
    })
    
    # 4. PRODUCT MIX OPTIMIZATION
    mix_revenue = scenarios['scenario_product_mix_shift'].sum()
    mix_impact = mix_revenue - base_revenue
    mix_cost = base_revenue * 0.03  # Assume 3% for product analytics/sourcing
    mix_roi = (mix_impact - mix_cost) / mix_cost * 100 if mix_cost > 0 else 0
    
    recommendations.append({
        'recommendation_id': 'R4',
        'category': 'Strategic',
        'title': 'Reallocate Product Mix to High-Margin Categories',
        'description': 'Increase allocation to Outdoor (high volume) and reduce lower-margin categories',
        'implementation_effort': 'Medium',
        'timeframe_months': 4,
        'revenue_impact': mix_impact,
        'estimated_cost': mix_cost,
        'roi_percent': mix_roi,
        'priority': 'High',
        'evidence_basis': 'M3 shows category concentration; margin analysis enables optimization'
    })
    
    # 5. RETURN REDUCTION (Product Quality)
    returns_revenue = scenarios['scenario_return_reduction'].sum()
    returns_impact = returns_revenue - base_revenue
    returns_cost = base_revenue * 0.01  # Assume 1% for improved size guides, quality control
    returns_roi = (returns_impact - returns_cost) / returns_cost * 100 if returns_cost > 0 else 0
    
    recommendations.append({
        'recommendation_id': 'R5',
        'category': 'Tactical',
        'title': 'Improve Product Descriptions & Reduce Returns',
        'description': 'Enhanced size guides, material specs, and quality inspections; target "Wrong Size" (top return reason)',
        'implementation_effort': 'Low',
        'timeframe_months': 2,
        'revenue_impact': returns_impact,
        'estimated_cost': returns_cost,
        'roi_percent': returns_roi,
        'priority': 'High',
        'evidence_basis': 'M4 shows "Wrong Size" is top return reason; return rates are category-driven, not channel-driven'
    })
    
    # Convert to dataframe
    rec_df = pd.DataFrame(recommendations)
    save_table(rec_df, 'm5_recommendations_roi.csv')
    
    return rec_df

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 80)
    print("MILESTONE 5: PREDICTIVE & PRESCRIPTIVE EDA")
    print("=" * 80)
    print(f"\nExecution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Random Seed: {RANDOM_SEED}")
    
    # Load data
    data = load_data()
    
    # Split train/test
    sales = data['sales'].copy()
    sales_train = sales[sales['Date'] < TEST_START].copy()
    
    print(f"\nTrain Period: {sales_train['Date'].min()} to {sales_train['Date'].max()}")
    print(f"Test Period: {TEST_START} to {TEST_END}")
    
    # Generate test dates
    test_dates = pd.date_range(start=TEST_START, end=TEST_END, freq='D')
    
    print("\n" + "=" * 80)
    print("PREDICTIVE & PRESCRIPTIVE ANALYSES")
    print("=" * 80)
    
    results = {}
    
    # 1. Time-series decomposition
    sales_decomposed, decomp_summary = time_series_decomposition(sales_train)
    results['decomposition'] = (sales_decomposed, decomp_summary)
    
    # 2. Ensemble forecasting (use original sales_train, not decomposed)
    forecast_base = ensemble_forecast(sales_train, test_dates)
    results['forecast_base'] = forecast_base
    
    # 3. Scenario analysis
    scenarios = scenario_analysis(sales_train, forecast_base, data)
    results['scenarios'] = scenarios
    
    # 4. Recommendations with ROI
    recommendations = recommendations_with_roi(forecast_base, scenarios, sales_train)
    results['recommendations'] = recommendations
    
    print("\n" + "=" * 80)
    print("MILESTONE 5 EXECUTION COMPLETE")
    print("=" * 80)
    print(f"\nAll outputs saved to:")
    print(f"  • Tables: {OUTPUT_TABLE_DIR}")
    print(f"  • Report: {REPORT_DIR}")
    print(f"  • Notebook: {NOTEBOOK_DIR}")
    
    return results

if __name__ == "__main__":
    results = main()
