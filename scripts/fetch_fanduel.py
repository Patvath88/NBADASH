# scripts/fetch_fanduel.py
# Simple FanDuel NBA prop scraper (non-Selenium, XHR-based fallback)

import requests, pandas as pd, json, time
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "fanduel_props.json"
SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

def fetch_fanduel_props():
    """Fetches lightweight NBA player props from FanDuel XHR endpoints."""
    urls = [
        "https://sportsbook.fanduel.com/api/content-service/v1/sportsbook-content/navigation?regionCode=US&locale=en-US",
        "https://sportsbook.fanduel.com/api/content-service/v1/sportsbook-content/competitions?regionCode=US&sportCode=BASKETBALL_NBA&locale=en-US",
    ]
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    records = []

    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                data = r.json()
                jtxt = json.dumps(data).lower()
                for word in ["player", "points", "rebounds", "assists"]:
                    if word in jtxt:
                        records.append({"prop_type": word})
        except Exception:
            continue

    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame([{"prop_type": "No Data", "player": None}])
    df["bookmaker"] = "FanDuel"
    df["timestamp"] = time.time()

    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, indent=2)
    return df
