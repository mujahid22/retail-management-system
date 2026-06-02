"""Toys Retail Store — Streamlit main entry point."""
import streamlit as st
from utils.logger import log_login, log_logout

st.set_page_config(
    page_title="ToyWorld Retail",
    page_icon="🧸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { background: #12172B; }
    [data-testid="stSidebar"] * { color: #FAFAFA !important; }

    /* Brand header above nav links */
    section[data-testid="stSidebar"] > div:first-child { display: flex; flex-direction: column; }
    [data-testid="stSidebarNav"] { order: 2; }
    [data-testid="stSidebarUserContent"] {
        order: 1;
        border-bottom: 1px solid #2A3050;
        padding-bottom: 0.6rem;
        margin-bottom: 0.25rem;
    }

    /* KPI cards */
    .kpi-card {
        background: white;
        border-radius: 10px;
        padding: 16px 18px 14px;
        border-top: 3px solid #FF6B35;
        margin-bottom: 8px;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
    }
    .kpi-label { font-size: 10px; color: #6B7280; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 28px; font-weight: 800; color: #0A0A0A; line-height: 1.15; margin: 6px 0 4px; }
    .kpi-delta { font-size: 11px; font-weight: 600; min-height: 16px; }

    .section-header { font-size: 22px; font-weight: 700; color: #FF6B35; margin-bottom: 4px; }


    /* ── Sidebar buttons — override Streamlit's white default ── */
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: 1px solid #3A4060 !important;
        color: #AABBCC !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        padding: 6px 14px !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #2A3050 !important;
        border-color: #FF6B35 !important;
        color: #FF6B35 !important;
    }

    /* ── Login page ── */
    .role-badge {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        font-size: 12px; font-weight: 600; letter-spacing: 0.5px; margin-top: 6px;
    }
    .badge-cashier  { background: #1E3A5F; color: #5BB8FF; }
    .badge-manager  { background: #3A1F0A; color: #FF6B35; }
    .badge-it       { background: #1A2E1A; color: #4CAF50; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state defaults ────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None

# ── Login page ────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    # Hide sidebar (stale nav) and Streamlit's top toolbar on the login screen
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"]  { display: none !important; }
        [data-testid="stHeader"]   { display: none !important; }
        [data-testid="stToolbar"]  { display: none !important; }
        #MainMenu                  { display: none !important; }
        footer                     { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.write("")  # top breathing room
    _, center, _ = st.columns([1, 1.6, 1])
    with center:
        with st.container(border=True):
            st.markdown("## 🧸 ToyWorld Retail")
            st.markdown("*End-to-End Retail Management System*")
            st.divider()

            st.markdown("#### Welcome — Select Your Role")
            st.caption("Your role determines which sections of the app you can access.")

            role_options = {
                "🛒  Cashier":       "Cashier",
                "🏪  Store Manager": "Store Manager",
                "💻  IT Manager":    "IT Manager",
            }
            selected_label = st.selectbox(
                "Role",
                options=list(role_options.keys()),
                label_visibility="collapsed",
            )
            selected_role = role_options[selected_label]

            # Role description badge
            ROLE_BADGES = {
                "Cashier":       '<span class="role-badge badge-cashier">🛒 Point of Sale terminal only</span>',
                "Store Manager": '<span class="role-badge badge-manager">🏪 Point of Sale · Sales Dashboard</span>',
                "IT Manager":    '<span class="role-badge badge-it">💻 Point of Sale · Data Model · Analytics · Admin Hub</span>',
            }
            st.markdown(ROLE_BADGES[selected_role], unsafe_allow_html=True)

            st.write("")
            if st.button("Enter Store →", type="primary", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.role = selected_role
                st.session_state.session_id = log_login(selected_role)
                st.rerun()

    st.stop()

# ── Build page list based on role ─────────────────────────────────────────────
_pos = [st.Page("pages/1_Transaction.py", title="Point of Sale",    icon="🛒")]
_dm  = [st.Page("pages/2_Data_Model.py",  title="Data Model",       icon="🗄️")]
_sd  = [st.Page("pages/3_Analytics.py",   title="Sales Dashboard",  icon="📊")]
_ah  = [st.Page("pages/4_Admin_Hub.py",   title="Admin Hub",        icon="🔧")]

role = st.session_state.role
if role == "Cashier":
    pages = {"Sales Terminal": _pos}
elif role == "Store Manager":
    pages = {"Sales Terminal": _pos, "Analytics Hub": _sd}
else:  # IT Manager
    pages = {"Sales Terminal": _pos, "Analytics Hub": _dm + _sd, "Admin": _ah}

# ── Sidebar: brand + role badge + logout ──────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧸 ToyWorld Retail")
    st.markdown("*End-to-End Retail Management*")
    role_icon  = {"Cashier": "🛒", "Store Manager": "🏪", "IT Manager": "💻"}.get(role, "👤")
    role_color = {"Cashier": "#5BB8FF", "Store Manager": "#FF6B35", "IT Manager": "#4CAF50"}.get(role, "#FAFAFA")
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:6px;'
        f'background:#12233A;border:1px solid {role_color}33;border-radius:20px;'
        f'padding:3px 10px 3px 8px;margin:4px 0 8px;">'
        f'<span style="font-size:13px;">{role_icon}</span>'
        f'<span style="font-size:12px;font-weight:600;color:{role_color};">'
        f'{st.session_state.role}</span></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    # Sign-out sits below the nav links (order:2 pushes nav down, so this appears last)
    st.write("")
    if st.button("Sign Out", use_container_width=True):
        if st.session_state.session_id:
            log_logout(st.session_state.session_id, "Sign Out")
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.session_id = None
        st.rerun()

pg = st.navigation(pages)
pg.run()
