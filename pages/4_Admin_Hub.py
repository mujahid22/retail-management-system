"""Admin Hub — IT Manager only. Session tracking + system logs + health."""
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.db_handler import get_client, load_all
from utils.logger import load_session_log, load_system_log

# ── Guard ─────────────────────────────────────────────────────────────────────
if st.session_state.get("role") != "IT Manager":
    st.error("Access denied. This section is restricted to IT Managers.")
    st.stop()

import plotly.graph_objects as go

PALETTE      = ["#FF6B35", "#4361EE", "#2EC4B6", "#7209B7", "#FB8500", "#023E8A"]
ROLE_COLORS  = {"Cashier": "#4361EE", "Store Manager": "#FF6B35", "IT Manager": "#2EC4B6"}
LOG_COLORS   = {"INFO": "#4361EE", "WARNING": "#FB8500", "ERROR": "#DC2626"}
FONT_COLOR   = "#374151"
TITLE_COLOR  = "#0A0A0A"
GRID_COLOR   = "#E5E7EB"

BASE_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="#F8FAFB",
    font=dict(color=FONT_COLOR, family="Segoe UI, Inter, Arial, sans-serif", size=12),
    title_font_color=TITLE_COLOR,
    title_font_size=15,
    title_font_family="Segoe UI, Inter, Arial, sans-serif",
    title_x=0.01,
    margin=dict(l=20, r=20, t=54, b=32),
    legend=dict(
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor=GRID_COLOR,
        borderwidth=1,
        font=dict(size=11, color=FONT_COLOR),
    ),
    hoverlabel=dict(bgcolor="white", font_size=12, font_color=TITLE_COLOR),
)


def _apply(fig: go.Figure) -> go.Figure:
    fig.update_layout(**BASE_LAYOUT)
    fig.update_xaxes(gridcolor=GRID_COLOR, zeroline=False, linecolor=GRID_COLOR,
                     showline=True, tickfont=dict(color=FONT_COLOR, size=11))
    fig.update_yaxes(gridcolor=GRID_COLOR, zeroline=False, linecolor=GRID_COLOR,
                     showline=False, tickfont=dict(color=FONT_COLOR, size=11))
    return fig

st.markdown('<div class="section-header">🔧 Admin Hub</div>', unsafe_allow_html=True)
st.caption("System observability for IT Managers — session tracking, event logs, and data health.")

# ── Refresh control ───────────────────────────────────────────────────────────
top_l, top_r = st.columns([5, 1])
with top_r:
    auto_refresh = st.toggle("Auto-refresh (30s)", value=False)
if auto_refresh:
    import time
    time.sleep(30)
    st.rerun()

st.divider()

