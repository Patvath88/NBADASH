# -------------------------------------------------
# scripts/fetch_games.py
# -------------------------------------------------
# Pulls today's NBA schedule + team matchups via nba_api
# Used by dashboard home page for Game Slate
# -------------------------------------------------

import os
import pandas as pd
from datetime import datetime
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.library.parameters import LeagueID

def fetch_games_today():
    """
    Fetch today's NBA games (date = system local time).
    Returns a DataFrame with game_id, teams, and start time.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Fetching NBA games for {today}...")

    try:
        sb = scoreboardv2.ScoreboardV2(
            league_id=LeagueID.nba,
            game_date=today
        )

        games_df = sb.line_score.get_data_frame()
        teams_df = sb.game_header.get_data_frame()

        # Extract key info
        matchups = []
        for _, row in teams_df.iterrows():
            home_team = row["HOME_TEAM_ABBREVIATION"]
            away_team = row["VISITOR_TEAM_ABBREVIATION"]
            game_time = row["GAME_STATUS_TEXT"]
            game_id = row["GAME_ID"]

            matchups.append({
                "game_id": game_id,
                "home_team": home_team,
                "away_team": away_team,
                "game_time": game_time,
                "date": today,
                "spread": None,  # placeholder until we merge odds
                "total": None,
                "status": row["GAME_STATUS_TEXT"]
            })

        df = pd.DataFrame(matchups)
        save_path = os.path.join(os.path.dirname(__file__), "..", "data", "games_today.json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_json(save_path, orient="records", indent=2)
        print(f"✅ {len(df)} games fetched and saved to {save_path}")
        return df

    except Exception as e:
        print(f"❌ Error fetching NBA games: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    df = fetch_games_today()
    if not df.empty:
        print(df.head())
    else:
        print("No NBA games available today.")
