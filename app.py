# -------------------------------------------------
# app.py | Hot Shot Props – NBA Prop Lab (AI + Live Status)
# -------------------------------------------------
# Adds Live Data Status display for all data sources.
# -------------------------------------------------

import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from scripts.fetch_fanduel import load_fanduel_snapshot, fetch_fanduel_data
from scripts.fetch_games import load_games_snapshot, fetch_games_today
from scripts.apply_predictions import run_model_predictions

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="🏀 Hot Shot Props | NBA Prop Lab (AI)",
    page_icon="🏀",
    layout="wide",
)

# ---------- STYLE ----------
st.markdown("""
<style>
body {background:#121212;color:#EAEAEA;font-family:'Roboto',sans-serif;}
h1,h2,h3 {color:#FF6F00;text-shadow:0 0 8px #FF9F43;font-family:'Oswald',sans-serif;}
.section {background:#1C1C1C;border-radius:12px;padding:1rem;margin-bottom:1rem;}
.data-status {background:#1e1e1e;border-radius:10px;padding:1rem;margin-bottom:1rem;}
.data-status h4 {margin-bottom:0.5rem;}
.status-ok {color:#00e676;font-weight:bold;}
.status-warn {color:#ffea00;font-weight:bold;}
.status-err {color:#ff1744;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("<h1>🏀 Hot Shot Props</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#aaa;'>AI-powered NBA prop prediction lab with real-time edges</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)


# ---------- LIVE STATUS PANEL ----------
def check_status():
    """Ping all key APIs and return their status."""
    status = {}

    # OddsAPI check
    try:
        odds_start = time.time()
        resp = requests.get(
            "https://api.the-odds-api.com/v4/sports/basketball_nba/odds",
            timeout=10,
        )
        odds_time = round((time.time() - odds_start), 2)
        status["OddsAPI"] = {
            "ok": resp.status_code == 200,
            "code": resp.status_code,
            "time": odds_time,
        }
    except Exception as e:
        status["OddsAPI"] = {"ok": False, "code": str(e), "time": None}

    # BallDontLie check
    try:
        games_start = time.time()
        resp = requests.get("https://api.balldontlie.io/v1/games", timeout=10)
        games_time = round((time.time() - games_start), 2)
        status["BallDontLie"] = {
            "ok": resp.status_code == 200,
            "code": resp.status_code,
            "time": games_time,
        }
    except Exception as e:
        status["BallDontLie"] = {"ok": False, "code": str(e), "time": None}

    # NBA API (Player Stats)
    try:
        nba_start = time.time()
        resp = requests.get("https://stats.nba.com/stats/scoreboardv2", timeout=10)
        nba_time = round((time.time() - nba_start), 2)
        status["NBA Stats"] = {
            "ok": resp.status_code == 200,
            "code": resp.status_code,
            "time": nba_time,
        }
    except Exception as e:
        status["NBA Stats"] = {"ok": False, "code": str(e), "time": None}

    return status


def render_status_panel():
    """Display API health visually in the dashboard."""
    st.markdown("### 📡 Live Data Status")

    status = check_status()
    cols = st.columns(3)
    for i, (name, data) in enumerate(status.items()):
        col = cols[i]
        if data["ok"]:
            col.markdown(
                f"<div class='data-status'><h4>{name}</h4>"
                f"<p class='status-ok'>🟢 ONLINE</p>"
                f"<p>Response: {data['code']} • {data['time']}s</p></div>",
                unsafe_allow_html=True,
            )
        elif data["time"] is None:
            col.markdown(
                f"<div class='data-status'><h4>{name}</h4>"
                f"<p class='status-err'>🔴 OFFLINE</p>"
                f"<p>{data['code']}</p></div>",
                unsafe_allow_html=True,
            )
        else:
            col.markdown(
                f"<div class='data-status'><h4>{name}</h4>"
                f"<p class='status-warn'>🟡 UNSTABLE</p>"
                f"<p>Response: {data['code']} • {data['time']}s</p></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr>", unsafe_allow_html=True)


# ---------- MAIN DASHBOARD ----------
render_status_panel()

# (Everything below this stays the same)
# Fetch data, show games, and model predictions
from scripts.fetch_games import load_games_snapshot, fetch_games_today
from scripts.fetch_fanduel import load_fanduel_snapshot, fetch_fanduel_data
from scripts.apply_predictions import run_model_predictions

def wait_for_data():
    odds_df, games_df = pd.DataFrame(), pd.DataFrame()
    st.info("🔄 Fetching data... please wait.")

    odds_df = load_fanduel_snapshot()
    if odds_df.empty:
        odds_df = fetch_fanduel_data()

    games_df = load_games_snapshot()
    if games_df.empty:
        games_df = fetch_games_today()

    return odds_df, games_df


odds_df, games_df = wait_for_data()
st.success(f"✅ Data refreshed successfully — {datetime.now().strftime('%b %d, %Y %I:%M %p')}")
st.markdown("<hr>", unsafe_allow_html=True)

# ---------- DISPLAY ----------
st.markdown("### 🏀 Today's Games")
if games_df.empty:
    st.warning("No games found for today (check data source).")
else:
    st.dataframe(
        games_df[["home_team", "away_team", "status"]].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("### 🤖 Top AI Model Edges (Projected Value Bets)")
if not odds_df.empty:
    preds_df = run_model_predictions(odds_df, games_df)
    st.dataframe(
        preds_df[
            ["player", "prop_type", "line", "model_projection", "edge_pct", "expected_value_over", "expected_value_under"]
        ].round(2),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No odds data available.")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#888;font-size:13px;'>"
    "Built by <b>Hot Shot Props</b> • AI-powered NBA analytics platform</p>",
    unsafe_allow_html=True,
)
