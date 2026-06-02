"""Supabase-backed session and system event logger — replaces CSV files."""
import uuid
from datetime import datetime, timezone

import pandas as pd

from utils.db_handler import get_client


# ── Session tracking ──────────────────────────────────────────────────────────

def log_login(role: str) -> str:
    """Record a login event. Returns the new session_id."""
    session_id = str(uuid.uuid4())[:8].upper()
    get_client().table("session_log").insert({
        "session_id": session_id,
        "role":       role,
        "login_time": datetime.now(timezone.utc).isoformat(),
    }).execute()
    log_event("INFO", "Auth", "LOGIN", f"Role '{role}' logged in  [session {session_id}]")
    return session_id


def log_logout(session_id: str, logout_type: str = "Sign Out") -> None:
    """Populate logout_time and duration for an existing session row."""
    now = datetime.now(timezone.utc)
    result = (
        get_client()
        .table("session_log")
        .select("login_time")
        .eq("session_id", session_id)
        .execute()
    )
    if result.data:
        try:
            login_dt = datetime.fromisoformat(result.data[0]["login_time"])
            # Ensure both are timezone-aware for subtraction
            if login_dt.tzinfo is None:
                login_dt = login_dt.replace(tzinfo=timezone.utc)
            duration = round((now - login_dt).total_seconds() / 60, 1)
        except Exception:
            duration = None
        get_client().table("session_log").update({
            "logout_time":   now.isoformat(),
            "duration_mins": duration,
            "logout_type":   logout_type,
        }).eq("session_id", session_id).execute()
    log_event("INFO", "Auth", "LOGOUT", f"Session {session_id} ended  [{logout_type}]")


# ── System event logging ──────────────────────────────────────────────────────

def log_event(level: str, source: str, event: str, message: str) -> None:
    """Append one event row to the system log."""
    count = (
        get_client()
        .table("system_log")
        .select("log_id", count="exact")
        .execute()
        .count
    ) or 0
    get_client().table("system_log").insert({
        "log_id":    f"L{count + 1:06d}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level":     level.upper(),
        "source":    source,
        "event":     event,
        "message":   message,
    }).execute()


# ── Read helpers ──────────────────────────────────────────────────────────────

def load_session_log() -> pd.DataFrame:
    result = (
        get_client()
        .table("session_log")
        .select("*")
        .order("login_time", desc=True)
        .execute()
    )
    if not result.data:
        return pd.DataFrame(columns=[
            "session_id", "role", "login_time", "logout_time",
            "duration_mins", "logout_type",
        ])
    df = pd.DataFrame(result.data)
    df["login_time"]    = pd.to_datetime(df["login_time"],  utc=True, errors="coerce").dt.tz_convert(None)
    df["logout_time"]   = pd.to_datetime(df["logout_time"], utc=True, errors="coerce").dt.tz_convert(None)
    df["duration_mins"] = pd.to_numeric(df["duration_mins"], errors="coerce")
    return df


def load_system_log() -> pd.DataFrame:
    result = (
        get_client()
        .table("system_log")
        .select("*")
        .order("timestamp", desc=True)
        .execute()
    )
    if not result.data:
        return pd.DataFrame(columns=[
            "log_id", "timestamp", "level", "source", "event", "message",
        ])
    df = pd.DataFrame(result.data)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(None)
    return df
