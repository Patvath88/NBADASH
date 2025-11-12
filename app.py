import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from scripts.fetch_fanduel import fetch_fanduel_data
from scripts.fetch_games import fetch_games_today
from scripts.apply_predictions import run_model_predictions

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="🏀 Hot Shot Props | NBA Prop Lab (AI)",
    page_icon="🏀",
    layout="wide"
)

# ---------- STYLE ----------
st.markdown("""
<style>
body {background:#121212;color:#EAEAEA;font-family:'Roboto',sans-serif;}
.title {font-size:34px;font-weight:700;color:#FF6F00;text-shadow:0 0 6px #FF9F43;}
.subtext {font-size:16px;color:#BBB;margin-bottom:12px;}
.card {
  background:#1C1C1C;border-radius:12px;padding:16px;margin-bottom:12px;
  box-shadow:0 0 10px rgba(0,0,0,0.35);
}
.prop-row {display:flex;justify-content:space-between;align-items:center;padding:4px 0;}
.prop-type {font-weight:600;color:#FF9F43;}
.line {color:#EAEAEA;}
.ev {font-weight:600;}
.edge-bar {
  height:10px;border-radius:5px;background:linear-gradient(90deg,#FF9F43,#FF6F00);
}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown(f"<div class='title'>🏀 Hot Shot Props</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>AI-powered NBA prop prediction lab with real-time edges</div>", unsafe_allow_html=True)
st.markdown("---")


# ---------- LOAD DATA HELPERS ----------
@st.cache_data(ttl=600)
def load_odds_data():
    try:
        odds_path = os.path.join("data", "odds_snapshot.json")
        if not os.path.exists(odds_path):
            df = fetch_fanduel_data()
        else:
            with open(odds_path, "r") as f:
                df = pd.DataFrame(json.load(f))
        return df
    except Exception as e:
        st.error(f"Error loading odds: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_games_data():
    try:
        games_path = os.path.join("data", "games_today.json")
        if not os.path.exists(games_path):
            df = fetch_games_today()
        else:
            with open(games_path, "r") as f:
                df = pd.DataFrame(json.load(f))
        return df
    except Exception as e:
        st.error(f"Error loading games: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_model_predictions():
    try:
        pred_path = os.path.join("data", "model_predictions.csv")
        if not os.path.exists(pred_path):
            df = run_model_predictions()
        else:
            df = pd.read_csv(pred_path)
        return df
    except Exception as e:
        st.error(f"Error loading predictions: {e}")
        return pd.DataFrame()


# ---------- LOAD DATA ----------
odds_df = load_odds_data()
games_df = load_games_data()
pred_df = load_model_predictions()

# ---------- SECTION 1: Today's Games ----------
st.subheader(f"📅 Today's Games — {datetime.now().strftime('%b %d, %Y')}")
if games_df.empty:
    st.warning("No games found for today (may be due to UTC timing or offseason).")
else:
    for _, game in games_df.iterrows():
        st.markdown(
            f"<div class='card'><b>{game['away_team']}</b> @ <b>{game['home_team']}</b> "
            f"<span style='color:#888'>— {game['game_time']}</span></div>",
            unsafe_allow_html=True
        )


# ---------- SECTION 2: AI Model Top Edges ----------
st.markdown("---")
st.subheader("🤖 Top AI Model Edges (Projected Value Bets)")

if pred_df.empty:
    st.info("No AI model predictions yet. Run `scripts/apply_predictions.py` manually or wait for data refresh.")
else:
    # Keep only highest-edge props
    top_edges = pred_df.sort_values("edge_%", ascending=False).head(15)

    st.dataframe(
        top_edges[["player", "prop_type", "projection", "line", "edge_%", "odds_over"]]
        .rename(columns={
            "player": "Player",
            "prop_type": "Prop",
            "projection": "Model Projection",
            "line": "Sportsbook Line",
            "edge_%": "Edge %",
            "odds_over": "Odds"
        }),
        hide_index=True,
        use_container_width=True
    )

    # Visual edge summary
    st.markdown("### 🔥 Edge Strength Overview")
    for _, row in top_edges.iterrows():
        bar_width = max(0, min(100, row["edge_%"])) if not pd.isna(row["edge_%"]) else 0
        st.markdown(
            f"<div class='card'>"
            f"<b>{row['player']}</b> — {row['prop_type']} "
            f"<span style='color:#BBB'>(Proj: {row['projection']} vs {row['line']})</span><br>"
            f"<div class='edge-bar' style='width:{bar_width}%;'></div>"
            f"<span class='ev'>Edge: {row['edge_%']}%</span>"
            f"</div>",
            unsafe_allow_html=True
        )


# ---------- FOOTER ----------
st.markdown("---")
st.markdown(
    "<div style='color:#888;font-size:14px;'>"
    "Built by <b>Hot Shot Props</b> • AI-powered NBA analytics platform • "
    "Data from NBA API & FanDuel</div>",
    unsafe_allow_html=True
)

