# ToyWorld Retail Management System

> A full-stack retail management platform built with **Streamlit**, **Supabase (PostgreSQL)**, and **Plotly** — featuring a live POS terminal, star-schema analytics, and an IT admin hub, all with role-based access control.

**Live demo → [retail-management-system-hq8rsabsyekwtvb48c9jty.streamlit.app](https://retail-management-system-hq8rsabsyekwtvb48c9jty.streamlit.app)**

---

## Functional Architecture

The system is organised around three user roles, each with access to a specific set of pages. Every interaction is logged and persists to Supabase.

```
┌─────────────────────────────────────────────────────────────────┐
│                       LOGIN  (role selector)                     │
└──────────┬──────────────────┬───────────────────────────────────┘
           │                  │                         │
     [Cashier]         [Store Manager]            [IT Manager]
           │                  │                         │
     ┌─────▼─────┐    ┌───────▼───────┐    ┌───────────▼──────────┐
     │  Point of │    │  Point of Sale│    │  Point of Sale        │
     │  Sale     │    │  + Analytics  │    │  + Data Model         │
     └───────────┘    └───────────────┘    │  + Analytics          │
                                           │  + Admin Hub          │
                                           └───────────────────────┘
```

### Pages

| Page | Roles | What it does |
|---|---|---|
| **Point of Sale** | All | Product scanner → cart builder → customer info → payment → receipt modal |
| **Data Model** | IT Manager | Star schema viewer — 5 tables with row counts, column types, and search |
| **Sales Analytics** | Store Manager, IT Manager | 6 KPI cards + 16 interactive Plotly charts across 4 analytic dimensions |
| **Admin Hub** | IT Manager | Session tracking, system event log, and data store health panel |

---

## Technical Architecture

```
┌─────────────────────── Presentation Layer ───────────────────────┐
│  Streamlit 1.58  ·  4 pages  ·  Role-based navigation            │
│  Custom CSS dark sidebar  ·  Light executive chart theme          │
└───────────────┬──────────────────────────────┬────────────────────┘
                │  reads / writes              │  renders
┌───────────────▼────────────────┐  ┌──────────▼─────────────────┐
│    Python Processing Layer      │  │   Plotly 6.7 Charts        │
│  utils/db_handler.py            │  │  16 chart functions        │
│  utils/logger.py                │  │  Light theme · value       │
│  utils/data_generator.py        │  │  labels · gradient fills   │
│  utils/schema.py                │  └────────────────────────────┘
│  utils/charts.py                │
└───────────────┬────────────────┘
                │  Supabase REST API  (supabase-py)
┌───────────────▼──────────────────────────────────────────────────┐
│                  Data Layer — Supabase (PostgreSQL)               │
│                                                                   │
│   dim_customer ──┐                                                │
│   dim_product  ──┼──▶  fact_sales  (10,000+ rows)                │
│   dim_date     ──┤                                                │
│   dim_geography──┘     session_log  ·  system_log                │
└───────────────────────────────────────────────────────────────────┘
```

### Star Schema

```
                 ┌──────────────────┐
                 │   dim_customer   │
                 │  customer_id PK  │
                 └────────┬─────────┘
                          │
┌──────────────┐  ┌───────┴──────────────────────┐  ┌──────────────────┐
│  dim_product │  │         fact_sales            │  │  dim_geography   │
│ product_id PK├──┤  sale_id PK                   ├──┤ geography_id PK  │
└──────────────┘  │  qty · unit_price             │  └──────────────────┘
                  │  discount · tax · total_amount│
┌──────────────┐  │  payment_mode                 │
│   dim_date   │  │                               │
│  date_id PK  ├──┤  ~10,000 rows · 2-year window │
└──────────────┘  └───────────────────────────────┘
```

---

## Role-Based Access

| Feature | Cashier | Store Manager | IT Manager |
|---|:---:|:---:|:---:|
| Point of Sale terminal | ✅ | ✅ | ✅ |
| Sales Analytics Dashboard | — | ✅ | ✅ |
| Data Model Explorer | — | — | ✅ |
| Admin Hub (sessions, logs, health) | — | — | ✅ |

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| App framework | Streamlit | 1.58 |
| Database | Supabase (PostgreSQL) | Cloud |
| Database client | supabase-py | 2.30 |
| Data manipulation | Pandas | 3.0 |
| Visualisation | Plotly | 6.7 |
| Synthetic data | Faker | 40 |
| Language | Python | 3.12 |
| Hosting | Streamlit Community Cloud | — |

---

## Project Structure

```
retail-management-system/
├── app.py                    # Entry point — login, sidebar, role-based navigation
├── pages/
│   ├── 1_Transaction.py      # Point of Sale terminal
│   ├── 2_Data_Model.py       # Star schema viewer
│   ├── 3_Analytics.py        # Sales analytics dashboard
│   └── 4_Admin_Hub.py        # IT admin hub
├── utils/
│   ├── db_handler.py         # Supabase read/write — mirrors excel_handler API
│   ├── logger.py             # Session tracking + system event logging
│   ├── data_generator.py     # Synthetic data seeding (idempotent)
│   ├── charts.py             # 16 reusable Plotly chart builders
│   └── schema.py             # Dataclasses, product categories, US tax rates
├── supabase_schema.sql       # Run once in Supabase SQL Editor to create all tables
├── requirements.txt          # Streamlit Cloud pip dependencies
├── runtime.txt               # Python 3.12 for Streamlit Cloud
└── .streamlit/
    └── secrets.toml.example  # Copy to secrets.toml and fill in your values
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- A free [Supabase](https://supabase.com) account
- A free [Streamlit Community Cloud](https://share.streamlit.io) account (for deployment)

### 1. Clone the repo

```bash
git clone https://github.com/mujahid22/retail-management-system.git
cd retail-management-system
```

### 2. Set up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** → paste the full contents of `supabase_schema.sql` → click **Run**
3. Go to **Project Settings → API** and copy:
   - **Project URL** (e.g. `https://abcxyz.supabase.co`)
   - **anon / public key** (long JWT string)

### 3. Configure secrets

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with your values:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```

> `secrets.toml` is listed in `.gitignore` and will never be committed.

### 4. Install dependencies and run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

### 5. Seed the database

On first run, populate the database with 2 years of synthetic sales data:

```bash
python -c "from utils.data_generator import seed_database; seed_database()"
```

This inserts ~10,000 sales rows, 500 customers, 300+ products, and a full calendar dimension spanning the last 2 years. The seed is idempotent — safe to run again if you want to reset all data.

---

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → sign in → **New app**
3. Select your repo, branch `master`, main file path `app.py`
4. Click **Advanced settings** → add your Supabase secrets:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```

5. Click **Deploy** — Streamlit installs from `requirements.txt` and launches the app

---

## Analytics Dashboard — Chart Inventory

| Tab | Charts |
|---|---|
| **Time Analytics** | Monthly Revenue Trend (spline area), Quarterly Revenue (grouped bar), Sales by Day of Week (bar), Sales Activity Heatmap (week × day) |
| **Product Analytics** | Revenue by Category (horizontal bar), Category Share (donut), Top 15 Products by Revenue (bar), Price vs Units Sold (bubble scatter) |
| **Geo Analytics** | Revenue by US State (choropleth map), Top 20 Cities (bar), Revenue by Region (donut) |
| **Customer Analytics** | Revenue by Gender (donut), Payment Method Breakdown (donut), Revenue by Age Group (bar), Customer Lifetime Value Distribution (histogram), New vs Returning Customers (stacked bar) |

---

## Data Characteristics

| Dimension | Detail |
|---|---|
| Date range | Rolling 2-year window ending today |
| Customers | 500 seeded · new customers added on each POS transaction |
| Products | 300+ SKUs across 15 categories and 60 sub-categories |
| Geographies | 50 US cities across 4 regions (Northeast, South, Midwest, West) |
| Seasonality | Holiday boost ×3.5 (Nov–Dec) · Spring ×1.5 · Summer ×1.2 |
| Tax rates | Real US state sales tax rates for all 50 states |
| Payment modes | Cash · Credit Card · Debit Card · Digital Wallet · Store Credit |
