# -------------------------------------------------
# pages/Player_Props.py
# -------------------------------------------------
# Hot Shot Props – Player Prop Analyzer
# Search any player → show recent stats, hit rates,
# and compare vs today's prop line.
# -------------------------------------------------

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scripts.fetch_player_stats import get_player_stats_summary

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Player Prop Analyzer | Hot Shot Props", page_icon="📊")

# ---------- STYLE ----------
st.markdown("""
<style>
body {background:#121212;color:#EAEAEA;font-family:'Roboto',sans-serif;}
.title {font-size:28px;font-weight:700;color:#FF6F00;text-shadow:0 0 6px #FF9F43;}
.subtext {font-size:15px;color:#BBB;margin-bottom:10px;}
.card {
  background:#1C1C1C;border-radius:12px;padding:18px;margin-bottom:12px;
  box-shadow:0 0 10px rgba(0,0,0,0.35);
}
.metric {font-size:15px;font-weight:600;color:#FF9F43;}
.value {font-size:15px;color:#EAEAEA;}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("<div class='title'>📊 Player Prop Analyzer</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>View player trends, hit rates, and compare to today's prop lines</div>", unsafe_allow_html=True)
st.markdown("---")

# ---------- SIDEBAR INPUTS ----------
player_name = st.sidebar.text_input("Search Player", placeholder="e.g. LeBron James")
prop_type = st.sidebar.selectbox(
    "Prop Type",
    ["Points", "Rebounds", "Assists", "PRA", "3PM"]
)
prop_line = st.sidebar.number_input("Prop Line", min_value=0.0, step=0.5, value=20.5)

# ---------- FETCH & DISPLAY ----------
if player_name:
    with st.spinner(f"Fetching {player_name}'s game logs..."):
        df, summary = get_player_stats_summary(player_name, prop_type, prop_line)

    if df.empty:
        st.warning("No data available for that player.")
        st.stop()

    st.markdown(f"### {summary['player']} — {summary['prop_type']} ({summary['line']})")
    st.markdown(
        f"Average: **{summary['avg']}** &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"L5 Hit Rate: **{summary['hit_rates']['L5']}%**, "
        f"L10: **{summary['hit_rates']['L10']}%**, "
        f"L20: **{summary['hit_rates']['L20']}%**"
    )

    # ---------- LINE CHART ----------
    stat_col = "PRA" if prop_type == "PRA" else prop_type[0:3].upper()
    if stat_col not in df.columns:
        stat_col = "PTS"

    chart = go.Figure()
    chart.add_trace(go.Scatter(
        x=df["GAME_DATE"],
        y=df[stat_col],
        mode="lines+markers",
        name=prop_type,
        line=dict(color="#FF6F00", width=2)
    ))
    chart.add_hline(
        y=prop_line, line_dash="dash", line_color="#888", annotation_text="Prop Line",
        annotation_position="top left"
    )
    chart.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis_title=prop_type,
        xaxis_title="Game Date"
    )
    st.plotly_chart(chart, use_container_width=True)

    # ---------- GAME LOG TABLE ----------
    with st.expander("📅 Last 20 Games"):
        show_cols = ["GAME_DATE", "MATCHUP", "PTS", "REB", "AST", "FG3M", "PRA"]
        for col in show_cols:
            if col not in df.columns:
                df[col] = None
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"]).dt.strftime("%b %d")
        st.dataframe(df[show_cols].sort_values("GAME_DATE", ascending=False), use_container_width=True)
else:
    st.info("Use the sidebar to search a player and view their prop trends.")
