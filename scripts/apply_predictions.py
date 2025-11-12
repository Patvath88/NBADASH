# -------------------------------------------------
# scripts/apply_predictions.py
# -------------------------------------------------
# Hot Shot Props – AI Regression Model for Player Prop Prediction
# Learns from last 10 player games to project next-game stat value
# and calculate betting edges vs sportsbook lines.
# -------------------------------------------------

import os
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from scripts.fetch_player_stats import get_player_stats_summary


# -------------------------------------------------
# HELPER — Build features from last N games
# -------------------------------------------------
def build_recent_features(player_name: str, prop_type: str, n_games: int = 10):
    """Fetch recent logs and return average stat features for model input."""
    logs = get_player_stats_summary(player_name)
    if logs.empty:
        return None

    # Select stat column
    col_map = {
        "PTS": "PTS",
        "REB": "REB",
        "AST": "AST",
        "PRA": None,   # computed manually
        "3PM": "FG3M",
    }
    col = col_map.get(prop_type, None)

    if prop_type == "PRA":
        logs["PRA"] = logs["PTS"] + logs["REB"] + logs["AST"]
        col = "PRA"

    if col not in logs.columns:
        return None

    # Sort by recent games
    logs = logs.sort_values(by="GAME_DATE", ascending=False).head(n_games)
    logs["GAME_DATE"] = pd.to_datetime(logs["GAME_DATE"])

    # Basic rolling metrics
    recent_mean = logs[col].mean()
    recent_std = logs[col].std() if len(logs) > 1 else 0
    last_game = logs[col].iloc[0]

    return {
        "player": player_name,
        "prop_type": prop_type,
        "recent_mean": recent_mean,
        "recent_std": recent_std,
        "last_game": last_game,
        "games_used": len(logs),
    }


# -------------------------------------------------
# MAIN MODEL
# -------------------------------------------------
def run_model_predictions(fanduel_df: pd.DataFrame, games_df: pd.DataFrame = None):
    """
    Train lightweight regression model on recent performance
    and predict expected prop value vs FanDuel line.
    """
    if fanduel_df.empty:
        print("⚠️ No FanDuel data to model.")
        return pd.DataFrame()

    features = []
    for _, row in fanduel_df.iterrows():
        f = build_recent_features(row["player"], row["prop_type"])
        if f:
            features.append(f)

    if not features:
        print("⚠️ No valid feature data found — skipping modeling.")
        return pd.DataFrame()

    feat_df = pd.DataFrame(features)

    # Simple model: Ridge regression on past mean/std to predict next stat
    X = feat_df[["recent_mean", "recent_std", "last_game"]].fillna(0)
    y = feat_df["recent_mean"]  # target is next expected mean stat
    model = Pipeline([
        ("scale", StandardScaler()),
        ("ridge", Ridge(alpha=1.0))
    ])
    model.fit(X, y)
    preds = model.predict(X)

    # Merge predictions back to odds
    out = fanduel_df.merge(feat_df, on=["player", "prop_type"], how="left")
    out["model_projection"] = np.round(preds, 1)
    out["edge_pct"] = np.round(
        np.abs(out["model_projection"] - out["line"]) / out["line"] * 100, 2
    )
    out["expected_value_over"] = (out["model_projection"] - out["line"]) * 1.5
    out["expected_value_under"] = (out["line"] - out["model_projection"]) * 1.5
    out["timestamp"] = datetime.utcnow().isoformat()

    out = out.sort_values("edge_pct", ascending=False).reset_index(drop=True)

    print(f"✅ Built model projections for {len(out)} props.")
    return out


# -------------------------------------------------
# TEST ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    # Quick offline test
    sample = pd.DataFrame([
        {"player": "LeBron James", "prop_type": "PTS", "line": 25.5},
        {"player": "Nikola Jokic", "prop_type": "AST", "line": 9.5},
        {"player": "Jayson Tatum", "prop_type": "REB", "line": 8.5},
    ])
    df = run_model_predictions(sample)
    print(df[["player", "prop_type", "line", "model_projection", "edge_pct"]])
