# -------------------------------------------------
# app.py | Hot Shot Props – NBA Prop Lab (Free Tier Stable Build)
# -------------------------------------------------
# Version: 2025-11-12
# Uses: OddsAPI game-level data + BallDontLie game schedule
# -------------------------------------------------

import streamlit as st
import pandas as pd
import requests
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
st.markdown("<p style='color:#aaa;'>AI-powered NBA prediction lab with live game odds & model edges</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# -------------------------------------------------
# 📡 LIVE DATA STATUS PANEL
# -------------------------------------------------
def check_status():
    status = {}

    # OddsAPI check
    try:
        resp = requests.get(
            f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds?apiKey={ODDS_API_KEY}&regions=us&markets=h2h",
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

    # NBA Stats check
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
# 🏀 Fetch Live Game Odds (Supported Free Markets)
# -------------------------------------------------
def fetch_odds_data():
    """Fetches NBA game odds for free-tier markets (h2h, spreads, totals)."""
    st.info("📊 Fetching NBA game odds (free-tier markets)...")

    url = (
        f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
        f"?regions=us&markets=h2h,spreads,totals"
        f"&oddsFormat=american&bookmakers=fanduel&apiKey={ODDS_API_KEY}"
    )

    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 401:
            st.error("🚫 OddsAPI 401: Invalid or inactive API key.")
            return pd.DataFrame()
        elif resp.status_code == 422:
            st.error("⚠️ OddsAPI 422: Invalid markets for your plan. Using free-tier endpoints only.")
            return pd.DataFrame()
        elif resp.status_code != 200:
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
                    market_type = market.get("key", "")
                    for outcome in market.get("outcomes", []):
                        records.append({
                            "game": game,
                            "market": market_type,
                            "team": outcome.get("name"),
                            "odds": outcome.get("price"),
                            "point": outcome.get("point"),
                        })

        df = pd.DataFrame(records)
        if df.empty:
            st.warning("⚠️ No odds data found for these markets (check OddsAPI usage).")
        else:
            st.success(f"✅ Loaded {len(df)} odds from OddsAPI (FanDuel).")
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
    st.warning("⚠️ Data sources may be offline or limited by API plan.")

st.markdown("<hr>", unsafe_allow_html=True)

# ---------- Display Games ----------
st.markdown("### 🏀 Today's Games")
if games_df.empty:
    st.warning("No games found for today (check BallDontLie key or timing).")
else:
    st.dataframe(
        games_df[["home_team", "away_team", "status"]].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ---------- Display Game Odds ----------
st.markdown("### 💰 Live Game Odds (FanDuel)")
if not odds_df.empty:
    st.dataframe(
        odds_df[["game", "market", "team", "odds", "point"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No odds data available (free-tier markets only).")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#888;font-size:13px;'>"
    "Built by <b>Hot Shot Props</b> • Powered by OddsAPI & BallDontLie</p>",
    unsafe_allow_html=True,
)
