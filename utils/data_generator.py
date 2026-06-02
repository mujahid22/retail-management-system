"""Generate 2-year synthetic sales data for the toys retail store."""
import hashlib
import random
import uuid
from datetime import date, timedelta

import pandas as pd
from faker import Faker

from utils.schema import (
    AGE_GROUPS, CATEGORIES, GENDERS, PAYMENT_MODES,
    STATE_ABBREVS, TAX_BY_STATE, US_REGIONS,
)

fake = Faker("en_US")
Faker.seed(42)
random.seed(42)

BRANDS = [
    "ToyWorld", "PlayMaster", "KidZone", "FunFactory", "BrightPlay",
    "SmartKidz", "WonderToys", "JoyBurst", "StarPlay", "TinyWonders",
    "MegaFun", "SuperPlay", "NovaToys", "ArcadePals", "DreamToys",
]

CITY_STATE_MAP = {
    "New York": "NY", "Los Angeles": "CA", "Chicago": "IL", "Houston": "TX",
    "Phoenix": "AZ", "Philadelphia": "PA", "San Antonio": "TX", "San Diego": "CA",
    "Dallas": "TX", "San Jose": "CA", "Austin": "TX", "Jacksonville": "FL",
    "Fort Worth": "TX", "Columbus": "OH", "Charlotte": "NC", "Indianapolis": "IN",
    "San Francisco": "CA", "Seattle": "WA", "Denver": "CO", "Nashville": "TN",
    "Oklahoma City": "OK", "El Paso": "TX", "Boston": "MA", "Portland": "OR",
    "Las Vegas": "NV", "Memphis": "TN", "Louisville": "KY", "Baltimore": "MD",
    "Milwaukee": "WI", "Albuquerque": "NM", "Tucson": "AZ", "Fresno": "CA",
    "Mesa": "AZ", "Sacramento": "CA", "Atlanta": "GA", "Kansas City": "MO",
    "Omaha": "NE", "Colorado Springs": "CO", "Raleigh": "NC", "Long Beach": "CA",
    "Virginia Beach": "VA", "Minneapolis": "MN", "Tampa": "FL", "New Orleans": "LA",
    "Arlington": "TX", "Wichita": "KS", "Bakersfield": "CA", "Aurora": "CO",
    "Anaheim": "CA", "Santa Ana": "CA",
}


def _get_region(state: str) -> str:
    for region, states in US_REGIONS.items():
        if state in states:
            return region
    return "Other"


def _seasonal_weight(d: date) -> float:
    """Higher sales in Nov-Dec holiday season and spring."""
    month = d.month
    if month in (11, 12):
        return 3.5
    if month in (3, 4):
        return 1.5
    if month in (6, 7, 8):
        return 1.2
    return 1.0


def build_dim_customer(n: int = 500) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        email = fake.email()
        rows.append({
            # Hash email -> stable ID so upsert on PK works across reseeds
            "customer_id":   "C" + hashlib.md5(email.encode()).hexdigest()[:11].upper(),
            "customer_name": fake.name(),
            "email":         email,
            "phone":         fake.phone_number(),
            "age_group":     random.choice(AGE_GROUPS),
            "gender":        random.choice(GENDERS),
        })
    return pd.DataFrame(rows).drop_duplicates(subset=["email"]).reset_index(drop=True)


