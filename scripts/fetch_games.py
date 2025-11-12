# -------------------------------------------------
# scripts/fetch_games.py  — Robust live version
# -------------------------------------------------
import os, json, pandas as pd
from datetime import datetime, timedelta, timezone
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.library.parameters import LeagueID

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
GAMES_PATH = os.path.join(DATA_DIR, "games_today.json")


def fetch_games_today():
    """Always fetch games for the current Eastern date and verify result."""
    EST = timezone(timedelta(hours=-5))
    today_est = datetime.now(EST).strftime("%Y-%m-%d")
    print(f"🏀 Fetching NBA games for {today_est}...")

    try:
        sb = scoreboardv2.ScoreboardV2(league_id=LeagueID.nba, game_date=today_est, timeout=45)
        games_df = sb.game_header.get_data_frame()
    except Exception as e:
        print(f"⚠️ Error contacting NBA API: {e}")
        return pd.DataFrame()

    if games_df.empty:
        print("⚠️ NBA API returned no games — possible rate-limit or wrong date.")
        # quick retry 12h earlier (covers late-night games)
        try:
            alt_date = (datetime.now(EST) - timedelta(hours=12)).strftime("%Y-%m-%d")
            sb = scoreboardv2.ScoreboardV2(league_id=LeagueID.nba, game_date=alt_date, timeout=45)
            games_df = sb.game_header.get_data_frame()
            print(f"🔁 Retried for {alt_date}: {len(games_df)} games")
        except Exception:
            pass

    if games_df.empty:
        return pd.DataFrame()

    game_rows = [
        dict(
            game_id=r["GAME_ID"],
            home_team=r["HOME_TEAM_ABBREVIATION"],
            away_team=r["VISITOR_TEAM_ABBREVIATION"],
            game_time=r["GAME_STATUS_TEXT"],
            status=r["GAME_STATUS_TEXT"],
            date=today_est,
        )
        for _, r in games_df.iterrows()
    ]

    df = pd.DataFrame(game_rows)
    df.to_json(GAMES_PATH, orient="records", indent=2)
    print(f"✅ Saved {len(df)} games → {GAMES_PATH}")
    return df


def load_games_snapshot():
    """Load cached games; refetch if file empty."""
    if not os.path.exists(GAMES_PATH) or os.path.getsize(GAMES_PATH) < 10:
        return fetch_games_today()
    try:
        with open(GAMES_PATH, "r") as f:
            return pd.DataFrame(json.load(f))
    except Exception:
        return fetch_games_today()
