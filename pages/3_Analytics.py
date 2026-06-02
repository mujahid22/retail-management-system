"""Section 2b — Sales Analytics Dashboard."""
from datetime import date

import pandas as pd
import streamlit as st

from utils.charts import (
    age_group_bar, category_revenue_bar, category_share_donut,
    clv_histogram, day_of_week_sales, gender_donut, monthly_revenue_trend,
    new_vs_returning, payment_mode_pie, price_qty_scatter,
    quarterly_revenue, region_pie, sales_heatmap, state_choropleth,
    top_cities_bar, top_products_bar,
)
from utils.db_handler import load_all

st.markdown('<div class="section-header">📊 Sales Analytics Dashboard</div>', unsafe_allow_html=True)
st.caption("Interactive analytics across time, product, geography, and customer dimensions.")


# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_compact(n: float, prefix: str = "") -> str:
    """Format a number with K/M suffix for compact display."""
    if abs(n) >= 1_000_000:
        return f"{prefix}{n / 1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{prefix}{n / 1_000:.1f}k"
    return f"{prefix}{n:,.0f}"


_KPI_ACCENTS = ["#FF6B35", "#4361EE", "#2EC4B6", "#7209B7", "#FB8500", "#023E8A"]
_kpi_idx = 0


def kpi_card(label: str, value: str, delta: str = None, delta_up: bool = None,
             accent: str = None) -> str:
    global _kpi_idx
    color = accent or _KPI_ACCENTS[_kpi_idx % len(_KPI_ACCENTS)]
    _kpi_idx += 1
    if delta is not None:
        if delta_up is True:
            dcolor, darrow = "#16A34A", "&#9650;"
        elif delta_up is False:
            dcolor, darrow = "#DC2626", "&#9660;"
        else:
            dcolor, darrow = "#6B7280", "&ndash;"
        delta_html = f'<div class="kpi-delta" style="color:{dcolor}">{darrow} {delta}</div>'
    else:
        delta_html = '<div class="kpi-delta" style="visibility:hidden">&ndash;</div>'
    return (
        f'<div class="kpi-card" style="border-top-color:{color};">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{color};">{value}</div>'
        f'{delta_html}'
        f'</div>'
    )


# ── Load & Join ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_analytics_data():
    sheets = load_all()
    fact = sheets["fact_sales"]
    dc = sheets["dim_customer"]
    dp = sheets["dim_product"]
    dd = sheets["dim_date"]
    dg = sheets["dim_geography"]

    # If any key table is empty, return an empty DataFrame so the caller shows the warning
    if fact.empty or dc.empty or dp.empty or dd.empty or dg.empty:
        return pd.DataFrame()

    df = (
        fact
        .merge(dc, on="customer_id", how="left")
        .merge(dp[["product_id", "product_name", "category", "sub_category", "brand"]], on="product_id", how="left")
        .merge(dd[["date_id", "full_date", "year", "quarter", "month", "month_name",
                   "week_of_year", "day_of_week", "day_name", "is_weekend"]], on="date_id", how="left")
        .merge(dg[["geography_id", "city", "state", "region"]], on="geography_id", how="left")
    )
    df["full_date"] = pd.to_datetime(df["full_date"])
    # Drop rows where the date join found no match (transaction date outside dim_date range)
    df = df.dropna(subset=["full_date", "year", "day_of_week"])
    df["day_of_week"] = df["day_of_week"].astype(int)
    df["week_of_year"] = df["week_of_year"].astype(int)
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    df["quarter"] = df["quarter"].astype(int)
    return df


df_full = load_analytics_data()

if df_full.empty:
    st.warning("No data found. Go to **Data Model** page and click **Generate Sample Data** first.")
    st.stop()

# ── Inline Filter Bar ─────────────────────────────────────────────────────────
from datetime import date as _date
min_date = df_full["full_date"].min().date()
max_date = df_full["full_date"].max().date()

_today        = _date.today()
_default_end  = min(_today, max_date)
try:
    _default_start = _default_end.replace(year=_default_end.year - 1)
except ValueError:
    _default_start = _default_end - pd.Timedelta(days=365)
_default_start = max(_default_start, min_date)