def build_dim_product() -> pd.DataFrame:
    rows = []
    product_id = 1
    for category, subs in CATEGORIES.items():
        per_sub = max(2, 10 // len(subs))
        for sub in subs:
            for _ in range(per_sub):
                cost = round(random.uniform(3.0, 85.0), 2)
                margin = random.uniform(0.35, 0.65)
                price = round(cost * (1 + margin), 2)
                brand = random.choice(BRANDS)
                name = f"{brand} {sub} {category} #{product_id}"
                rows.append({
                    "product_id": f"P{product_id:04d}",
                    "product_name": name,
                    "category": category,
                    "sub_category": sub,
                    "brand": brand,
                    "sku": f"SKU-{product_id:05d}",
                    "unit_cost": cost,
                    "unit_price": price,
                })
                product_id += 1
    return pd.DataFrame(rows)


def build_dim_date(start: date, end: date) -> pd.DataFrame:
    rows = []
    current = start
    while current <= end:
        rows.append({
            "date_id": int(current.strftime("%Y%m%d")),
            "full_date": current,
            "year": current.year,
            "quarter": (current.month - 1) // 3 + 1,
            "month": current.month,
            "month_name": current.strftime("%B"),
            "week_of_year": current.isocalendar()[1],
            "day_of_week": current.weekday(),
            "day_name": current.strftime("%A"),
            "is_weekend": current.weekday() >= 5,
        })
        current += timedelta(days=1)
    return pd.DataFrame(rows)


def build_dim_geography() -> pd.DataFrame:
    rows = []
    geo_id = 1
    for city, state in CITY_STATE_MAP.items():
        rows.append({
            "geography_id": f"G{geo_id:04d}",
            "city": city,
            "state": state,
            "region": _get_region(state),
            "zip_code": fake.zipcode_in_state(state),
        })
        geo_id += 1
    return pd.DataFrame(rows)


def build_fact_sales(
    dim_customer: pd.DataFrame,
    dim_product: pd.DataFrame,
    dim_date: pd.DataFrame,
    dim_geography: pd.DataFrame,
    target_rows: int = 10000,
) -> pd.DataFrame:
    customers = dim_customer["customer_id"].tolist()
    products = dim_product.set_index("product_id")[["unit_cost", "unit_price", "category"]].to_dict("index")
    product_ids = list(products.keys())
    dates = dim_date[["date_id", "full_date"]].copy()
    geo_rows = dim_geography[["geography_id", "state"]].to_dict("records")

    all_dates = dates["date_id"].tolist()
    date_weights = [
        _seasonal_weight(pd.to_datetime(str(d)).date()) for d in all_dates
    ]

    rows = []
    sale_id = 1
    generated = 0
    while generated < target_rows:
        transaction_id = str(uuid.uuid4())[:16]
        items_in_txn = random.choices([1, 2, 3, 4, 5], weights=[40, 25, 15, 12, 8])[0]
        date_id = random.choices(all_dates, weights=date_weights)[0]
        customer_id = random.choice(customers)
        geo = random.choice(geo_rows)
        payment_mode = random.choice(PAYMENT_MODES)
        tax_rate = TAX_BY_STATE.get(geo["state"], 5.0)

        for _ in range(items_in_txn):
            pid = random.choice(product_ids)
            pdata = products[pid]
            qty = random.choices([1, 2, 3, 4, 5, 6], weights=[45, 25, 14, 8, 5, 3])[0]
            discount_pct = random.choices(
                [0, 5, 10, 15, 20, 25],
                weights=[50, 15, 15, 10, 7, 3],
            )[0]
            unit_price = pdata["unit_price"]
            unit_cost = pdata["unit_cost"]
            subtotal = round(unit_price * qty, 2)
            discount_amount = round(subtotal * discount_pct / 100, 2)
            taxable = round(subtotal - discount_amount, 2)
            tax_amount = round(taxable * tax_rate / 100, 2)
            total_amount = round(taxable + tax_amount, 2)

            rows.append({
                "sale_id": f"S{sale_id:08d}",
                "transaction_id": transaction_id,
                "customer_id": customer_id,
                "product_id": pid,
                "date_id": date_id,
                "geography_id": geo["geography_id"],
                "qty": qty,
                "unit_cost": unit_cost,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "discount_amount": discount_amount,
                "subtotal": subtotal,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "total_amount": total_amount,
                "payment_mode": payment_mode,
            })
            sale_id += 1
            generated += 1
            if generated >= target_rows:
                break

    return pd.DataFrame(rows)


def seed_database(target_rows: int = 10000) -> None:
    """Idempotent reseed: 2 years of data ending today. Safe to run multiple times."""
    from datetime import date as date_type
    from utils.db_handler import get_client

    client = get_client()

    # Reset seeds so generation is identical every run
    Faker.seed(42)
    random.seed(42)

    end_date   = date_type.today()
    start_date = date_type(end_date.year - 2, end_date.month, end_date.day)

    def _is_empty(table: str, id_col: str) -> bool:
        """Return True if the table has no rows (uses limit-1 SELECT)."""
        return not client.table(table).select(id_col).limit(1).execute().data

    def _drain(table: str, id_col: str, is_int: bool = False) -> None:
        """DELETE in a loop until the table is confirmed empty."""
        while not _is_empty(table, id_col):
            if is_int:
                client.table(table).delete().gte(id_col, 0).execute()
            else:
                client.table(table).delete().neq(id_col, "").execute()

    def _upsert_batches(table: str, df: pd.DataFrame, batch: int = 500) -> None:
        records = df.to_dict("records")
        for i in range(0, len(records), batch):
            client.table(table).upsert(records[i: i + batch]).execute()

    # ── 1. Clear all star-schema tables ──────────────────────────────────────
    # Strategy: try the atomic RPC first, then verify each table via SELECT,
    # and drain any that still have rows. This handles both the case where the
    # RPC works (fast path) and where it doesn't (safe fallback).
    print("Attempting atomic truncation via RPC...")
    try:
        client.rpc("truncate_star_schema", {}).execute()
    except Exception as exc:
        print(f"  RPC raised: {exc} — will drain manually.")

    # Drain in FK-safe order: fact_sales must be empty before dims can be cleared.
    TABLE_ORDER = [
        ("fact_sales",    "sale_id",       False),
        ("dim_customer",  "customer_id",   False),
        ("dim_product",   "product_id",    False),
        ("dim_date",      "date_id",       True),
        ("dim_geography", "geography_id",  False),
    ]
    for tbl, col, is_int in TABLE_ORDER:
        if not _is_empty(tbl, col):
            print(f"  {tbl} still has rows — draining...")
            _drain(tbl, col, is_int)
        print(f"  {tbl} [empty]")

    # ── 2. Generate all DataFrames in memory ──────────────────────────────────
    print("Generating dim_customer...")
    dc = build_dim_customer(500)
    print("Generating dim_product...")
    dp = build_dim_product()
    print(f"Generating dim_date ({start_date} -> {end_date})...")
    dd_raw = build_dim_date(start_date, end_date)
    print("Generating dim_geography...")
    dg = build_dim_geography()
    print(f"Generating fact_sales (~{target_rows} rows)...")
    fs = build_fact_sales(dc, dp, dd_raw, dg, target_rows)

    # Convert dim_date dates -> ISO strings for Supabase
    dd = dd_raw.copy()
    dd["full_date"]  = dd["full_date"].apply(lambda d: d.isoformat())
    dd["is_weekend"] = dd["is_weekend"].astype(bool)

    # ── 3. Upsert dim tables — on_conflict handles duplicate emails/PKs ───────
    #       fact_sales is empty so no FK constraints block the upserts.
    print("Upserting dim_customer...")
    _upsert_batches("dim_customer",  dc)
    print("Upserting dim_product...")
    _upsert_batches("dim_product",   dp)
    print("Upserting dim_date...")
    _upsert_batches("dim_date",      dd)
    print("Upserting dim_geography...")
    _upsert_batches("dim_geography", dg)

    # ── 4. Insert fresh fact_sales (already empty from step 1) ───────────────
    print("Inserting fact_sales...")
    _upsert_batches("fact_sales", fs)

    print(f"Done. Seeded {target_rows:,} rows from {start_date} to {end_date}.")
