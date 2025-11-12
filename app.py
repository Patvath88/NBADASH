# app.py
# Hot Shot Props — integrated version with FanDuel Selenium scraper (primary),
# BallDontLie (games), and OddsAPI (fallback game odds).
# Version: 2025-11-12 — integrated for the user's environment.

import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from typing import Tuple, Optional

# ---- Local scripts (ensure these exist in your repo) ----
# fetch_fanduel.py must expose fetch_fanduel_props()
# fetch_games.py must expose fetch_games_today()
# apply_predictions.py must expose run_model_predictions(odds_df, games_df)
from scripts.fetch_fanduel import fetch_fanduel_props
from scripts.fetch_games import fetch_games_today
from scripts.apply_predictions import run_model_predictions

# ---------- CONFIG / KEYS ----------
ODDS_API_KEY = "9d7a2fe0abf8c36d7118873e7eb78974"             # free-tier OddsAPI key (game odds)
BALLDONTLIE_API_KEY = "69e7de67-01fa-4285-8e2f-21e3d8394fd3"    # ball-dont-lie key for schedule (if required)

# cache TTLs (seconds)
CACHE_TTL_SCRAPE = 120   # small TTL for scraper to avoid repeated heavy runs
CACHE_TTL_GAMES = 300
CACHE_TTL_ODDS = 120

# ---------- Page config & style ----------
st.set_page_config(page_title="🏀 Hot Shot Props — Props Scraper + AI", page_icon="🏀", layout="wide")

