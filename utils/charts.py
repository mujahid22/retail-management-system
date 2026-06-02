"""Reusable Plotly chart builders — light executive theme."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Palette & theme constants ─────────────────────────────────────────────────
PALETTE     = ["#FF6B35", "#4361EE", "#2EC4B6", "#F72585", "#7209B7", "#FB8500", "#4CC9F0", "#023E8A"]
ACCENT      = "#FF6B35"
PAPER_BG    = "white"
PLOT_BG     = "#F8FAFB"
TITLE_COLOR = "#0A0A0A"
FONT_COLOR  = "#374151"
GRID_COLOR  = "#E5E7EB"

BASE_LAYOUT = dict(
    paper_bgcolor=PAPER_BG,
    plot_bgcolor=PLOT_BG,
    font=dict(color=FONT_COLOR, family="Segoe UI, Inter, Arial, sans-serif", size=12),
    title_font_color=TITLE_COLOR,
    title_font_size=15,
    title_font_family="Segoe UI, Inter, Arial, sans-serif",
    title_x=0.01,
    margin=dict(l=20, r=20, t=54, b=32),
    legend=dict(
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor="#E5E7EB",
        borderwidth=1,
        font=dict(size=11, color=FONT_COLOR),
    ),
    hoverlabel=dict(bgcolor="white", font_size=12, font_color=TITLE_COLOR),
)


def _apply(fig: go.Figure) -> go.Figure:
    fig.update_layout(**BASE_LAYOUT)
    fig.update_xaxes(
        gridcolor=GRID_COLOR, zeroline=False,
        linecolor="#E5E7EB", showline=True,
        tickfont=dict(color=FONT_COLOR, size=11),
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR, zeroline=False,
        linecolor=GRID_COLOR, showline=False,
        tickfont=dict(color=FONT_COLOR, size=11),
    )
    return fig


def _rgba(hex_color: str, alpha: float = 0.10) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Time Analytics ─────────────────────────────────────────────────────────────

def monthly_revenue_trend(df: pd.DataFrame) -> go.Figure:
    agg = (
        df.groupby(["year", "month", "month_name"])["total_amount"]
        .sum().reset_index().sort_values(["year", "month"])
    )
    agg["period"] = agg["month_name"].str[:3] + " " + agg["year"].astype(str)

    year_colors = [ACCENT, "#4361EE", "#2EC4B6"]
    fig = go.Figure()
    for i, year in enumerate(sorted(agg["year"].unique())):
        yd  = agg[agg["year"] == year]
        col = year_colors[i % len(year_colors)]
        fig.add_trace(go.Scatter(
            x=yd["period"], y=yd["total_amount"],
            name=str(year),
            mode="lines+markers",
            line=dict(color=col, width=2.5, shape="spline"),
            marker=dict(size=6, color=col, line=dict(color="white", width=1.5)),
            fill="tozeroy",
            fillcolor=_rgba(col, 0.08),
            hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
        ))

    fig.update_layout(
        title="Monthly Revenue Trend",
        yaxis=dict(tickprefix="$", tickformat=",", gridcolor=GRID_COLOR, zeroline=False, tickfont=dict(color=FONT_COLOR)),
        xaxis=dict(gridcolor=GRID_COLOR, zeroline=False, linecolor="#E5E7EB", showline=True,
                   tickfont=dict(color=FONT_COLOR, size=10), tickangle=-30),
        hovermode="x unified",
        **BASE_LAYOUT,
    )
    return fig


def day_of_week_sales(df: pd.DataFrame) -> go.Figure:
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    agg = df.groupby("day_name")["total_amount"].sum().reindex(order).reset_index()
    fig = px.bar(
        agg, x="day_name", y="total_amount",
        title="Sales by Day of Week",
        labels={"total_amount": "Revenue ($)", "day_name": ""},
        color="total_amount",
        color_continuous_scale=["#FFE4D6", ACCENT],
    )
    fig.update_traces(
        text=agg["total_amount"],
        texttemplate="$%{text:.2s}",
        textposition="outside",
        textfont=dict(color=FONT_COLOR, size=10),
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(yaxis=dict(tickprefix="$", tickformat=","))
    return _apply(fig)


def quarterly_revenue(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby(["year", "quarter"])["total_amount"].sum().reset_index()
    agg["label"] = "Q" + agg["quarter"].astype(str) + " " + agg["year"].astype(str)
    fig = px.bar(
        agg, x="label", y="total_amount", color="year",
        title="Quarterly Revenue",
        labels={"total_amount": "Revenue ($)", "label": ""},
        barmode="group",
        color_discrete_sequence=[ACCENT, "#4361EE", "#2EC4B6"],
    )
    fig.update_traces(
        text=agg["total_amount"],
        texttemplate="$%{text:.2s}",
        textposition="outside",
        textfont=dict(color=FONT_COLOR, size=10),
    )
    fig.update_layout(yaxis=dict(tickprefix="$", tickformat=","))
    return _apply(fig)


def sales_heatmap(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby(["week_of_year", "day_of_week"])["total_amount"].sum().reset_index()
    pivot = agg.pivot(index="day_of_week", columns="week_of_year", values="total_amount").fillna(0)
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=[day_labels[int(i)] for i in pivot.index],
        colorscale="Plasma",
        showscale=True,
        hovertemplate="Week %{x}, %{y}<br>Revenue: $%{z:,.0f}<extra></extra>",
        colorbar=dict(
            title="Revenue ($)",
            tickprefix="$",
            tickformat=",",
            tickfont=dict(color=FONT_COLOR, size=10),
            title_font=dict(color=FONT_COLOR, size=11),
        ),
    ))
    fig.update_layout(
        title="Sales Activity Heatmap — Week x Day",
        xaxis=dict(title="Week of Year", tickfont=dict(color=FONT_COLOR, size=10)),
        yaxis=dict(tickfont=dict(color=FONT_COLOR, size=11)),
        **BASE_LAYOUT,
    )
    return fig


# ── Product Analytics ──────────────────────────────────────────────────────────

def category_revenue_bar(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby("category")["total_amount"].sum().sort_values().reset_index()
    fig = px.bar(
        agg, x="total_amount", y="category", orientation="h",
        title="Revenue by Category",
        labels={"total_amount": "Revenue ($)", "category": ""},
        color="total_amount",
        color_continuous_scale=["#FFE4D6", ACCENT],
    )
    fig.update_traces(
        text=agg["total_amount"],
        texttemplate="$%{text:.2s}",
        textposition="outside",
        textfont=dict(color=FONT_COLOR, size=10),
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(xaxis=dict(tickprefix="$", tickformat=","))
    return _apply(fig)


def category_share_donut(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby("category")["total_amount"].sum().reset_index()
    fig = px.pie(
        agg, names="category", values="total_amount",
        title="Category Revenue Share",
        hole=0.55,
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        textfont_size=11,
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f} — %{percent}<extra></extra>",
        pull=[0.02] * len(agg),
        marker=dict(line=dict(color="white", width=2)),
    )
    return _apply(fig)


def top_products_bar(df: pd.DataFrame, n: int = 15) -> go.Figure:
    agg = df.groupby("product_name")["total_amount"].sum().nlargest(n).reset_index()
    fig = px.bar(
        agg, x="total_amount", y="product_name", orientation="h",
        title=f"Top {n} Products by Revenue",
        labels={"total_amount": "Revenue ($)", "product_name": ""},
        color="total_amount",
        color_continuous_scale=["#C7D8FF", "#4361EE"],
    )
    fig.update_traces(
        text=agg["total_amount"],
        texttemplate="$%{text:.2s}",
        textposition="outside",
        textfont=dict(color=FONT_COLOR, size=10),
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        xaxis=dict(tickprefix="$", tickformat=","),
    )
    return _apply(fig)


def price_qty_scatter(df: pd.DataFrame) -> go.Figure:
    agg = (
        df.groupby(["product_name", "category"])
        .agg(total_qty=("qty", "sum"), avg_price=("unit_price", "mean"), revenue=("total_amount", "sum"))
        .reset_index()
    )
    fig = px.scatter(
        agg, x="avg_price", y="total_qty",
        size="revenue", color="category",
        hover_name="product_name",
        title="Price vs Units Sold  (bubble size = revenue)",
        labels={"avg_price": "Avg Unit Price ($)", "total_qty": "Total Units Sold"},
        color_discrete_sequence=PALETTE,
        size_max=44,
        opacity=0.82,
    )
    fig.update_layout(xaxis=dict(tickprefix="$"))
    return _apply(fig)


# ── Geo Analytics ──────────────────────────────────────────────────────────────

def state_choropleth(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby("state")["total_amount"].sum().reset_index()
    fig = px.choropleth(
        agg, locations="state", locationmode="USA-states",
        color="total_amount", scope="usa",
        title="Revenue by US State",
        color_continuous_scale="Oranges",
        labels={"total_amount": "Revenue ($)"},
    )
    fig.update_layout(
        **BASE_LAYOUT,
        geo=dict(
            bgcolor="white",
            lakecolor="#EFF6FF",
            landcolor="#F1F5F9",
            subunitcolor="#CBD5E1",
            showlakes=True,
        ),
        coloraxis_colorbar=dict(
            title="Revenue",
            tickprefix="$",
            tickformat=",",
            tickfont=dict(color=FONT_COLOR, size=10),
            title_font=dict(color=FONT_COLOR, size=11),
        ),
    )
    return fig


def top_cities_bar(df: pd.DataFrame, n: int = 20) -> go.Figure:
    agg = df.groupby("city")["total_amount"].sum().nlargest(n).reset_index()
    fig = px.bar(
        agg, x="total_amount", y="city", orientation="h",
        title=f"Top {n} Cities by Revenue",
        labels={"total_amount": "Revenue ($)", "city": ""},
        color="total_amount",
        color_continuous_scale=["#BFDBFE", "#023E8A"],
    )
    fig.update_traces(
        text=agg["total_amount"],
        texttemplate="$%{text:.2s}",
        textposition="outside",
        textfont=dict(color=FONT_COLOR, size=10),
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        xaxis=dict(tickprefix="$", tickformat=","),
    )
    return _apply(fig)


def region_pie(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby("region")["total_amount"].sum().reset_index()
    fig = px.pie(
        agg, names="region", values="total_amount",
        title="Revenue by US Region",
        hole=0.5,
        color_discrete_sequence=[ACCENT, "#4361EE", "#2EC4B6", "#7209B7"],
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont_size=12,
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f} — %{percent}<extra></extra>",
        pull=[0.03] * len(agg),
        marker=dict(line=dict(color="white", width=2)),
    )
    return _apply(fig)


# ── Customer Analytics ─────────────────────────────────────────────────────────

def age_group_bar(df: pd.DataFrame) -> go.Figure:
    order = ["0-2", "3-5", "6-8", "9-12", "13-17", "18+"]
    agg = df.groupby("age_group")["total_amount"].sum().reindex(order).reset_index()
    fig = px.bar(
        agg, x="age_group", y="total_amount",
        title="Revenue by Age Group",
        labels={"total_amount": "Revenue ($)", "age_group": "Age Group"},
        color="total_amount",
        color_continuous_scale=["#EDE9FE", "#7209B7"],
    )
    fig.update_traces(
        text=agg["total_amount"],
        texttemplate="$%{text:.2s}",
        textposition="outside",
        textfont=dict(color=FONT_COLOR, size=10),
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(yaxis=dict(tickprefix="$", tickformat=","))
    return _apply(fig)


def gender_donut(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby("gender")["total_amount"].sum().reset_index()
    fig = px.pie(
        agg, names="gender", values="total_amount",
        title="Revenue by Gender",
        hole=0.56,
        color_discrete_sequence=[ACCENT, "#4361EE", "#2EC4B6", "#7209B7"],
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont_size=11,
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f} — %{percent}<extra></extra>",
        marker=dict(line=dict(color="white", width=2)),
    )
    return _apply(fig)


def payment_mode_pie(df: pd.DataFrame) -> go.Figure:
    agg = df.groupby("payment_mode")["total_amount"].sum().reset_index()
    fig = px.pie(
        agg, names="payment_mode", values="total_amount",
        title="Payment Method Breakdown",
        hole=0.5,
        color_discrete_sequence=["#2EC4B6", "#4361EE", ACCENT, "#7209B7", "#FB8500"],
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont_size=11,
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f} — %{percent}<extra></extra>",
        marker=dict(line=dict(color="white", width=2)),
    )
    return _apply(fig)


def clv_histogram(df: pd.DataFrame) -> go.Figure:
    clv = df.groupby("customer_id")["total_amount"].sum().reset_index()
    clv.columns = ["customer_id", "lifetime_value"]
    fig = px.histogram(
        clv, x="lifetime_value", nbins=40,
        title="Customer Lifetime Value Distribution",
        labels={"lifetime_value": "Total Lifetime Spend ($)", "count": "# Customers"},
        color_discrete_sequence=[ACCENT],
        opacity=0.88,
    )
    fig.update_traces(marker_line_color="white", marker_line_width=0.6)
    fig.update_layout(
        xaxis=dict(tickprefix="$", tickformat=","),
        bargap=0.04,
    )
    return _apply(fig)


def new_vs_returning(df: pd.DataFrame) -> go.Figure:
    first_purchase = df.groupby("customer_id")["full_date"].min().reset_index()
    first_purchase.columns = ["customer_id", "first_date"]
    merged = df.merge(first_purchase, on="customer_id")
    merged["customer_type"] = merged.apply(
        lambda r: "New" if r["full_date"] == r["first_date"] else "Returning", axis=1
    )
    agg = (
        merged.groupby(["year", "month", "month_name", "customer_type"])["transaction_id"]
        .nunique().reset_index()
    ).sort_values(["year", "month"])
    agg["period"] = agg["month_name"].str[:3] + " " + agg["year"].astype(str)
    fig = px.bar(
        agg, x="period", y="transaction_id", color="customer_type",
        title="New vs Returning Customers — Monthly Transactions",
        labels={"transaction_id": "Transactions", "period": "", "customer_type": "Customer Type"},
        barmode="stack",
        color_discrete_map={"New": ACCENT, "Returning": "#4361EE"},
    )
    fig.update_layout(xaxis_tickangle=-30)
    return _apply(fig)
