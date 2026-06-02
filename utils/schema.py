"""Star schema table definitions."""
from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


SHEET_NAMES = {
    "fact_sales": "fact_sales",
    "dim_customer": "dim_customer",
    "dim_product": "dim_product",
    "dim_date": "dim_date",
    "dim_geography": "dim_geography",
}

CATEGORIES = {
    "Action Figures": ["Superheroes", "Villains", "Military", "Movie Characters"],
    "Building Blocks": ["LEGO Compatible", "Magnetic", "Wooden", "Foam"],
    "Dolls": ["Fashion Dolls", "Baby Dolls", "Collectible", "Accessory Sets"],
    "Board Games": ["Strategy", "Family", "Party", "Educational"],
    "Puzzles": ["Jigsaw", "3D", "Brain Teasers", "Floor Puzzles"],
    "Remote Control": ["Cars", "Drones", "Boats", "Planes"],
    "Outdoor Toys": ["Water Toys", "Sand Toys", "Ride-Ons", "Sports"],
    "Arts & Crafts": ["Painting", "Clay", "Jewelry Making", "Drawing"],
    "Educational": ["Science Kits", "Math Games", "Coding Toys", "Flash Cards"],
    "Stuffed Animals": ["Bears", "Dogs", "Exotic Animals", "Fantasy"],
    "Electronic Toys": ["Tablets", "Gaming", "Robots", "Interactive"],
    "Musical Toys": ["Instruments", "Karaoke", "Singing", "Rhythm"],
    "Sports Toys": ["Basketball", "Soccer", "Batting", "Golf"],
    "Science Kits": ["Chemistry", "Biology", "Astronomy", "Physics"],
    "Card Games": ["Memory", "War", "UNO Style", "Collectible"],
}

AGE_GROUPS = ["0-2", "3-5", "6-8", "9-12", "13-17", "18+"]
GENDERS = ["Male", "Female", "Non-Binary", "Prefer not to say"]
PAYMENT_MODES = ["Cash", "Credit Card", "Debit Card", "Digital Wallet", "Store Credit"]
US_REGIONS = {
    "Northeast": ["CT", "ME", "MA", "NH", "NJ", "NY", "PA", "RI", "VT"],
    "South": ["AL", "AR", "DE", "FL", "GA", "KY", "LA", "MD", "MS", "NC", "OK", "SC", "TN", "TX", "VA", "WV"],
    "Midwest": ["IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI"],
    "West": ["AK", "AZ", "CA", "CO", "HI", "ID", "MT", "NV", "NM", "OR", "UT", "WA", "WY"],
}

STATE_ABBREVS = [s for states in US_REGIONS.values() for s in states]

TAX_BY_STATE = {
    "AL": 4.0, "AK": 0.0, "AZ": 5.6, "AR": 6.5, "CA": 7.25, "CO": 2.9,
    "CT": 6.35, "DE": 0.0, "FL": 6.0, "GA": 4.0, "HI": 4.0, "ID": 6.0,
    "IL": 6.25, "IN": 7.0, "IA": 6.0, "KS": 6.5, "KY": 6.0, "LA": 4.45,
    "ME": 5.5, "MD": 6.0, "MA": 6.25, "MI": 6.0, "MN": 6.875, "MS": 7.0,
    "MO": 4.225, "MT": 0.0, "NE": 5.5, "NV": 6.85, "NH": 0.0, "NJ": 6.625,
    "NM": 5.125, "NY": 4.0, "NC": 4.75, "ND": 5.0, "OH": 5.75, "OK": 4.5,
    "OR": 0.0, "PA": 6.0, "RI": 7.0, "SC": 6.0, "SD": 4.5, "TN": 7.0,
    "TX": 6.25, "UT": 4.85, "VT": 6.0, "VA": 5.3, "WA": 6.5, "WV": 6.0,
    "WI": 5.0, "WY": 4.0,
}


@dataclass
class DimCustomer:
    customer_id: str
    customer_name: str
    email: str
    phone: str
    age_group: str
    gender: str


@dataclass
class DimProduct:
    product_id: str
    product_name: str
    category: str
    sub_category: str
    brand: str
    sku: str
    unit_cost: float
    unit_price: float


@dataclass
class DimDate:
    date_id: int
    full_date: date
    year: int
    quarter: int
    month: int
    month_name: str
    week_of_year: int
    day_of_week: int
    day_name: str
    is_weekend: bool


@dataclass
class DimGeography:
    geography_id: str
    city: str
    state: str
    region: str
    zip_code: str


@dataclass
class FactSales:
    sale_id: str
    transaction_id: str
    customer_id: str
    product_id: str
    date_id: int
    geography_id: str
    qty: int
    unit_cost: float
    unit_price: float
    discount_pct: float
    discount_amount: float
    subtotal: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    payment_mode: str
