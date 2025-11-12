# -------------------------------------------------
# scripts/fetch_fanduel.py
# -------------------------------------------------
# Hot Shot Props — FanDuel Odds Scraper (Safe + Fallback)
# Ensures odds_snapshot.json is always valid JSON.
# -------------------------------------------------

import os
import json
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
ODDS_PATH = os.path.join(DATA_DIR, "odds_snapshot.json")


def fetch_fanduel_data():
    """Fetch or rebuild FanDuel odds snapshot."""
    print("📊 Fetching FanDuel NBA player props...")

    try:
        # --- Placeholder dataset (replace with Selenium or OddsAPI later) ---
        mock_data = [
            {"player": "LeBron James", "prop_type": "PTS", "line": 25.5, "odds_over": -115, "odds_under": -105},
            {"player": "Jayson Tatum", "prop_type": "REB", "line": 8.5, "odds_over": -110, "odds_under": -110},
            {"player": "Nikola Jokic", "prop_type": "AST", "line": 9.5, "odds_over": -120, "odds_under": 100},
            {"player": "Luka Doncic", "prop_type": "PRA", "line": 48.5, "odds_over": -105, "odds_under": -115},
            {"player": "Stephen Curry", "prop_type": "3PM", "line": 4.5, "odds_over": -125, "odds_under": 105},
        ]
        df = pd.DataFrame(mock_data)
        df["timestamp"] = datetime.utcnow().isoformat()

        # Save JSON snapshot
        df.to_json(ODDS_PATH, orient="records", indent=2)
        print(f"✅ Saved FanDuel odds → {ODDS_PATH}")
        return df

    except Exception as e:
        print(f"⚠️ Error fetching FanDuel data: {e}")
        return pd.DataFrame()


def load_fanduel_snapshot():
    """Loads snapshot safely. If empty/corrupted, rebuilds."""
    if not os.path.exists(ODDS_PATH) or os.path.getsize(ODDS_PATH) < 5:
        print("⚠️ No valid odds file found — rebuilding.")
        return fetch_fanduel_data()

    try:
        with open(ODDS_PATH, "r") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except json.JSONDecodeError:
        print("⚠️ odds_snapshot.json invalid — rebuilding.")
        return fetch_fanduel_data()


if __name__ == "__main__":
    df = load_fanduel_snapshot()
    print(df)
