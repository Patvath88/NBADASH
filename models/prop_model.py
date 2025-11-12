# -------------------------------------------------
# models/prop_model.py
# -------------------------------------------------
# Hot Shot Props — AI Projection Model
# Builds and applies predictive models for NBA player props
# -------------------------------------------------

import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

MODEL_DIR = os.path.join(os.path.dirname(__file__))
os.makedirs(MODEL_DIR, exist_ok=True)


# -------------------------------------------------
# Utility: prepare features for regression
# -------------------------------------------------
def prepare_training_data(df: pd.DataFrame, target_col: str):
    """
    Given a DataFrame of player game logs, create features for model training.
    target_col = 'PTS', 'REB', 'AST', 'PRA', or 'FG3M'
    """
    df = df.copy()
    if df.empty or target_col not in df.columns:
        raise ValueError(f"Missing target column: {target_col}")

    # Basic rolling features
    df["PTS_L5"] = df["PTS"].rolling(5).mean()
    df["REB_L5"] = df["REB"].rolling(5).mean()
    df["AST_L5"] = df["AST"].rolling(5).mean()
    df["FG3M_L5"] = df["FG3M"].rolling(5).mean()
    df["MIN_L5"] = df["MIN"].rolling(5).mean()

    df["PRA"] = df["PTS"] + df["REB"] + df["AST"]

    # Drop missing rows from rolling
    df = df.dropna()

    # Target and features
    y = df[target_col]
    X = df[["PTS_L5", "REB_L5", "AST_L5", "FG3M_L5", "MIN_L5", "PRA"]]

    return X, y


# -------------------------------------------------
# Model Training
# -------------------------------------------------
def train_prop_model(df: pd.DataFrame, target_col: str, save=True):
    """
    Trains and saves a model for the given stat type.
    """
    X, y = prepare_training_data(df, target_col)

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBRegressor(
        n_estimators=300,
        learning_rate=0.08,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.9,
        random_state=42
    )

    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    preds = model.predict(X_val)
    mae = mean_absolute_error(y_val, preds)

    if save:
        path = os.path.join(MODEL_DIR, f"{target_col}_model.joblib")
        joblib.dump(model, path)
        print(f"✅ {target_col} model trained & saved — MAE: {mae:.2f}")

    return model, mae


# -------------------------------------------------
# Load existing or train fresh
# -------------------------------------------------
def load_or_train(df: pd.DataFrame, target_col: str):
    """
    Loads model from disk if it exists; otherwise trains it.
    """
    path = os.path.join(MODEL_DIR, f"{target_col}_model.joblib")
    if os.path.exists(path):
        print(f"📂 Loading saved model for {target_col}")
        model = joblib.load(path)
        return model
    else:
        return train_prop_model(df, target_col)


# -------------------------------------------------
# Prediction for new games
# -------------------------------------------------
def predict_props(df: pd.DataFrame):
    """
    Given a fresh player dataset (latest rolling stats),
    predict PTS/REB/AST/PRA/3PM.
    Returns DataFrame with projected stats.
    """
    results = []

    stat_cols = ["PTS", "REB", "AST", "PRA", "FG3M"]
    for stat in stat_cols:
        try:
            model = load_or_train(df, stat)
            X, _ = prepare_training_data(df, stat)
            pred = model.predict(X.tail(1))[0]
            results.append({"prop_type": stat, "projection": round(pred, 1)})
        except Exception as e:
            print(f"⚠️ Prediction failed for {stat}: {e}")

    return pd.DataFrame(results)


if __name__ == "__main__":
    # Demo using sample data
    sample = pd.DataFrame({
        "PTS": np.random.randint(10, 35, 30),
        "REB": np.random.randint(2, 12, 30),
        "AST": np.random.randint(1, 10, 30),
        "FG3M": np.random.randint(0, 6, 30),
        "MIN": np.random.randint(25, 38, 30)
    })

    out = predict_props(sample)
    print(out)
