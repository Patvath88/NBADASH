import pandas as pd
import numpy as np

def run_model_predictions(props_df: pd.DataFrame, games_df: pd.DataFrame):
    """Mock AI predictions combining props and games."""
    if props_df.empty or games_df.empty:
        return pd.DataFrame()

    # Example simple prediction model placeholder
    props_df = props_df.copy()
    props_df["predicted_value"] = np.random.uniform(-10, 10, len(props_df)).round(2)
    props_df["edge_value"] = (props_df["predicted_value"] - props_df["line"]).round(2)
    props_df["edge_flag"] = np.where(props_df["edge_value"] > 0, "🔥 Over", "❄️ Under")

    return props_df[["player", "prop_type", "line", "odds", "predicted_value", "edge_value", "edge_flag", "game"]]
