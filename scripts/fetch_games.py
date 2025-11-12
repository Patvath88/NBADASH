# -------------------------------------------------
# scripts/fetch_games.py
# -------------------------------------------------
# Fetches today's NBA games (UTC-safe) and saves JSON
# -------------------------------------------------

import os
import json
import pandas as pd
from datetime import datetime, timedelta, timezone
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.library.parameters import LeagueID

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
GAMES_PATH = os.path.join(DATA_DIR, "games_today.json")


def fetch_games_today():
    """Fetch today's NBA games and store valid JSON."""
    EST = timezone(timedelta(hours=-5))
    today = datetime.now(EST).strftime("%Y-%m-%d")
    print(f"🏀 Fetching NBA games for {today}...")

    try:
        sb = scoreboardv2.ScoreboardV2(league_id=LeagueID.nba, game_date=today)
        games_df = sb.game_header.get_data_frame()

        if games_df.empty:
            print("⚠️ No NBA games found (API returned empty).")
            games_df = pd.DataFrame(columns=["game_id", "home_team", "away_team", "game_time"])

        game_rows = []
        for _, row in games_df.iterrows():
            game_rows.append({
                "game_id": row["GAME_ID"],
                "home_team": row["HOME_TEAM_ABBREVIATION"],
                "away_team": row["VISITOR_TEAM_ABBREVIATION"],
                "game_time": row["GAME_STATUS_TEXT"],
                "status": row["GAME_STATUS_TEXT"],
                "date": today
            })

        df = pd.DataFrame(game_rows)
        df.to_json(GAMES_PATH, orient="records", indent=2)
        print(f"✅ Saved {len(df)} games → {GAMES_PATH}")
        return df

    except Exception as e:
        print(f"⚠️ Error fetching games: {e}")
        return pd.DataFrame()


def load_games_snapshot():
    """Safe loader with auto rebuild if file invalid or empty."""
    if not os.path.exists(GAMES_PATH) or os.path.getsize(GAMES_PATH) < 5:
        print("⚠️ No valid games file — rebuilding.")
        return fetch_games_today()

    try:
        with open(GAMES_PATH, "r") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except json.JSONDecodeError:
        print("⚠️ games_today.json invalid — rebuilding.")
        return fetch_games_today()


if __name__ == "__main__":
    df = load_games_snapshot()
    print(df)
