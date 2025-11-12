# -------------------------------------------------
# app.py | Hot Shot Props – Infinite Loader Edition
# -------------------------------------------------
# Never times out. Keeps retrying fetches until data is loaded.
# Shows user-friendly progress messages during long waits.
# -------------------------------------------------

import streamlit as st
import pandas as pd
import time
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
div[data-testid="stAlert"] p {font-size:16px;}
hr {border:0;border-top:1px solid #333;margin:1rem 0;}
.section {background:#1C1C1C;border-radius:12px;padding:1rem;margin-bottom:1rem;}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("<h1>🏀 Hot Shot Props</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#aaa;'>AI-powered NBA prop prediction lab with real-time edges</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------- INFINITE FETCH LOOP ----------
def wait_for_data():
    """Keep retrying until valid odds & games are fetched."""
    odds_df, games_df = pd.DataFrame(), pd.DataFrame()
    progress = st.empty()
    spinner = st.empty()
    tries = 0

    while (odds_df.empty or games_df.empty):
        tries += 1
        spinner.info(f"⏳ Attempt {tries}: Fetching live NBA odds and games... please wait.")
        time.sleep(1)

        try:
            # Odds first
            odds_df = load_fanduel_snapshot()
            if odds_df.empty:
                odds_df = fetch_fanduel_data()
        except Exception as e:
            st.warning(f"⚠️ Error loading odds: {e}")
            odds_df = pd.DataFrame()

        try:
            # Then games
            games_df = load_games_snapshot()
            if games_df.empty:
                games_df = fetch_games_today()
        except Exception as e:
            st.warning(f"⚠️ Error loading games: {e}")
            games_df = pd.DataFrame()

        # small sleep between retries to prevent API hammering
        if odds_df.empty or games_df.empty:
            progress.progress(min(1.0, (tries % 10) / 10.0))
            time.sleep(30)  # wait 30 sec then retry

    progress.empty()
    spinner.success(f"✅ Data loaded successfully after {tries} attempt(s).")
    return odds_df, games_df


# ---------- MAIN ----------
odds_df, games_df = wait_for_data()

st.markdown(f"<p style='color:#0f0;'>Last updated: {datetime.now().strftime('%b %d, %Y %I:%M %p')}</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------- DISPLAY GAMES ----------
st.markdown("### 🏀 Today's Games")
if games_df.empty:
    st.info("No games found for today (may be due to offseason).")
else:
    st.dataframe(
        games_df[["home_team", "away_team", "game_time", "status"]],
        use_container_width=True,
        hide_index=True
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ---------- RUN MODEL ----------
st.markdown("### 🤖 Top AI Model Edges (Projected Value Bets)")
try:
    preds_df = run_model_predictions(odds_df, games_df)
    if preds_df.empty:
        st.info("No AI model predictions yet — waiting for prop lines.")
    else:
        st.dataframe(
            preds_df[
                ["player", "prop_type", "line", "model_projection", "edge_pct", "expected_value_over", "expected_value_under"]
            ].round(2),
            use_container_width=True,
            hide_index=True
        )
except Exception as e:
    st.error(f"⚠️ Error running model predictions: {e}")

# ---------- FOOTER ----------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""
<p style='text-align:center;color:#888;font-size:13px;'>
Built by <b>Hot Shot Props</b> • AI-powered NBA analytics platform • Data from NBA API & FanDuel
</p>
""", unsafe_allow_html=True)
