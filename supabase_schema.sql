-- ══════════════════════════════════════════════════════════════════
-- ToyWorld Retail — Supabase Schema
-- Paste this entire file into Supabase → SQL Editor → Run
-- ══════════════════════════════════════════════════════════════════

-- 1. Dimension: Customers
CREATE TABLE IF NOT EXISTS dim_customer (
  customer_id   TEXT PRIMARY KEY,
  customer_name TEXT NOT NULL,
  email         TEXT UNIQUE NOT NULL,
  phone         TEXT,
  age_group     TEXT,
  gender        TEXT
);

-- 2. Dimension: Products
CREATE TABLE IF NOT EXISTS dim_product (
  product_id   TEXT PRIMARY KEY,
  product_name TEXT NOT NULL,
  category     TEXT,
  sub_category TEXT,
  brand        TEXT,
  sku          TEXT UNIQUE,
  unit_cost    NUMERIC(10,2),
  unit_price   NUMERIC(10,2)
);

-- 3. Dimension: Date calendar (date_id format = YYYYMMDD integer)
CREATE TABLE IF NOT EXISTS dim_date (
  date_id      INTEGER PRIMARY KEY,
  full_date    DATE    NOT NULL,
  year         INTEGER,
  quarter      INTEGER,
  month        INTEGER,
  month_name   TEXT,
  week_of_year INTEGER,
  day_of_week  INTEGER,
  day_name     TEXT,
  is_weekend   BOOLEAN
);

-- 4. Dimension: Geography
CREATE TABLE IF NOT EXISTS dim_geography (
  geography_id TEXT PRIMARY KEY,
  city         TEXT NOT NULL,
  state        TEXT NOT NULL,
  region       TEXT,
  zip_code     TEXT,
  UNIQUE (city, state)
);

-- 5. Fact: Sales — one row per line item sold
CREATE TABLE IF NOT EXISTS fact_sales (
  sale_id         TEXT PRIMARY KEY,
  transaction_id  TEXT           NOT NULL,
  customer_id     TEXT           REFERENCES dim_customer(customer_id),
  product_id      TEXT           REFERENCES dim_product(product_id),
  date_id         INTEGER        REFERENCES dim_date(date_id),
  geography_id    TEXT           REFERENCES dim_geography(geography_id),
  qty             INTEGER        NOT NULL,
  unit_cost       NUMERIC(10,2),
  unit_price      NUMERIC(10,2),
  discount_pct    NUMERIC(5,2)   DEFAULT 0,
  discount_amount NUMERIC(10,2)  DEFAULT 0,
  subtotal        NUMERIC(10,2),
  tax_rate        NUMERIC(5,2)   DEFAULT 0,
  tax_amount      NUMERIC(10,2)  DEFAULT 0,
  total_amount    NUMERIC(10,2)  NOT NULL,
  payment_mode    TEXT
);

-- 6. Session log (replaces session_log.csv)
CREATE TABLE IF NOT EXISTS session_log (
  session_id    TEXT PRIMARY KEY,
  role          TEXT        NOT NULL,
  login_time    TIMESTAMPTZ NOT NULL,
  logout_time   TIMESTAMPTZ,
  duration_mins NUMERIC(8,1),
  logout_type   TEXT
);

-- 7. System event log (replaces system_log.csv)
CREATE TABLE IF NOT EXISTS system_log (
  log_id    TEXT        PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  level     TEXT        NOT NULL,
  source    TEXT,
  event     TEXT,
  message   TEXT
);

-- ══════════════════════════════════════════════════════════════════
-- Disable Row Level Security on all tables
-- This is required so the anon key can read and write freely.
-- Appropriate for a demo/portfolio app.
-- ══════════════════════════════════════════════════════════════════
ALTER TABLE dim_customer  DISABLE ROW LEVEL SECURITY;
ALTER TABLE dim_product   DISABLE ROW LEVEL SECURITY;
ALTER TABLE dim_date      DISABLE ROW LEVEL SECURITY;
ALTER TABLE dim_geography DISABLE ROW LEVEL SECURITY;
ALTER TABLE fact_sales    DISABLE ROW LEVEL SECURITY;
ALTER TABLE session_log   DISABLE ROW LEVEL SECURITY;
ALTER TABLE system_log    DISABLE ROW LEVEL SECURITY;

-- ══════════════════════════════════════════════════════════════════
-- Helper function: truncate all star-schema tables in one call
-- Called by the "Reseed Data" button in the Data Model page
-- ══════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION truncate_star_schema()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  TRUNCATE TABLE fact_sales, dim_customer, dim_product, dim_date, dim_geography CASCADE;
END;
$$;
