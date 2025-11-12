import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# --- Local imports ---
from scripts.fetch_fanduel import fetch_fanduel_props
from scripts.fetch_games import fetch_games_today
from scripts.apply_predictions import run_model_predictions

# --- PAGE CONFIG ---
st.set_page_config(page_title="Hot Shot Props — NBA Prop Lab (AI)",
                   page_icon="🏀", layout="wide")

# --- HEADER ---
st.markdown("<h1 style='color:#FF6F00;'>🏀 Hot Shot Props — NBA Prop Lab (AI)</h1>", unsafe_allow_html=True)
st.markdown("<p>Live FanDuel props + BallDontLie games + AI model preview.</p>", unsafe_allow_html=True)

# --- REFRESH DATA ---
col1, col2 = st.columns([1, 1])
if col1.button("🔁 Refresh Data"):
    st.cache_data.clear()
    st.rerun()
last_update = datetime.now().strftime("%b %d, %Y %I:%M:%S %p")
col2.write(f"**Last updated:** {last_update}")

# --- FETCH LIVE DATA ---
with st.status("⏳ Fetching live data...", expanded=False):
    try:
        props_df = fetch_fanduel_props()
    except Exception as e:
        st.error(f"FanDuel fetch error: {e}")
        props_df = pd.DataFrame()

    try:
        games_df = fetch_games_today()
    except Exception as e:
        st.error(f"Game fetch error: {e}")
        games_df = pd.DataFrame()

# --- DISPLAY DATA ---
st.subheader("🎯 FanDuel Player Props")
if props_df.empty:
    st.warning("No FanDuel props found.")
else:
    st.dataframe(props_df.head(30), use_container_width=True)

st.subheader("🏀 Today's Games (BallDontLie)")
if games_df.empty:
    st.warning("No games available.")
else:
    st.dataframe(games_df, use_container_width=True)

# --- RUN AI PREDICTIONS ---
st.subheader("🤖 AI Model Predictions (Preview)")
try:
    preds_df = run_model_predictions(props_df, games_df)
    if preds_df.empty:
        st.info("No model predictions yet.")
    else:
        st.dataframe(preds_df.head(20), use_container_width=True)
except Exception as e:
    st.error(f"Prediction error: {e}")
