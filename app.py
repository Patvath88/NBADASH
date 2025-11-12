# app.py
# Hot Shot Props — NBA Prop Dashboard (Patched Version)
# Integrated: FanDuel XHR scraper + BallDontLie games + AI predictions placeholder

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from scripts.fanduel_xhr import fetch_fanduel_props_xhr as fetch_fanduel_props
from scripts.fetch_games import fetch_games_today
from scripts.apply_predictions import run_model_predictions

# ---------- CONFIG ----------
ODDS_API_KEY = "9d7a2fe0abf8c36d7118873e7eb78974"

st.set_page_config(
    page_title="🏀 Hot Shot Props | NBA Prop Lab",
    page_icon="🏀",
    layout="wide"
)

# ---------- STYLES ----------
st.markdown("""
<style>
body {background:#0f1115;color:#EAEAEA;font-family:Inter,ui-sans-serif;}
h1{color:#FF6F00}
.status-ok {color:#00e676;font-weight:700;}
.status-warn {color:#ffea00;font-weight:700;}
.status-err {color:#ff1744;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ---------- UTILITIES ----------
@st.cache_data(ttl=120, show_spinner=False)
def cached_fetch_fanduel():
    try:
        return fetch_fanduel_props()
    except Exception as e:
        st.error(f"FanDuel scraper error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_games():
    try:
        return fetch_games_today()
    except Exception as e:
        st.error(f"Game fetch error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=180, show_spinner=False)
def cached_fetch_oddsapi_game_odds():
    try:
        url = (
            f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
            f"?regions=us&markets=h2h,spreads,totals&oddsFormat=american"
            f"&bookmakers=fanduel&apiKey={ODDS_API_KEY}"
        )
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json()
        records = []
        for event in data:
            game = f"{event.get('home_team','')} vs {event.get('away_team','')}"
            for bookmaker in event.get("bookmakers", []):
                if bookmaker.get("key") != "fanduel":
                    continue
                for market in bookmaker.get("markets", []):
                    for o in market.get("outcomes", []):
                        records.append({
                            "game": game,
                            "market": market.get("key"),
                            "team": o.get("name"),
                            "odds": o.get("price"),
                            "point": o.get("point")
                        })
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()

# ---------- UI ----------
st.title("🏀 Hot Shot Props — NBA Prop Lab (AI)")
st.write("Live FanDuel props + BallDontLie games + AI model preview.")

col1, col2 = st.columns([1,1])
if col1.button("🔁 Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()
last_update = datetime.now().strftime("%b %d, %Y %I:%M:%S %p")
col2.write(f"**Last updated:** {last_update}")

# ---------- LOAD DATA ----------
st.info("⏳ Fetching live data...")
fanduel_df = cached_fetch_fanduel()
games_df = cached_fetch_games()
odds_df = cached_fetch_oddsapi_game_odds()

# ---------- FAN DUEL DATA ----------
st.header("🎯 FanDuel Player Props")
if fanduel_df.empty:
    st.warning("No FanDuel props found.")
else:
    st.success(f"Fetched {len(fanduel_df)} props from FanDuel.")
    show_cols = [c for c in ["player","prop_type","line","odds","team","game"] if c in fanduel_df.columns]
    st.dataframe(fanduel_df[show_cols], use_container_width=True)

# ---------- GAMES ----------
st.header("🏀 Today's Games (BallDontLie)")
if games_df.empty:
    st.warning("No games available.")
else:
    show_cols = [c for c in ["home_team","away_team","status","start_time"] if c in games_df.columns]
    st.dataframe(games_df[show_cols], use_container_width=True)

# ---------- GAME ODDS ----------
st.header("💰 Game Odds (OddsAPI Fallback)")
if odds_df.empty:
    st.warning("No game odds available.")
else:
    st.dataframe(odds_df, use_container_width=True)

# ---------- AI PREDICTIONS ----------
st.header("🤖 AI Model Predictions (Preview)")
try:
    input_odds = fanduel_df if not fanduel_df.empty else odds_df
    preds = run_model_predictions(input_odds, games_df)
    if preds is not None and not preds.empty:
        st.success(f"Generated {len(preds)} predictions.")
        st.dataframe(preds, use_container_width=True)
    else:
        st.info("Model produced no predictions.")
except Exception as e:
    st.error(f"Prediction error: {e}")

st.markdown("---")
st.caption("Hot Shot Props © 2025 — FanDuel scraping + AI predictions demo.")
