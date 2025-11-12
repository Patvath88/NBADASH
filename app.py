# -------------------------------------------------
# app.py | Hot Shot Props – NBA Prop Lab (AI Edition)
# -------------------------------------------------
# Displays: Game Slate + AI Model Top Edges + Player Analyzer Link
# Auto-refreshes data each runtime and self-heals missing files.
# -------------------------------------------------

import streamlit as st
import pandas as pd
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

# ---------- STYLES ----------
st.markdown("""
<style>
body {background:#121212;color:#EAEAEA;font-family:'Roboto',sans-serif;}
h1,h2,h3 {color:#FF6F00;text-shadow:0 0 8px #FF9F43;font-family:'Oswald',sans-serif;}
div[data-testid="stAlert"] p {font-size:16px;}
hr {border:0;border-top:1px solid #333;margin:1rem 0;}
.section {background:#1C1C1C;border-radius:12px;padding:1rem;margin-bottom:1rem;}
</style>
""", unsafe_allow_html=True)

# ---------- TITLE ----------
st.markdown("<h1>🏀 Hot Shot Props</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#aaa;'>AI-powered NBA prop prediction lab with real-time edges</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------- LOAD OR REFRESH DATA ----------
@st.cache_data(ttl=60*60, show_spinner=False)
def load_data():
    """Auto-fetch and load all required data safely."""
    try:
        odds_df = load_fanduel_snapshot()
        if odds_df.empty:
            odds_df = fetch_fanduel_data()
    except Exception as e:
        st.error(f"Error loading odds: {e}")
        odds_df = pd.DataFrame()

    try:
        games_df = load_games_snapshot()
        if games_df.empty:
            games_df = fetch_games_today()
    except Exception as e:
        st.error(f"Error loading games: {e}")
        games_df = pd.DataFrame()

    return odds_df, games_df


with st.spinner("Fetching live data..."):
    odds_df, games_df = load_data()

# ---------- STATUS CHECK ----------
if odds_df.empty or games_df.empty:
    st.warning("⚠️ No games or odds found (possibly due to UTC timing or offseason).")
else:
    st.success(f"✅ Data refreshed successfully — {datetime.now().strftime('%b %d, %Y %I:%M %p')}")

# ---------- DISPLAY GAME SLATE ----------
st.markdown("### 🏀 Today's Games")
if games_df.empty:
    st.info("No games found for today (may be due to UTC timing or offseason).")
else:
    st.dataframe(
        games_df[["home_team", "away_team", "game_time", "status"]].reset_index(drop=True),
        use_container_width=True
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ---------- RUN AI MODEL PREDICTIONS ----------
st.markdown("### 🤖 Top AI Model Edges (Projected Value Bets)")
try:
    if not odds_df.empty:
        preds_df = run_model_predictions(odds_df, games_df)
        if preds_df.empty:
            st.info("No AI model predictions yet. Try again after data refresh.")
        else:
            st.dataframe(
                preds_df[
                    ["player", "prop_type", "line", "model_projection", "edge_pct", "expected_value_over", "expected_value_under"]
                ].round(2),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No odds data available.")
except Exception as e:
    st.error(f"Error running model predictions: {e}")

# ---------- FOOTER ----------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("""
<p style='text-align:center;color:#888;font-size:13px;'>
Built by <b>Hot Shot Props</b> • AI-powered NBA analytics platform • Data from NBA API & FanDuel
</p>
""", unsafe_allow_html=True)
