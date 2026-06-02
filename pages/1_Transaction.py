"""Section 1 — Point of Sale Transaction Interface (single-screen layout)."""
import uuid
from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.db_handler import (
    append_sale_rows, ensure_date_exists, load_sheet, next_sale_id,
    upsert_customer, upsert_geography,
)
from utils.logger import log_event
from utils.schema import AGE_GROUPS, CATEGORIES, GENDERS, PAYMENT_MODES, TAX_BY_STATE

# ── Compact POS CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Tighten vertical rhythm inside the POS page */
div[data-testid="stVerticalBlock"] > div { gap: 0.25rem !important; }
div[data-testid="column"] > div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
.pos-info-strip {
    display: flex; gap: 6px; flex-wrap: wrap; margin: 2px 0 6px;
}
.pos-info-chip {
    background: #1A1F2E; border: 1px solid #2A3050;
    border-radius: 6px; padding: 3px 10px;
    font-size: 12px; color: #AABBCC;
}
.pos-info-chip b { color: #FAFAFA; }
.pos-bill-row {
    display: flex; gap: 6px; margin-top: 6px;
}
.pos-bill-cell {
    flex: 1; background: #1A1F2E; border-radius: 8px;
    padding: 6px 10px; text-align: center;
    border-left: 3px solid #2A3050;
}
.pos-bill-cell.accent { border-left-color: #FF6B35; }
.pos-bill-label { font-size: 10px; color: #8899AA; text-transform: uppercase; }
.pos-bill-value { font-size: 15px; font-weight: 700; color: #FAFAFA; }
.pos-section-title {
    font-size: 13px; font-weight: 600; color: #FF6B35;
    text-transform: uppercase; letter-spacing: 0.8px;
    margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
if "cart" not in st.session_state:
    st.session_state.cart = []
if "transaction_id" not in st.session_state:
    st.session_state.transaction_id = str(uuid.uuid4())[:16].upper()
if "receipt_data" not in st.session_state:
    st.session_state.receipt_data = None


def clear_cart():
    st.session_state.cart = []
    st.session_state.transaction_id = str(uuid.uuid4())[:16].upper()
    st.session_state.receipt_data = None


# ── Receipt modal ─────────────────────────────────────────────────────────────
@st.dialog("🧾 Transaction Receipt", width="large")
def show_receipt(r: dict):
    st.markdown(f"**Transaction ID:** `{r['transaction_id']}` &nbsp;|&nbsp; "
                f"**{r['date']}** at **{r['time']}**")
    st.markdown(f"**Customer:** {r['customer_name']} &nbsp;|&nbsp; "
                f"**Payment:** {r['payment_mode']}"
                + (f"  `{r['payment_ref']}`" if r['payment_ref'] else ""))
    st.divider()
    items_df = pd.DataFrame(r["items"])[
        ["product_name", "qty", "unit_price", "discount_pct", "discount_amount", "subtotal"]
    ].copy()
    items_df.columns = ["Product", "Qty", "Unit Price", "Disc%", "Disc Amt", "Subtotal"]
    st.dataframe(items_df, use_container_width=True, hide_index=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross",    f"${r['subtotal']:,.2f}")
    c2.metric("Discount", f"-${r['discount']:,.2f}")
    c3.metric(f"Tax ({r['state']} {r['tax_rate']}%)", f"${r['tax']:,.2f}")
    c4.metric("Grand Total", f"${r['grand_total']:,.2f}", delta="Paid")
    st.divider()
    if st.button("🆕 Start New Transaction", type="primary", use_container_width=True):
        st.session_state.receipt_data = None
        st.rerun()


# Trigger the dialog if a completed receipt is waiting
if st.session_state.receipt_data:
    show_receipt(st.session_state.receipt_data)

# ── Load product catalog ──────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_products() -> pd.DataFrame:
    return load_sheet("dim_product")

products_df = get_products()

# ── Compact header bar ────────────────────────────────────────────────────────
h1, h2 = st.columns([3, 1])
h1.markdown('<div class="section-header">🛒 Point of Sale Terminal</div>',
            unsafe_allow_html=True)
h2.caption(f"**Tx:** `{st.session_state.transaction_id}`  \n"
           f"{date.today().strftime('%d %b %Y')} · {datetime.now().strftime('%I:%M %p')}")

st.divider()

# ── Three-column single-screen layout ────────────────────────────────────────
col_prod, col_cart, col_cust = st.columns([3, 4, 3], gap="medium")

# ══════════════════════════════════════════════════════
# COLUMN 1 — PRODUCT SCANNER
# ══════════════════════════════════════════════════════
with col_prod:
    st.markdown('<div class="pos-section-title">📦 Product Scanner</div>',
                unsafe_allow_html=True)

    category = st.selectbox(
        "Category", sorted(CATEGORIES.keys()),
        index=None, placeholder="Select Product Category",
        key="sel_cat", label_visibility="collapsed",
    )

    sub_category = st.selectbox(
        "Sub-Category", CATEGORIES.get(category, []),
        index=None, placeholder="Select Sub-Category",
        key=f"sel_sub_{category}",        # resets when category changes
        label_visibility="collapsed",
        disabled=(category is None),
    )

    _prod_opts = []
    if category and sub_category:
        _prod_opts = products_df[
            (products_df["category"] == category) &
            (products_df["sub_category"] == sub_category)
        ]["product_name"].tolist()

    selected_name = st.selectbox(
        "Product", _prod_opts,
        index=None, placeholder="Select Product",
        key=f"sel_prod_{category}_{sub_category}",  # resets when either parent changes
        label_visibility="collapsed",
        disabled=(not _prod_opts),
    )

    _product_ready = selected_name is not None
    if _product_ready:
        prod = products_df[products_df["product_name"] == selected_name].iloc[0]

    # Info strip — always visible; grayed out until a product is chosen
    _sku   = prod["sku"]             if _product_ready else "—"
    _brand = prod["brand"]           if _product_ready else "—"
    _cost  = f'${float(prod["unit_cost"]):.2f}'  if _product_ready else "—"
    _price = f'${float(prod["unit_price"]):.2f}' if _product_ready else "—"
    _chip_style = "" if _product_ready else "opacity:0.35;"
    st.markdown(
        f'<div class="pos-info-strip" style="{_chip_style}">'
        f'<span class="pos-info-chip"><b>SKU</b> {_sku}</span>'
        f'<span class="pos-info-chip"><b>Brand</b> {_brand}</span>'
        f'<span class="pos-info-chip"><b>Cost</b> {_cost}</span>'
        f'<span class="pos-info-chip"><b>Price</b> {_price}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    q_col, d_col = st.columns([1, 2])
    with q_col:
        qty = st.number_input("Qty", min_value=1, max_value=99, value=1,
                              key="qty_input", disabled=not _product_ready)
    with d_col:
        discount_pct = st.slider("Discount %", 0, 50, 0, step=5,
                                 key="disc_input", disabled=not _product_ready)

    if _product_ready:
        unit_price = float(prod["unit_price"])
        unit_cost  = float(prod["unit_cost"])
        subtotal   = unit_price * qty
        disc_amt   = subtotal * discount_pct / 100
        taxable    = subtotal - disc_amt
        st.caption(
            f"Subtotal **${subtotal:.2f}** · Disc **-${disc_amt:.2f}** · "
            f"Taxable **${taxable:.2f}**"
        )
    else:
        st.caption("Subtotal **—** · Disc **—** · Taxable **—**")

    if st.button("➕ Add to Cart", type="primary", use_container_width=True,
                 disabled=not _product_ready):
        st.session_state.cart.append({
            "product_id":      prod["product_id"],
            "product_name":    selected_name,
            "category":        category,
            "sub_category":    sub_category,
            "sku":             prod["sku"],
            "brand":           prod["brand"],
            "unit_cost":       unit_cost,
            "unit_price":      unit_price,
            "qty":             qty,
            "discount_pct":    discount_pct,
            "discount_amount": round(disc_amt, 2),
            "subtotal":        round(subtotal, 2),
            "taxable":         round(taxable, 2),
        })
        st.toast(f"Added {selected_name} ×{qty}", icon="✅")


# ══════════════════════════════════════════════════════
# COLUMN 2 — CART + BILLING
# ══════════════════════════════════════════════════════
with col_cart:
    cart_title, cart_btn = st.columns([3, 1])
    cart_title.markdown(
        f'<div class="pos-section-title">🧾 Cart'
        f'{"  (" + str(len(st.session_state.cart)) + " items)" if st.session_state.cart else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.cart:
        with cart_btn:
            if st.button("🗑️ Clear", use_container_width=True):
                clear_cart()
                st.rerun()

    if not st.session_state.cart:
        st.info("Cart is empty — scan a product and click Add to Cart.")
    else:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(
            cart_df[["product_name", "qty", "unit_price", "discount_pct", "subtotal"]]
            .rename(columns={
                "product_name": "Product", "qty": "Qty",
                "unit_price": "Price", "discount_pct": "Disc%", "subtotal": "Sub",
            }),
            use_container_width=True, hide_index=True, height=175,
        )

        # Billing panel (uses state tax from col 3 — derive from key if available)
        _state_key = st.session_state.get("_cust_state_live", "TX")
        tax_rate     = TAX_BY_STATE.get(_state_key, 5.0)
        tot_sub      = cart_df["subtotal"].sum()
        tot_disc     = cart_df["discount_amount"].sum()
        tot_taxable  = cart_df["taxable"].sum()
        tax_amt      = round(tot_taxable * tax_rate / 100, 2)
        grand_total  = round(tot_taxable + tax_amt, 2)

        st.markdown(
            f'<div class="pos-bill-row">'
            f'<div class="pos-bill-cell"><div class="pos-bill-label">Gross</div>'
            f'<div class="pos-bill-value">${tot_sub:,.2f}</div></div>'
            f'<div class="pos-bill-cell"><div class="pos-bill-label">Discount</div>'
            f'<div class="pos-bill-value">-${tot_disc:,.2f}</div></div>'
            f'<div class="pos-bill-cell"><div class="pos-bill-label">Taxable</div>'
            f'<div class="pos-bill-value">${tot_taxable:,.2f}</div></div>'
            f'<div class="pos-bill-cell"><div class="pos-bill-label">Tax ({_state_key} {tax_rate}%)</div>'
            f'<div class="pos-bill-value">${tax_amt:,.2f}</div></div>'
            f'<div class="pos-bill-cell accent"><div class="pos-bill-label">Grand Total</div>'
            f'<div class="pos-bill-value" style="color:#FF6B35">${grand_total:,.2f}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════
# COLUMN 3 — CUSTOMER + PAYMENT + SUBMIT
# ══════════════════════════════════════════════════════
with col_cust:
    st.markdown('<div class="pos-section-title">👤 Customer</div>',
                unsafe_allow_html=True)

    n_col, e_col = st.columns(2)
    with n_col:
        cust_name  = st.text_input("Name *",  placeholder="Jane Smith",       key="c_name")
    with e_col:
        cust_email = st.text_input("Email *", placeholder="jane@example.com", key="c_email")

    ph_col, ag_col = st.columns(2)
    with ph_col:
        cust_phone = st.text_input("Phone",  placeholder="(555) 000-0000",    key="c_phone")
    with ag_col:
        cust_age   = st.selectbox("Age Group", AGE_GROUPS,                    key="c_age")

    gn_col, ci_col = st.columns(2)
    with gn_col:
        cust_gender = st.selectbox("Gender", GENDERS,                         key="c_gender")
    with ci_col:
        cust_city  = st.text_input("City *", placeholder="Dallas",            key="c_city")

    st_col, zp_col = st.columns(2)
    with st_col:
        _state_list   = sorted(TAX_BY_STATE.keys())
        cust_state    = st.selectbox("State *", _state_list,
                                     index=_state_list.index("TX"),           key="c_state")
        # Expose to cart column for live tax
        st.session_state["_cust_state_live"] = cust_state
    with zp_col:
        cust_zip   = st.text_input("ZIP",  placeholder="75201",               key="c_zip")

    st.markdown('<div class="pos-section-title" style="margin-top:6px">💳 Payment</div>',
                unsafe_allow_html=True)

    pm_col, ref_col = st.columns(2)
    with pm_col:
        payment_mode = st.selectbox("Mode *", PAYMENT_MODES, key="c_pmode")
    with ref_col:
        payment_ref  = st.text_input("Ref #", placeholder="AUTH-XXXX",        key="c_pref")

    st.write("")

    # Complete Sale
    if st.button("✅ Complete Sale", type="primary", use_container_width=True,
                 disabled=not bool(st.session_state.cart)):

        errors = []
        if not cust_name.strip():  errors.append("Customer name is required.")
        if not cust_email.strip(): errors.append("Email is required.")
        if not cust_city.strip():  errors.append("City is required.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            with st.spinner("Processing…"):
                customer_id  = upsert_customer({
                    "customer_name": cust_name, "email": cust_email,
                    "phone": cust_phone, "age_group": cust_age, "gender": cust_gender,
                })
                geography_id = upsert_geography({
                    "city": cust_city, "state": cust_state, "zip_code": cust_zip,
                })
                tx_date  = date.today()
                date_id  = int(tx_date.strftime("%Y%m%d"))
                ensure_date_exists(tx_date)

                # Re-derive totals here (col_cart values aren't in scope)
                cart_df2      = pd.DataFrame(st.session_state.cart)
                tot_sub2      = cart_df2["subtotal"].sum()
                tot_disc2     = cart_df2["discount_amount"].sum()
                tot_taxable2  = cart_df2["taxable"].sum()
                tr            = TAX_BY_STATE.get(cust_state, 5.0)
                tax_amt2      = round(tot_taxable2 * tr / 100, 2)
                grand2        = round(tot_taxable2 + tax_amt2, 2)

                sale_rows    = []
                id_num       = int(next_sale_id().replace("S", ""))
                tx_id        = st.session_state.transaction_id

                for item in st.session_state.cart:
                    item_tax   = round(item["taxable"] * tr / 100, 2)
                    sale_rows.append({
                        "sale_id":         f"S{id_num:08d}",
                        "transaction_id":  tx_id,
                        "customer_id":     customer_id,
                        "product_id":      item["product_id"],
                        "date_id":         date_id,
                        "geography_id":    geography_id,
                        "qty":             item["qty"],
                        "unit_cost":       item["unit_cost"],
                        "unit_price":      item["unit_price"],
                        "discount_pct":    item["discount_pct"],
                        "discount_amount": item["discount_amount"],
                        "subtotal":        item["subtotal"],
                        "tax_rate":        tr,
                        "tax_amount":      item_tax,
                        "total_amount":    round(item["taxable"] + item_tax, 2),
                        "payment_mode":    payment_mode,
                    })
                    id_num += 1

                append_sale_rows(sale_rows)
                log_event("INFO", "Transaction", "SALE_COMPLETED",
                          f"Tx {tx_id} | {len(sale_rows)} item(s) | ${grand2:.2f} | {payment_mode}")
                st.cache_data.clear()

                st.session_state.receipt_data = {
                    "transaction_id": tx_id,
                    "customer_name":  cust_name,
                    "items":          list(st.session_state.cart),
                    "subtotal":       tot_sub2,
                    "discount":       tot_disc2,
                    "tax":            tax_amt2,
                    "grand_total":    grand2,
                    "payment_mode":   payment_mode,
                    "payment_ref":    payment_ref,
                    "date":           tx_date.strftime("%B %d, %Y"),
                    "time":           datetime.now().strftime("%I:%M %p"),
                    "state":          cust_state,
                    "tax_rate":       tr,
                }
                clear_cart()
                st.rerun()
