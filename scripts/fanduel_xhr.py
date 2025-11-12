# scripts/fanduel_xhr.py
# Lightweight FanDuel player prop scraper via direct XHR JSON capture

import requests, json, pandas as pd, time
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "odds_snapshot.json"
SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

def fetch_fanduel_props_xhr():
    """Fetch props from known FanDuel content-service endpoints (no Selenium)."""
    urls = [
        "https://sportsbook.fanduel.com/api/content-service/v1/sportsbook-content/navigation?regionCode=US&locale=en-US",
        "https://sportsbook.fanduel.com/api/content-service/v1/sportsbook-content/competitions?regionCode=US&sportCode=BASKETBALL_NBA&locale=en-US",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
    }
    records = []
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                data = r.json()
                # Shallow scan for player markets
                for k, v in json.dumps(data).split("},"):
                    if any(t in k.lower() for t in ["player", "prop", "market"]):
                        records.append({"raw": k})
        except Exception:
            continue
    df = pd.DataFrame(records)
    df["player"] = df["raw"].str.extract(r"([A-Z][a-z]+\s[A-Z][a-z]+)")
    df["prop_type"] = "UNKNOWN"
    df["line"] = None
    df["odds"] = None
    df["team"] = None
    df["game"] = None
    df["bookmaker"] = "fanduel"

    snap = {"timestamp": time.time(), "count": len(df), "records": df.fillna("").to_dict(orient="records")}
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2)
    return df