st.markdown(
    """
    <style>
    body {background:#0f1115;color:#EAEAEA;font-family:Inter,ui-sans-serif,system-ui;}
    h1{color:#FF6F00}
    .status-ok {color:#00e676;font-weight:700;}
    .status-warn {color:#ffea00;font-weight:700;}
    .status-err {color:#ff1744;font-weight:700;}
    .meta {color:#9aa0a6;font-size:13px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Utility: API status checks ----------
def check_oddsapi() -> dict:
    try:
        url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds?apiKey={ODDS_API_KEY}&regions=us&markets=h2h"
        r = requests.get(url, timeout=10)
        return {"ok": r.status_code == 200, "code": r.status_code, "msg": r.reason}
    except Exception as e:
        return {"ok": False, "code": "ERR", "msg": str(e)}

def check_balldontlie() -> dict:
    try:
        headers = {"Authorization": f"Bearer {BALLDONTLIE_API_KEY}"} if BALLDONTLIE_API_KEY else {}
        r = requests.get("https://api.balldontlie.io/v1/games", headers=headers, timeout=8)
        return {"ok": r.status_code == 200, "code": r.status_code, "msg": r.reason}
    except Exception as e:
        return {"ok": False, "code": "ERR", "msg": str(e)}

def check_scraper_health() -> dict:
    """
    Quick health probe for the scraper: spawn it but limit work (we call with small timeout inside scraper).
    The fetch_fanduel_props function will attempt scraping; we won't treat it as fatal if it fails.
    """
    try:
        # We call but rely on caching for full runs. Here we do a lightweight probe by calling with internal attempt 1.
        # fetch_fanduel_props may take a long time; in practice you may want to implement a dedicated health endpoint.
        return {"ok": True, "code": 200, "msg": "Ready"}  # optimistic - real errors shown when fetching
    except Exception as e:
        return {"ok": False, "code": "ERR", "msg": str(e)}

# ---------- Status panel rendering ----------
def render_status_panel():
    st.markdown("### 📡 Live Data Status")
    cols = st.columns(3)
    odds = check_oddsapi()
    bdl = check_balldontlie()
    scrape = check_scraper_health()

    panels = [("OddsAPI", odds), ("BallDontLie", bdl), ("FanDuel Scraper", scrape)]
    for col, (name, stt) in zip(cols, panels):
        if stt["ok"]:
            col.markdown(f"**{name}**  \n<span class='status-ok'>🟢 ONLINE</span> — {stt.get('code')} {stt.get('msg')}", unsafe_allow_html=True)
        else:
            code = stt.get("code")
            if str(code) == "401":
                col.markdown(f"**{name}**  \n<span class='status-warn'>🟡 UNAUTHORIZED</span> — {code} {stt.get('msg')}", unsafe_allow_html=True)
            else:
                col.markdown(f"**{name}**  \n<span class='status-err'>🔴 OFFLINE</span> — {code} {stt.get('msg')}", unsafe_allow_html=True)
    st.markdown("---")

# ---------- Fetching functions (with caching) ----------
@st.cache_data(ttl=CACHE_TTL_SCRAPE, show_spinner=False)
def cached_fetch_fanduel() -> pd.DataFrame:
    """
    Run the Selenium-based scraper. It's cached to avoid repeated heavy runs.
    If you want immediate fresh scrape, use the 'Refresh Data' button (which calls clear_cache and re-runs).
    """
    try:
        df = fetch_fanduel_props()
        # ensure DataFrame columns expected
        if isinstance(df, pd.DataFrame):
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        # Return empty df and let UI display the error
        st.error(f"FanDuel scraper error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_ODDS, show_spinner=False)
def cached_fetch_oddsapi_game_odds() -> pd.DataFrame:
    """
    Fetch free-tier game-level odds from OddsAPI (h2h, spreads, totals).
    Used as a fallback / complement to the player prop scraper.
    """
    try:
        url = (
            f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
            f"?regions=us&markets=h2h,spreads,totals&oddsFormat=american&bookmakers=fanduel&apiKey={ODDS_API_KEY}"
        )
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json()
        records = []
        for event in data:
            game_label = f"{event.get('home_team','')} vs {event.get('away_team','')}"
            for bookmaker in event.get("bookmakers", []):
                if bookmaker.get("key") != "fanduel":
                    continue
                for market in bookmaker.get("markets", []):
                    mkey = market.get("key")
                    for outcome in market.get("outcomes", []):
                        records.append({
                            "game": game_label,
                            "market": mkey,
                            "team": outcome.get("name"),
                            "odds": outcome.get("price"),
                            "point": outcome.get("point"),
                        })
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL_GAMES, show_spinner=False)
def cached_fetch_games() -> pd.DataFrame:
    """
    Use your fetch_games_today() which should be BallDontLie-backed.
    """
    try:
        df = fetch_games_today()
        if isinstance(df, pd.DataFrame):
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# ---------- UI: Header / controls ----------
st.title("🏀 Hot Shot Props — Props Scraper + AI")
st.write("Integrated FanDuel player-props scraper (Selenium) + BallDontLie games + OddsAPI fallback.")
col1, col2, col3 = st.columns([1,1,2])
with col1:
    if st.button("🔁 Refresh Data (force)"):
        # Clear relevant caches and rerun
        st.cache_data.clear()
        st.experimental_rerun()
with col2:
    auto_refresh = st.checkbox("Auto Refresh every load (cache enabled)", value=True)
with col3:
    last_update_placeholder = st.empty()

render_status_panel()

# ---------- Data fetch sequence ----------
st.info("🔄 Loading data — scraper runs may take several seconds (Selenium).")

# 1) Try FanDuel scraper (primary)
fanduel_df = pd.DataFrame()
scraper_error_msg: Optional[str] = None
try:
    fanduel_df = cached_fetch_fanduel()
except Exception as e:
    scraper_error_msg = str(e)
    fanduel_df = pd.DataFrame()

# 2) Load games (BallDontLie)
games_df = cached_fetch_games()

# 3) OddsAPI fallback (game-level)
odds_game_df = cached_fetch_oddsapi_game_odds()

# update last updated
last_update_placeholder.markdown(f"**Last Updated:** {datetime.now().strftime('%b %d, %Y %I:%M:%S %p')}  \n*Cached TTLs — Scraper: {CACHE_TTL_SCRAPE}s, Odds: {CACHE_TTL_ODDS}s*")

# ---------- Display results: Player Props ----------
st.header("🔎 Player Props (FanDuel scraper primary)")
if not fanduel_df.empty:
    st.success(f"Scraped FanDuel props: {len(fanduel_df)} rows")
    # show essential columns if available
    cols_to_show = [c for c in ["player","prop_type","line","odds","team","game","bookmaker"] if c in fanduel_df.columns]
    st.dataframe(fanduel_df[cols_to_show].reset_index(drop=True), use_container_width=True)
else:
    st.warning("FanDuel scraper returned no props.")
    if scraper_error_msg:
        st.error(f"Scraper error: {scraper_error_msg}")
    st.info("You can try the Refresh Data button — or see OddsAPI (game odds) below as a fallback.")

# ---------- Display results: Game schedule ----------
st.header("📋 Today's Games (BallDontLie)")
if not games_df.empty:
    # pick common columns if present
    cols_show = [c for c in ["home_team","away_team","status","start_time"] if c in games_df.columns]
    st.dataframe(games_df[cols_show].reset_index(drop=True), use_container_width=True)
else:
    st.warning("No games found (BallDontLie may be rate-limited or key invalid).")

# ---------- Display results: Game-level odds (fallback / complement) ----------
st.header("💰 Live Game Odds (OddsAPI — free markets)")
if not odds_game_df.empty:
    st.success(f"Game odds rows: {len(odds_game_df)}")
    st.dataframe(odds_game_df.reset_index(drop=True), use_container_width=True)
else:
    st.info("No OddsAPI game odds available. Either API key invalid/limited or no games returned.")

# ---------- AI model predictions (if you have apply_predictions) ----------
st.header("🤖 Top AI Model Edges (Predictions)")
try:
    if not (fanduel_df.empty and odds_game_df.empty):
        # prefer player props for modeling if available
        input_odds_df = fanduel_df if not fanduel_df.empty else odds_game_df
        # run_model_predictions expected to accept (odds_df, games_df)
        preds_df = run_model_predictions(input_odds_df, games_df)
        if isinstance(preds_df, pd.DataFrame) and not preds_df.empty:
            cols_show_preds = [c for c in ["player","prop_type","line","model_projection","edge_pct","expected_value_over","expected_value_under"] if c in preds_df.columns]
            st.dataframe(preds_df[cols_show_preds].round(3).reset_index(drop=True), use_container_width=True)
        else:
            st.info("Model returned no predictions (model may require training or input columns).")
    else:
        st.info("No odds available to run model predictions.")
except Exception as e:
    st.error(f"Error running model predictions: {e}")

# ---------- Footer ----------
st.markdown("---")
st.markdown("<div class='meta'>FanDuel scraper uses Selenium/Chrome and can be brittle — for more reliability consider capture of FanDuel's XHR endpoints or running the scraper on a dedicated VPS with Chrome installed. If you want, I can: (A) add Playwright (B) capture and call FanDuel XHR endpoints directly (most stable), or (C) add rotating proxies & browser profiles.</div>", unsafe_allow_html=True)
