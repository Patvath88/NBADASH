# -------------------------------------------------
# scripts/apply_predictions.py
# -------------------------------------------------
# Hot Shot Props – AI Model Prediction Stub
# Applies simple baseline predictions & edges to FanDuel data.
# You can later replace this with your trained ML model.
# -------------------------------------------------

import pandas as pd
import numpy as np
from datetime import datetime

# -------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------
def run_model_predictions(fanduel_df: pd.DataFrame, games_df: pd.DataFrame = None):
    """
    Takes FanDuel props and (optionally) today's games,
    applies a mock prediction model, and returns DataFrame
    with expected values, model projections, and edge %.
    """

    if fanduel_df is None or fanduel_df.empty:
        print("⚠️ No FanDuel data provided — skipping predictions.")
        return pd.DataFrame()

    # --- Basic placeholder prediction logic ---
    df = fanduel_df.copy()
    np.random.seed(42)

    # Randomized prediction logic (to simulate model output)
    df["model_projection"] = df["line"] + np.random.uniform(-3, 3, len(df))
    df["expected_value_over"] = (df["model_projection"] - df["line"]) * 1.5
    df["expected_value_under"] = (df["line"] - df["model_projection"]) * 1.5

    # Edge % based on how far model deviates from line
    df["edge_pct"] = np.round(
        np.abs(df["model_projection"] - df["line"]) / df["line"] * 100, 2
    )

    # Sort descending by edge for dashboard display
    df = df.sort_values(by="edge_pct", ascending=False).reset_index(drop=True)
    df["timestamp"] = datetime.utcnow().isoformat()

    print(f"✅ Generated predictions for {len(df)} props.")
    return df


# -------------------------------------------------
# TEST ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    # Example test run
    test_data = pd.DataFrame({
        "player": ["LeBron James", "Jayson Tatum", "Nikola Jokic"],
        "prop_type": ["PTS", "REB", "AST"],
        "line": [25.5, 8.5, 9.5],
        "odds_over": [-115, -110, -120],
        "odds_under": [-105, -110, 100],
    })
    result = run_model_predictions(test_data)
    print(result.head())