tab_session, tab_syslog, tab_health = st.tabs([
    "👥 Session & Usage Tracking",
    "📋 System Logs",
    "🩺 System Health",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SESSION & USAGE TRACKING
# ═══════════════════════════════════════════════════════════════════════════════
with tab_session:
    df_sess = load_session_log()

    if df_sess.empty:
        st.info("No session data yet. Sessions are recorded on login and sign-out.")
    else:
        active    = df_sess[df_sess["logout_time"].isna()]
        completed = df_sess[df_sess["logout_time"].notna()]
        avg_dur   = completed["duration_mins"].mean() if not completed.empty else 0
        most_role = df_sess["role"].value_counts().idxmax() if not df_sess.empty else "—"

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Sessions",       len(df_sess))
        k2.metric("Active Now",           len(active),
                  delta=f"{len(active)} live" if len(active) else None)
        k3.metric("Avg Session Duration", f"{avg_dur:.1f} min" if avg_dur else "—")
        k4.metric("Most Active Role",     most_role)

        st.divider()

        st.markdown("#### Session Log")
        search = st.text_input("Search sessions", placeholder="Filter by role, session ID…", key="sess_search")
        display = df_sess.copy().sort_values("login_time", ascending=False)
        if search:
            mask = display.apply(lambda c: c.astype(str).str.contains(search, case=False, na=False)).any(axis=1)
            display = display[mask]

        disp = display.copy()
        disp["login_time"]    = disp["login_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        disp["logout_time"]   = disp["logout_time"].dt.strftime("%Y-%m-%d %H:%M:%S").fillna("● Active")
        disp["duration_mins"] = disp["duration_mins"].apply(lambda x: f"{x:.1f} min" if pd.notna(x) else "—")
        disp = disp.rename(columns={
            "session_id": "Session ID", "role": "Role",
            "login_time": "Login Time", "logout_time": "Logout Time",
            "duration_mins": "Duration", "logout_type": "Logout Type",
        })

        def highlight_active(row):
            if row["Logout Time"] == "● Active":
                return ["background-color: #1A2E1A; color: #4CAF50"] * len(row)
            return [""] * len(row)

        st.dataframe(
            disp.style.apply(highlight_active, axis=1),
            use_container_width=True, hide_index=True, height=300,
        )

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            role_counts = df_sess["role"].value_counts().reset_index()
            role_counts.columns = ["Role", "Sessions"]
            fig = px.bar(
                role_counts, x="Role", y="Sessions",
                title="Sessions by Role", color="Role",
                color_discrete_map=ROLE_COLORS,
                text="Sessions",
            )
            fig.update_traces(textposition="outside", textfont=dict(color=FONT_COLOR, size=11))
            st.plotly_chart(_apply(fig), use_container_width=True)

        with c2:
            role_pie = px.pie(
                role_counts, names="Role", values="Sessions",
                title="Role Distribution", hole=0.52,
                color_discrete_map=ROLE_COLORS,
            )
            role_pie.update_traces(
                textposition="inside", textinfo="percent+label",
                textfont_size=12,
                marker=dict(line=dict(color="white", width=2)),
                hovertemplate="<b>%{label}</b><br>%{value} sessions — %{percent}<extra></extra>",
            )
            st.plotly_chart(_apply(role_pie), use_container_width=True)

        if not df_sess.empty:
            df_sess["login_date"] = df_sess["login_time"].dt.date
            by_date = df_sess.groupby(["login_date", "role"]).size().reset_index(name="Sessions")
            fig_time = px.bar(
                by_date, x="login_date", y="Sessions", color="role",
                title="Sessions Over Time", barmode="stack",
                labels={"login_date": "Date", "role": "Role"},
                color_discrete_map=ROLE_COLORS,
            )
            fig_time.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(_apply(fig_time), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SYSTEM LOGS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_syslog:
    df_log = load_system_log()

    if df_log.empty:
        st.info("No system events logged yet. Events are recorded as the app is used.")
    else:
        info_n  = (df_log["level"] == "INFO").sum()
        warn_n  = (df_log["level"] == "WARNING").sum()
        error_n = (df_log["level"] == "ERROR").sum()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Events", len(df_log))
        k2.metric("INFO",         info_n)
        k3.metric("WARNING",      warn_n,  delta=f"{warn_n} warnings"  if warn_n  else None)
        k4.metric("ERROR",        error_n, delta=f"{error_n} errors"   if error_n else None,
                  delta_color="inverse" if error_n else "normal")

        st.divider()

        fc1, fc2, fc3, fc4 = st.columns([1.5, 1.5, 1.5, 2])
        with fc1:
            lvl_filter = st.multiselect("Level",  ["INFO", "WARNING", "ERROR"], default=[], placeholder="All", key="log_lvl")
        with fc2:
            src_filter = st.multiselect("Source", sorted(df_log["source"].unique()), default=[], placeholder="All", key="log_src")
        with fc3:
            evt_filter = st.multiselect("Event",  sorted(df_log["event"].unique()),  default=[], placeholder="All", key="log_evt")
        with fc4:
            log_search = st.text_input("Search message", placeholder="keyword…", key="log_search")

        filtered = df_log.copy().sort_values("timestamp", ascending=False)
        if lvl_filter: filtered = filtered[filtered["level"].isin(lvl_filter)]
        if src_filter: filtered = filtered[filtered["source"].isin(src_filter)]
        if evt_filter: filtered = filtered[filtered["event"].isin(evt_filter)]
        if log_search: filtered = filtered[filtered["message"].str.contains(log_search, case=False, na=False)]

        st.markdown("#### Event Log")

        def colour_log_row(row):
            if row["Level"] == "ERROR":
                return ["background-color: #FEF2F2; color: #DC2626; font-weight:600"] * len(row)
            if row["Level"] == "WARNING":
                return ["background-color: #FFFBEB; color: #D97706; font-weight:600"] * len(row)
            return [""] * len(row)

        disp_log = filtered.copy()
        disp_log["timestamp"] = disp_log["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        disp_log = disp_log.rename(columns={
            "log_id": "ID", "timestamp": "Timestamp", "level": "Level",
            "source": "Source", "event": "Event", "message": "Message",
        })
        st.dataframe(
            disp_log.style.apply(colour_log_row, axis=1),
            use_container_width=True, hide_index=True, height=350,
        )
        st.caption(f"Showing {len(filtered):,} of {len(df_log):,} events")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            lvl_counts = df_log["level"].value_counts().reset_index()
            lvl_counts.columns = ["Level", "Count"]
            fig_lvl = px.bar(
                lvl_counts, x="Count", y="Level", orientation="h",
                title="Events by Severity Level",
                color="Level", color_discrete_map=LOG_COLORS,
                text="Count",
            )
            fig_lvl.update_traces(textposition="outside", textfont=dict(color=FONT_COLOR, size=11))
            st.plotly_chart(_apply(fig_lvl), use_container_width=True)

        with c2:
            src_counts = df_log["source"].value_counts().reset_index()
            src_counts.columns = ["Source", "Count"]
            fig_src = px.pie(
                src_counts, names="Source", values="Count",
                title="Events by Source Module", hole=0.5,
                color_discrete_sequence=PALETTE,
            )
            fig_src.update_traces(
                textposition="inside", textinfo="percent+label",
                textfont_size=12,
                marker=dict(line=dict(color="white", width=2)),
                hovertemplate="<b>%{label}</b><br>%{value} events — %{percent}<extra></extra>",
            )
            st.plotly_chart(_apply(fig_src), use_container_width=True)

        if df_log["timestamp"].notna().any():
            df_log["hour"] = df_log["timestamp"].dt.floor("h")
            timeline = df_log.groupby(["hour", "level"]).size().reset_index(name="count")
            fig_tl = px.scatter(
                timeline, x="hour", y="count", color="level",
                size="count", title="Event Timeline — Hourly Activity",
                labels={"hour": "Time", "count": "Events", "level": "Level"},
                color_discrete_map=LOG_COLORS,
                size_max=28, opacity=0.85,
            )
            st.plotly_chart(_apply(fig_tl), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SYSTEM HEALTH
# ═══════════════════════════════════════════════════════════════════════════════
with tab_health:
    st.markdown("#### Supabase Table Health")

    try:
        sheets = load_all()
        fact   = sheets.get("fact_sales", pd.DataFrame())

        h1, h2, h3 = st.columns(3)

        # Star schema stats
        h1.metric("fact_sales rows",    f"{len(sheets.get('fact_sales',    [])):,}")
        h1.metric("dim_product rows",   f"{len(sheets.get('dim_product',   [])):,}")
        h2.metric("dim_customer rows",  f"{len(sheets.get('dim_customer',  [])):,}")
        h2.metric("dim_geography rows", f"{len(sheets.get('dim_geography', [])):,}")
        h3.metric("dim_date rows",      f"{len(sheets.get('dim_date',      [])):,}")

        if not fact.empty:
            h3.metric("Cumulative Revenue", f"${fact['total_amount'].sum():,.2f}")

        st.divider()
        st.markdown("#### All Table Row Counts")
        sheet_df = pd.DataFrame([
            {"Table": name, "Rows": len(df), "Columns": len(df.columns)}
            for name, df in sheets.items()
        ])
        # Add log tables
        sess_count = len(load_session_log())
        sys_count  = len(load_system_log())
        sheet_df = pd.concat([
            sheet_df,
            pd.DataFrame([
                {"Table": "session_log", "Rows": sess_count, "Columns": 6},
                {"Table": "system_log",  "Rows": sys_count,  "Columns": 6},
            ])
        ], ignore_index=True)
        st.dataframe(sheet_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Could not read Supabase tables: {e}")

    st.divider()
    st.markdown("#### Recent Errors")
    df_err = load_system_log()
    errors = df_err[df_err["level"] == "ERROR"].sort_values("timestamp", ascending=False).head(5)
    if errors.empty:
        st.success("No errors logged. System is healthy.")
    else:
        err_disp = errors[["timestamp", "source", "event", "message"]].copy()
        err_disp["timestamp"] = err_disp["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(err_disp, use_container_width=True, hide_index=True)
