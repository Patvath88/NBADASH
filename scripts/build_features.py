# -------------------------------------------------
# scripts/build_features.py
# -------------------------------------------------
# Hot Shot Props — Feature Builder
# Combines player game logs + opponent stats into model-ready features
# -------------------------------------------------

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playergamelog, leaguedashteamstats

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "features_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


# -------------------------------------------------
# Fetch player logs + rolling stats
# -------------------------------------------------
def get_recent_logs(player_name: str, season: str = "2024-25"):
    """Return last 20 game logs for a player with rolling averages."""
    pid = None
    for p in players.get_players():
        if player_name.lower() in p["full_name"].lower():
            pid = p["id"]
            break
    if not pid:
        return pd.DataFrame()

    try:
        logs = playergamelog.PlayerGameLog(player_id=pid, season=season).get_data_frames()[0]
        logs["GAME_DATE"] = pd.to_datetime(logs["GAME_DATE"])
        logs = logs.sort_values("GAME_DATE")
        # Rolling features
        for col in ["PTS", "REB", "AST", "FG3M", "MIN"]:
            logs[f"{col}_L5"] = logs[col].rolling(5).mean()
            logs[f"{col}_L10"] = logs[col].rolling(10).mean()
        logs["PRA"] = logs["PTS"] + logs["REB"] + logs["AST"]
        logs["PRA_L5"] = logs["PRA"].rolling(5).mean()
        logs["PRA_L10"] = logs["PRA"].rolling(10).mean()
        return logs.tail(20)
    except Exception as e:
        print(f"⚠️ Failed to get logs for {player_name}: {e}")
        return pd.DataFrame()


# -------------------------------------------------
# Opponent team context
# -------------------------------------------------
def get_team_defense_rank(season="2024-25"):
    """
    Fetch team defensive stats and compute opponent ranks
    (points allowed, rebounds allowed, assists allowed per game)
    """
    try:
        team_stats = leaguedashteamstats.LeagueDashTeamStats(season=season).get_data_frames()[0]
        team_stats = team_stats[["TEAM_ID", "TEAM_NAME", "GP", "PTS", "REB", "AST"]]
        team_stats.rename(columns={"PTS": "PTS_ALLOWED", "REB": "REB_ALLOWED", "AST": "AST_ALLOWED"}, inplace=True)
        # Lower allowed => tougher defense
        for col in ["PTS_ALLOWED", "REB_ALLOWED", "AST_ALLOWED"]:
            team_stats[f"{col}_RANK"] = team_stats[col].rank(ascending=True)
        return team_stats
    except Exception as e:
        print(f"⚠️ Failed to get team defense ranks: {e}")
        return pd.DataFrame()


# -------------------------------------------------
# Build features for all players
# -------------------------------------------------
def build_feature_set(player_list, season="2024-25"):
    """Combine player rolling stats + opponent defensive context."""
    all_rows = []
    team_def = get_team_defense_rank(season)

    for name in player_list:
        logs = get_recent_logs(name, season)
        if logs.empty:
            continue
        last_game = logs.iloc[-1]
        team = last_game["TEAM_ABBREVIATION"]
        opp = last_game["MATCHUP"].split(" ")[-1].replace("@", "").replace("vs.", "")
        opp_row = team_def[team_def["TEAM_NAME"].str.contains(opp, case=False, na=False)]
        row = {
            "player": name,
            "team": team,
            "opponent": opp,
            "PTS_L5": last_game.get("PTS_L5", np.nan),
            "REB_L5": last_game.get("REB_L5", np.nan),
            "AST_L5": last_game.get("AST_L5", np.nan),
            "FG3M_L5": last_game.get("FG3M_L5", np.nan),
            "MIN_L5": last_game.get("MIN_L5", np.nan),
            "PRA_L5": last_game.get("PRA_L5", np.nan),
        }
        if not opp_row.empty:
            row["OPP_PTS_RANK"] = opp_row["PTS_ALLOWED_RANK"].values[0]
            row["OPP_REB_RANK"] = opp_row["REB_ALLOWED_RANK"].values[0]
            row["OPP_AST_RANK"] = opp_row["AST_ALLOWED_RANK"].values[0]
        else:
            row["OPP_PTS_RANK"] = row["OPP_REB_RANK"] = row["OPP_AST_RANK"] = np.nan
        all_rows.append(row)

    df = pd.DataFrame(all_rows)
    save_path = os.path.join(CACHE_DIR, f"features_{datetime.now().strftime('%Y%m%d')}.csv")
    df.to_csv(save_path, index=False)
    print(f"✅ Built feature set for {len(df)} players -> {save_path}")
    return df


if __name__ == "__main__":
    sample_players = ["LeBron James", "Jayson Tatum", "Nikola Jokic"]
    df = build_feature_set(sample_players)
    print(df.head())
