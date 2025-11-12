# -------------------------------------------------
# scripts/apply_predictions.py
# -------------------------------------------------
# Hot Shot Props — AI Prediction Runner
# Runs trained models on today's player feature set,
# compares to sportsbook lines, and saves ranked output
# -------------------------------------------------

import os
import pandas as pd
import numpy as np
from datetime import datetime
from scripts.build_features import build_feature_set
from models.prop_model import predict_props
from scripts.fetch_fanduel import fetch_fanduel_data

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "model_predictions.csv")


# -------------------------------------------------
# Compute edge value
# -------------------------------------------------
def calculate_edge(projection, line):
    """Compute % edge between model projection and sportsbook line."""
    try:
        return round(((projection - line) / line) * 100, 1)
    except Exception:
        return None


# -------------------------------------------------
# Run daily model predictions
# -------------------------------------------------
def run_model_predictions(player_list=None):
    """
    Full end-to-end run:
    1. Build feature set
    2. Predict stats
    3. Merge with live FanDuel props
    4. Compute edges
    5. Save CSV for dashboard
    """
    if player_list is None:
        player_list = [
            "LeBron James", "Luka Doncic", "Jayson Tatum",
            "Nikola Jokic", "Giannis Antetokounmpo",
            "Kevin Durant", "Shai Gilgeous-Alexander",
            "Anthony Davis", "Tyrese Haliburton"
        ]

    print("📦 Building feature set...")
    feature_df = build_feature_set(player_list)
    if feature_df.empty:
        print("⚠️ Feature set is empty.")
        return pd.DataFrame()

    print("🤖 Running AI model predictions...")
    results = []
    for _, row in feature_df.iterrows():
        player_name = row["player"]
        sample = feature_df[feature_df["player"] == player_name]
        preds = predict_props(sample)
        preds["player"] = player_name
        results.append(preds)

    pred_df = pd.concat(results, ignore_index=True)
    print(f"✅ Model generated {len(pred_df)} player-prop projections.")

    # Merge with FanDuel odds
    print("📊 Fetching live FanDuel props...")
    odds_df = fetch_fanduel_data()
    if odds_df.empty:
        print("⚠️ No odds data; skipping edge computation.")
        return pred_df

    odds_df["prop_type"] = odds_df["prop_type"].str.replace("Player ", "").str.replace(" Points", "PTS").str.replace(" Rebounds", "REB").str.replace(" Assists", "AST")
    merged = pd.merge(pred_df, odds_df, on=["player", "prop_type"], how="left")

    # Compute edge
    merged["edge_%"] = merged.apply(lambda r: calculate_edge(r["projection"], r["line"]), axis=1)
    merged = merged.dropna(subset=["edge_%"])
    merged = merged.sort_values("edge_%", ascending=False)

    merged["timestamp"] = datetime.utcnow().isoformat()
    merged.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Predictions + edges saved → {OUTPUT_PATH}")

    return merged


if __name__ == "__main__":
    df = run_model_predictions()
    print(df.head(15))
