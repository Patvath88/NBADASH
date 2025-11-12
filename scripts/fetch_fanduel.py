# -------------------------------------------------
# scripts/fetch_fanduel.py
# -------------------------------------------------
# Hot Shot Props – FanDuel Odds Scraper (Clean Build)
# Fetches NBA player props from FanDuel API or placeholder source
# and saves as JSON for dashboard consumption.
# -------------------------------------------------

import os
import json
import pandas as pd
from datetime import datetime

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
ODDS_PATH = os.path.join(DATA_DIR, "odds_snapshot.json")


# -------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------
def fetch_fanduel_data():
    """
    Fetches NBA player prop odds.
    For now, this uses a placeholder static structure (for live apps, 
    replace with your Selenium or OddsAPI scraper).
    Always returns a valid DataFrame and saves odds_snapshot.json.
    """
    print("📊 Fetching FanDuel NBA player props...")

    try:
        # TODO: Replace this mock data block with your live API/Selenium scraper.
        mock_data = [
            {"player": "LeBron James", "prop_type": "PTS", "line": 25.5, "odds_over": -115, "odds_under": -105},
            {"player": "Jayson Tatum", "prop_type": "REB", "line": 8.5, "odds_over": -110, "odds_under": -110},
            {"player": "Nikola Jokic", "prop_type": "AST", "line": 9.5, "odds_over": -120, "odds_under": +100},
            {"player": "Luka Doncic", "prop_type": "PRA", "line": 48.5, "odds_over": -105, "odds_under": -115},
            {"player": "Steph Curry", "prop_type": "3PM", "line": 4.5, "odds_over": -125, "odds_under": +105},
        ]

        df = pd.DataFrame(mock_data)

        # Timestamp metadata
        df["timestamp"] = datetime.utcnow().isoformat()

        # Save as JSON (always valid JSON)
        df.to_json(ODDS_PATH, orient="records", indent=2)
        print(f"✅ Saved FanDuel odds snapshot → {ODDS_PATH}")
        return df

    except Exception as e:
        print(f"⚠️ Error fetching FanDuel data: {e}")
        # If odds file exists and is valid, return it as fallback
        if os.path.exists(ODDS_PATH) and os.path.getsize(ODDS_PATH) > 5:
            try:
                with open(ODDS_PATH, "r") as f:
                    return pd.DataFrame(json.load(f))
            except Exception:
                pass
        return pd.DataFrame()


# -------------------------------------------------
# SAFE LOADER
# -------------------------------------------------
def load_odds_snapshot():
    """
    Load the most recent odds snapshot.
    If the file is empty or invalid, automatically rebuilds it.
    """
    if not os.path.exists(ODDS_PATH) or os.path.getsize(ODDS_PATH) < 5:
        print("⚠️ No valid odds file found — refetching...")
        return fetch_fanduel_data()

    try:
        with open(ODDS_PATH, "r") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except json.JSONDecodeError:
        print("⚠️ odds_snapshot.json corrupted — refetching...")
        return fetch_fanduel_data()


# -------------------------------------------------
# ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    df = fetch_fanduel_data()
    print(df)
