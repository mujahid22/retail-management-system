"""Supabase-backed data handler — replaces excel_handler.py."""
from __future__ import annotations

from datetime import date as date_type

import pandas as pd
import streamlit as st
from supabase import Client, create_client

SHEET_NAMES = ["fact_sales", "dim_customer", "dim_product", "dim_date", "dim_geography"]


# ── Supabase client (singleton, cached for the lifetime of the server process) ─

@st.cache_resource
def get_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# ── Internal pagination helper ────────────────────────────────────────────────

def _fetch_all(table: str) -> list[dict]:
    """Fetch every row in a table, working around Supabase's 1 000-row cap."""
    client = get_client()
    rows: list[dict] = []
    offset, batch = 0, 1000
    while True:
        result = (
            client.table(table)
            .select("*")
            .range(offset, offset + batch - 1)
            .execute()
        )
        rows.extend(result.data)
        if len(result.data) < batch:
            break
        offset += batch
    return rows


# ── Public API — mirrors excel_handler.py exactly ────────────────────────────

def load_all() -> dict[str, pd.DataFrame]:
    """Return all five star-schema tables as DataFrames."""
    return {t: pd.DataFrame(_fetch_all(t)) for t in SHEET_NAMES}


def load_sheet(sheet: str) -> pd.DataFrame:
    """Return a single table as a DataFrame."""
    return pd.DataFrame(_fetch_all(sheet))


def upsert_customer(data: dict) -> str:
    """Return existing customer_id for this email, or insert and return a new one."""
    client = get_client()
    result = (
        client.table("dim_customer")
        .select("customer_id")
        .eq("email", data["email"].lower())
        .execute()
    )
    if result.data:
        return result.data[0]["customer_id"]

    count = (
        client.table("dim_customer")
        .select("customer_id", count="exact")
        .execute()
        .count
    ) or 0
    new_id = f"C{count + 1:06d}"
    client.table("dim_customer").insert({
        "customer_id":   new_id,
        "customer_name": data["customer_name"],
        "email":         data["email"].lower(),
        "phone":         data.get("phone", ""),
        "age_group":     data.get("age_group", ""),
        "gender":        data.get("gender", ""),
    }).execute()
    return new_id


def upsert_geography(data: dict) -> str:
    """Return existing geography_id for this city+state, or insert and return a new one."""
    client = get_client()
    result = (
        client.table("dim_geography")
        .select("geography_id")
        .ilike("city", data["city"])
        .eq("state", data["state"].upper())
        .execute()
    )
    if result.data:
        return result.data[0]["geography_id"]

    from utils.schema import US_REGIONS
    region = next(
        (r for r, states in US_REGIONS.items() if data["state"].upper() in states),
        "Other",
    )
    count = (
        client.table("dim_geography")
        .select("geography_id", count="exact")
        .execute()
        .count
    ) or 0
    new_id = f"G{count + 1:04d}"
    client.table("dim_geography").insert({
        "geography_id": new_id,
        "city":         data["city"],
        "state":        data["state"].upper(),
        "region":       region,
        "zip_code":     data.get("zip_code", "00000"),
    }).execute()
    return new_id


def ensure_date_exists(d) -> None:
    """Insert d into dim_date if not already present."""
    if not isinstance(d, date_type):
        d = pd.Timestamp(d).date()
    date_id = int(d.strftime("%Y%m%d"))

    client = get_client()
    if client.table("dim_date").select("date_id").eq("date_id", date_id).execute().data:
        return

    iso = d.isocalendar()
    client.table("dim_date").insert({
        "date_id":      date_id,
        "full_date":    d.isoformat(),
        "year":         d.year,
        "quarter":      (d.month - 1) // 3 + 1,
        "month":        d.month,
        "month_name":   d.strftime("%B"),
        "week_of_year": iso[1],
        "day_of_week":  d.weekday(),
        "day_name":     d.strftime("%A"),
        "is_weekend":   d.weekday() >= 5,
    }).execute()


def next_sale_id() -> str:
    """Return the next sequential sale_id (e.g. 'S00000042')."""
    client = get_client()
    result = (
        client.table("fact_sales")
        .select("sale_id")
        .order("sale_id", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return "S00000001"
    return f"S{int(result.data[0]['sale_id'][1:]) + 1:08d}"


def append_sale_rows(rows: list[dict]) -> None:
    """Batch-insert completed sale line items into fact_sales."""
    get_client().table("fact_sales").insert(rows).execute()
