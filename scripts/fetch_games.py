# -------------------------------------------------
# scripts/fetch_games.py  (patched for timeouts)
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
    """Fetch today's NBA games safely (with 15 s timeout)."""
    EST = timezone(timedelta(hours=-5))
    today = datetime.now(EST).strftime("%Y-%m-%d")
    print(f"🏀 Fetching NBA games for {today}...")

    try:
        sb = scoreboardv2.ScoreboardV2(league_id=LeagueID.nba, game_date=today, timeout=15)
        games_df = sb.game_header.get_data_frame()
    except Exception as e:
        print(f"⚠️ Timeout or error fetching games: {e}")
        return pd.DataFrame()

    if games_df.empty:
        print("⚠️ No games returned by API.")
        return pd.DataFrame()

    game_rows = [
        {
            "game_id": r["GAME_ID"],
            "home_team": r["HOME_TEAM_ABBREVIATION"],
            "away_team": r["VISITOR_TEAM_ABBREVIATION"],
            "game_time": r["GAME_STATUS_TEXT"],
            "status": r["GAME_STATUS_TEXT"],
            "date": today,
        }
        for _, r in games_df.iterrows()
    ]

    df = pd.DataFrame(game_rows)
    df.to_json(GAMES_PATH, orient="records", indent=2)
    print(f"✅ Saved {len(df)} games → {GAMES_PATH}")
    return df
