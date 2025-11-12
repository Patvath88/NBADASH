# -------------------------------------------------
# app.py | Hot Shot Props – NBA Prop Lab (AI + Live Status)
# -------------------------------------------------
# Version: 2025-11-12
# Includes working OddsAPI + BallDontLie integrations
# -------------------------------------------------

import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from scripts.fetch_games import fetch_games_today
from scripts.apply_predictions import run_model_predictions

# ---------- API KEYS ----------
ODDS_API_KEY = "9d7a2fe0abf8c36d7118873e7eb78974"
BALLDONTLIE_API_KEY = "69e7de67-01fa-4285-8e2f-21e3d8394fd3"

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

# -------------------------------------------------
# 📡 LIVE DATA STATUS PANEL
# -------------------------------------------------
def check_status():
    """Ping all APIs and return their live status."""
    status = {}

    # OddsAPI check
    try:
        resp = requests.get(
            f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds?apiKey={ODDS_API_KEY}",
            timeout=10,
        )
        status["OddsAPI"] = {
            "ok": resp.status_code == 200,
            "code": resp.status_code,
            "msg": resp.reason,
        }
    except Exception as e:
        status["OddsAPI"] = {"ok": False, "code": "ERR", "msg": str(e)}

    # BallDontLie check
    try:
        headers = {"Authorization": f"Bearer {BALLDONTLIE_API_KEY}"}
        resp = requests.get("https://api.balldontlie.io/v1/games", headers=headers, timeout=10)
        status["BallDontLie"] = {
            "ok": resp.status_code == 200,
            "code": resp.status_code,
            "msg": resp.reason,
        }
    except Exception as e:
        status["BallDontLie"] = {"ok": False, "code": "ERR", "msg": str(e)}

    # NBA Stats (expected to timeout)
    try:
        resp = requests.get("https://stats.nba.com/stats/scoreboardv2", timeout=10)
        status["NBA Stats"] = {
            "ok": resp.status_code == 200,
            "code": resp.status_code,
            "msg": resp.reason,
        }
    except Exception as e:
        status["NBA Stats"] = {"ok": False, "code": "ERR", "msg": str(e)}

    return status


def render_status_panel():
    """Display API health visually in dashboard."""
    st.markdown("### 📡 Live Data Status")
    status = check_status()
    cols = st.columns(3)

    for i, (name, data) in enumerate(status.items()):
        col = cols[i]
        if data["ok"]:
            col.markdown(
                f"<div class='data-status'><h4>{name}</h4>"
                f"<p class='status-ok'>🟢 ONLINE</p>"
                f"<p>{data['code']} – {data['msg']}</p></div>",
                unsafe_allow_html=True,
            )
        elif str(data["code"]) == "401":
            col.markdown(
                f"<div class='data-status'><h4>{name}</h4>"
                f"<p class='status-warn'>🟡 UNAUTHORIZED</p>"
                f"<p>401 – Invalid or missing API key</p></div>",
                unsafe_allow_html=True,
            )
        else:
            col.markdown(
                f"<div class='data-status'><h4>{name}</h4>"
                f"<p class='status-err'>🔴 OFFLINE</p>"
                f"<p>{data['code']} – {data['msg']}</p></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr>", unsafe_allow_html=True)

# -------------------------------------------------
# 📊 Fetch Odds via OddsAPI
# -------------------------------------------------
def fetch_odds_data():
    """Fetch FanDuel props via OddsAPI."""
    st.info("📊 Fetching FanDuel NBA player props...")
    url = (
        f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
        f"?regions=us&markets=player_points,player_rebounds,player_assists,player_threes"
        f"&oddsFormat=american&apiKey={ODDS_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            st.error(f"OddsAPI Error: {resp.status_code} — {resp.reason}")
            return pd.DataFrame()

        data = resp.json()
        records = []
        for event in data:
            game = f"{event.get('home_team', '')} vs {event.get('away_team', '')}"
            for bookmaker in event.get("bookmakers", []):
                if bookmaker.get("key") != "fanduel":
                    continue
                for market in bookmaker.get("markets", []):
                    prop_type = market["key"]
                    for outcome in market.get("outcomes", []):
                        records.append({
                            "player": outcome.get("name"),
                            "prop_type": prop_type.replace("player_", "").upper(),
                            "line": outcome.get("point"),
                            "odds": outcome.get("price"),
                            "game": game,
                        })
        df = pd.DataFrame(records)
        if df.empty:
            st.warning("⚠️ No props found in OddsAPI response.")
        else:
            st.success(f"✅ Loaded {len(df)} props from OddsAPI.")
        return df

    except Exception as e:
        st.error(f"⚠️ Error fetching OddsAPI data: {e}")
        return pd.DataFrame()

# -------------------------------------------------
# 🚀 Main Runtime
# -------------------------------------------------
render_status_panel()

@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    odds_df = fetch_odds_data()
    games_df = fetch_games_today()
    return odds_df, games_df

st.info("🔄 Fetching data... please wait.")
odds_df, games_df = load_data()

if not odds_df.empty and not games_df.empty:
    st.success(f"✅ Data refreshed successfully — {datetime.now().strftime('%b %d, %Y %I:%M %p')}")
else:
    st.warning("⚠️ Data sources may be offline or unauthorized. Check API status above.")

st.markdown("<hr>", unsafe_allow_html=True)

# ---------- Display Games ----------
st.markdown("### 🏀 Today's Games")
if games_df.empty:
    st.warning("No games found for today (check BallDontLie or key validity).")
else:
    st.dataframe(
        games_df[["home_team", "away_team", "status"]].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ---------- Display AI Model Predictions ----------
st.markdown("### 🤖 Top AI Model Edges (Projected Value Bets)")
if not odds_df.empty and not games_df.empty:
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