with st.container(border=True):
    st.markdown("##### 🔍 Dashboard Filters")
    fc1, fc2, fc3, fc4, fc5 = st.columns([2.2, 1.8, 1.8, 1.8, 0.8])

    with fc1:
        date_range = st.date_input(
            "Date Range",
            value=(_default_start, _default_end),
            min_value=min_date,
            max_value=max_date,
            label_visibility="visible",
        )
    with fc2:
        categories = st.multiselect(
            "Category",
            sorted(df_full["category"].dropna().unique()),
            default=[],
            placeholder="All",
        )
    with fc3:
        states = st.multiselect(
            "State",
            sorted(df_full["state"].dropna().unique()),
            default=[],
            placeholder="All",
        )
    with fc4:
        payment_modes = st.multiselect(
            "Payment Mode",
            sorted(df_full["payment_mode"].dropna().unique()),
            default=[],
            placeholder="All",
        )
    with fc5:
        st.write("")
        st.write("")
        if st.button("🔄", help="Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# ── Apply Filters ─────────────────────────────────────────────────────────────
df = df_full.copy()
df = df[(df["full_date"].dt.date >= start_date) & (df["full_date"].dt.date <= end_date)]
if categories:
    df = df[df["category"].isin(categories)]
if states:
    df = df[df["state"].isin(states)]
if payment_modes:
    df = df[df["payment_mode"].isin(payment_modes)]

if df.empty:
    st.error("No data matches the selected filters.")
    st.stop()

# ── KPI Calculations ──────────────────────────────────────────────────────────
total_revenue = df["total_amount"].sum()
total_transactions = df["transaction_id"].nunique()
avg_order_value = df.groupby("transaction_id")["total_amount"].sum().mean()
total_units = df["qty"].sum()
total_customers = df["customer_id"].nunique()
best_month_data = df.groupby(["year", "month_name"])["total_amount"].sum()
best_month = best_month_data.idxmax() if not best_month_data.empty else (0, "—")

# ── Prior Year Comparison (same calendar window, 1 year back) ─────────────────
# Only valid when prior period doesn't overlap the current selection
try:
    prior_start = start_date.replace(year=start_date.year - 1)
    prior_end = end_date.replace(year=end_date.year - 1)
except ValueError:
    prior_start = (pd.Timestamp(start_date) - pd.DateOffset(years=1)).date()
    prior_end = (pd.Timestamp(end_date) - pd.DateOffset(years=1)).date()

if prior_end >= start_date:
    # Periods overlap — comparison is not meaningful
    rev_delta_text = "Select ≤1 yr for YoY"
    rev_delta_up = None
else:
    df_prior = df_full[
        (df_full["full_date"].dt.date >= prior_start) &
        (df_full["full_date"].dt.date <= prior_end)
    ]
    if categories:
        df_prior = df_prior[df_prior["category"].isin(categories)]
    if states:
        df_prior = df_prior[df_prior["state"].isin(states)]
    if payment_modes:
        df_prior = df_prior[df_prior["payment_mode"].isin(payment_modes)]

    prior_revenue = df_prior["total_amount"].sum() if not df_prior.empty else 0
    if prior_revenue > 0:
        pct = (total_revenue - prior_revenue) / prior_revenue * 100
        rev_delta_text = f"{abs(pct):.1f}% vs prior yr"
        rev_delta_up = pct >= 0
    else:
        rev_delta_text = "No prior yr data"
        rev_delta_up = None

# ── KPI Strip ─────────────────────────────────────────────────────────────────
_kpi_idx = 0  # reset accent rotation on every rerun
st.markdown("#### Key Performance Indicators")
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.markdown(kpi_card("Total Revenue",    f"${fmt_compact(total_revenue)}",   rev_delta_text, rev_delta_up), unsafe_allow_html=True)
k2.markdown(kpi_card("Transactions",     fmt_compact(total_transactions),     None),           unsafe_allow_html=True)
k3.markdown(kpi_card("Avg Order Value",  f"${avg_order_value:,.2f}",          None),           unsafe_allow_html=True)
k4.markdown(kpi_card("Units Sold",       fmt_compact(total_units),            None),           unsafe_allow_html=True)
k5.markdown(kpi_card("Unique Customers", fmt_compact(total_customers),        None),           unsafe_allow_html=True)
k6.markdown(kpi_card("Best Month",       f"{str(best_month[1])[:3]} {best_month[0]}", None),  unsafe_allow_html=True)

st.divider()

# ── Analytics Tabs ────────────────────────────────────────────────────────────
tab_time, tab_product, tab_geo, tab_customer = st.tabs([
    "⏱️ Time Analytics",
    "📦 Product Analytics",
    "🌎 Geo Analytics",
    "👤 Customer Analytics",
])

# ── Tab 1: Time Analytics ─────────────────────────────────────────────────────
with tab_time:
    st.markdown("#### Revenue Over Time")
    st.plotly_chart(monthly_revenue_trend(df), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(quarterly_revenue(df), use_container_width=True)
    with col2:
        st.plotly_chart(day_of_week_sales(df), use_container_width=True)

    st.markdown("#### Sales Activity Heatmap")
    st.plotly_chart(sales_heatmap(df), use_container_width=True)

    # Monthly summary table
    st.markdown("#### Monthly Revenue Summary")
    monthly_tbl = (
        df.groupby(["year", "month", "month_name"])
        .agg(
            Revenue=("total_amount", "sum"),
            Transactions=("transaction_id", "nunique"),
            Units=("qty", "sum"),
            Avg_Order=("total_amount", "mean"),
        )
        .reset_index()
        .sort_values(["year", "month"])
    )
    monthly_tbl["Revenue"] = monthly_tbl["Revenue"].map("${:,.2f}".format)
    monthly_tbl["Avg_Order"] = monthly_tbl["Avg_Order"].map("${:,.2f}".format)
    monthly_tbl = monthly_tbl.drop(columns=["month"]).rename(columns={
        "year": "Year", "month_name": "Month", "Avg_Order": "Avg Order"
    })
    st.dataframe(monthly_tbl, use_container_width=True, hide_index=True)


# ── Tab 2: Product Analytics ──────────────────────────────────────────────────
with tab_product:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(category_revenue_bar(df), use_container_width=True)
    with col2:
        st.plotly_chart(category_share_donut(df), use_container_width=True)

    st.plotly_chart(top_products_bar(df, 15), use_container_width=True)
    st.plotly_chart(price_qty_scatter(df), use_container_width=True)

    # Category YoY table
    st.markdown("#### Category Year-over-Year Performance")
    yoy = df.groupby(["category", "year"])["total_amount"].sum().reset_index()
    pivot = yoy.pivot(index="category", columns="year", values="total_amount").fillna(0)
    pivot.columns = [f"Revenue {c}" for c in pivot.columns]
    years = sorted(df["year"].unique())
    if len(years) >= 2:
        y1, y2 = years[-2], years[-1]
        pivot[f"YoY Growth %"] = (
            (pivot[f"Revenue {y2}"] - pivot[f"Revenue {y1}"]) /
            pivot[f"Revenue {y1}"].replace(0, float("nan")) * 100
        ).round(1)
    for col in pivot.columns:
        if "Revenue" in col:
            pivot[col] = pivot[col].map("${:,.2f}".format)
        elif "Growth" in col:
            pivot[col] = pivot[col].map(lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A")
    st.dataframe(pivot.reset_index().rename(columns={"category": "Category"}),
                 use_container_width=True, hide_index=True)


# ── Tab 3: Geo Analytics ──────────────────────────────────────────────────────
with tab_geo:
    st.plotly_chart(state_choropleth(df), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(top_cities_bar(df, 20), use_container_width=True)
    with col2:
        st.plotly_chart(region_pie(df), use_container_width=True)

    # State summary table
    st.markdown("#### State-Level Sales Summary")
    state_tbl = (
        df.groupby(["state", "region"])
        .agg(
            Revenue=("total_amount", "sum"),
            Transactions=("transaction_id", "nunique"),
            Customers=("customer_id", "nunique"),
            Units=("qty", "sum"),
        )
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )
    state_tbl["Revenue"] = state_tbl["Revenue"].map("${:,.2f}".format)
    state_tbl.columns = ["State", "Region", "Revenue", "Transactions", "Customers", "Units"]
    st.dataframe(state_tbl, use_container_width=True, hide_index=True)


# ── Tab 4: Customer Analytics ─────────────────────────────────────────────────
with tab_customer:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.plotly_chart(gender_donut(df), use_container_width=True)
    with col2:
        st.plotly_chart(payment_mode_pie(df), use_container_width=True)
    with col3:
        st.plotly_chart(age_group_bar(df), use_container_width=True)

    st.plotly_chart(clv_histogram(df), use_container_width=True)
    st.plotly_chart(new_vs_returning(df), use_container_width=True)

    # Top customers table
    st.markdown("#### Top 20 Customers by Lifetime Value")
    top_cust = (
        df.groupby(["customer_id", "customer_name", "age_group", "gender"])
        .agg(
            Total_Spend=("total_amount", "sum"),
            Transactions=("transaction_id", "nunique"),
            Units=("qty", "sum"),
        )
        .reset_index()
        .sort_values("Total_Spend", ascending=False)
        .head(20)
    )
    top_cust["Total_Spend"] = top_cust["Total_Spend"].map("${:,.2f}".format)
    top_cust = top_cust.drop(columns=["customer_id"])
    top_cust.columns = ["Name", "Age Group", "Gender", "Total Spend", "Transactions", "Units"]
    st.dataframe(top_cust, use_container_width=True, hide_index=True)
