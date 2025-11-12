# scripts/apply_predictions.py
import pandas as pd
import numpy as np

def run_model_predictions(odds_df: pd.DataFrame, games_df: pd.DataFrame) -> pd.DataFrame:
    """Simple random model to prove dashboard flow."""
    if odds_df.empty:
        return pd.DataFrame()
    df = odds_df.copy()
    np.random.seed(42)
    df["model_projection"] = np.random.uniform(0, 1, len(df))
    df["edge_pct"] = np.random.uniform(0, 0.3, len(df))
    df["expected_value_over"] = np.random.uniform(-0.05, 0.1, len(df))
    df["expected_value_under"] = np.random.uniform(-0.05, 0.1, len(df))
    return df
