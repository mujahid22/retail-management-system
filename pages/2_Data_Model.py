"""Section 2 — Star Schema Data Model Viewer (Supabase-backed)."""
import pandas as pd
import streamlit as st

from utils.db_handler import get_client, load_all
from utils.logger import log_event

st.markdown('<div class="section-header">🗄️ Data Model — Star Schema</div>', unsafe_allow_html=True)
st.caption("Relational star schema powering the analytics layer. One fact table + four dimension tables.")
st.divider()

# ── Schema Diagram ──────────────────────────────────────────────────────────
with st.expander("📐 Schema Diagram", expanded=False):
    st.markdown("""
    ```
                     ┌──────────────────┐
                     │   dim_customer   │
                     │  customer_id PK  │
                     └────────┬─────────┘
                              │
    ┌──────────────┐  ┌───────┴──────────────────────┐  ┌──────────────────┐
    │  dim_product │  │         fact_sales            │  │  dim_geography   │
    │ product_id PK├──┤  sale_id PK                   ├──┤ geography_id PK  │
    └──────────────┘  │  transaction_id               │  └──────────────────┘
                      │  customer_id FK               │
    ┌──────────────┐  │  product_id FK                │
    │   dim_date   │  │  date_id FK                   │
    │  date_id PK  ├──┤  geography_id FK              │
    └──────────────┘  │  qty, unit_cost, unit_price   │
                      │  discount_pct, discount_amount │
                      │  subtotal, tax_rate, tax_amount│
                      │  total_amount, payment_mode    │
                      └───────────────────────────────┘
    ```
    """)

# ── Database Status ──────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_all_data():
    return load_all()

all_data   = get_all_data()
fact       = all_data.get("fact_sales", pd.DataFrame())
data_exists = len(fact) > 0

if data_exists:
    st.success(f"Supabase connected | **{len(fact):,}** rows in fact_sales")
else:
    st.warning("No data found in Supabase. Contact the IT administrator to seed the database.")

st.divider()

# ── Table Viewer ─────────────────────────────────────────────────────────────
if data_exists:
    # KPI strip
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("fact_sales rows",     f"{len(fact):,}")
    k2.metric("dim_customer rows",   f"{len(all_data.get('dim_customer',   [])):,}")
    k3.metric("dim_product rows",    f"{len(all_data.get('dim_product',    [])):,}")
    k4.metric("dim_date rows",       f"{len(all_data.get('dim_date',       [])):,}")
    k5.metric("dim_geography rows",  f"{len(all_data.get('dim_geography',  [])):,}")

    st.divider()

    table_tabs = st.tabs([
        "📊 fact_sales",
        "👤 dim_customer",
        "📦 dim_product",
        "📅 dim_date",
        "🌎 dim_geography",
    ])

    schema_docs = {
        "fact_sales":     "One row per line item sold. Links to all four dimensions.",
        "dim_customer":   "Customer demographics. Upserted on each new transaction.",
        "dim_product":    "Product catalog with pricing, category, and brand info.",
        "dim_date":       "Full calendar dimension from 2024-01-01 to 2025-12-31.",
        "dim_geography":  "City/state/region lookup. Upserted when a new city appears.",
    }

    sheet_names = ["fact_sales", "dim_customer", "dim_product", "dim_date", "dim_geography"]
    for tab, sheet in zip(table_tabs, sheet_names):
        with tab:
            df = all_data.get(sheet, pd.DataFrame())
            st.caption(schema_docs[sheet])
            st.caption(f"**{len(df):,} rows × {len(df.columns)} columns**")

            with st.expander("Column Definitions", expanded=False):
                col_info = pd.DataFrame({
                    "Column":   df.columns,
                    "Type":     [str(df[c].dtype) for c in df.columns],
                    "Non-Null": [df[c].count() for c in df.columns],
                    "Sample":   [str(df[c].iloc[0]) if not df.empty else "—" for c in df.columns],
                })
                st.dataframe(col_info, use_container_width=True, hide_index=True)

            search = st.text_input(f"Search {sheet}", placeholder="Type to filter…", key=f"search_{sheet}")
            display_df = df.copy()
            if search:
                mask = display_df.apply(
                    lambda col: col.astype(str).str.contains(search, case=False, na=False)
                ).any(axis=1)
                display_df = display_df[mask]

            st.dataframe(display_df.head(500), use_container_width=True, hide_index=True, height=380)
            if len(display_df) > 500:
                st.caption(f"Showing first 500 of {len(display_df):,} rows.")
else:
    st.info("Click **Generate Sample Data** above to seed the database and explore the schema tables.")
