# -------------------------------------------------
# scripts/fetch_fanduel.py
# -------------------------------------------------
# Scrapes NBA player props from FanDuel (main U.S. site)
# Falls back to OddsAPI or PrizePicks if FanDuel fails
# -------------------------------------------------

import json
import time
import random
import os
import sys
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Import fallbacks dynamically
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)
try:
    from fetch_oddsapi import fetch_oddsapi_data
    from fetch_prizepicks import fetch_prizepicks_data
except ImportError:
    fetch_oddsapi_data = lambda: pd.DataFrame()
    fetch_prizepicks_data = lambda: pd.DataFrame()


def init_driver():
    """Launch headless Chrome for scraping."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)


def parse_fanduel_props(driver):
    """
    Navigate through FanDuel NBA player props and extract data.
    Returns list of dicts.
    """
    url = "https://sportsbook.fanduel.com/sports/navigation/nba"
    driver.get(url)
    time.sleep(random.uniform(6, 9))  # allow JS to render

    props_data = []

    try:
        prop_sections = driver.find_elements(By.CSS_SELECTOR, "section[aria-label*='Player Props']")
        if not prop_sections:
            print("No Player Props sections found — possible DOM change.")
            return []

        for section in prop_sections:
            try:
                title_el = section.find_element(By.CSS_SELECTOR, "h3")
                prop_type = title_el.text.strip()
            except Exception:
                prop_type = "Unknown"

            players = section.find_elements(By.CSS_SELECTOR, "[class*='event-cell']")
            for player in players:
                try:
                    name_el = player.find_element(By.CSS_SELECTOR, "[class*='participant']")
                    name = name_el.text.strip()
                    line_el = player.find_element(By.CSS_SELECTOR, "[class*='outcome-cell__line']")
                    line_val = line_el.text.strip().replace("O", "").replace("U", "").replace("½", ".5")
                    odds_els = player.find_elements(By.CSS_SELECTOR, "[class*='outcome-cell__odds']")

                    odds_over, odds_under = None, None
                    if len(odds_els) >= 2:
                        odds_over = odds_els[0].text.strip()
                        odds_under = odds_els[1].text.strip()

                    props_data.append({
                        "player": name,
                        "prop_type": prop_type,
                        "line": line_val,
                        "odds_over": odds_over,
                        "odds_under": odds_under,
                        "source": "FanDuel",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    continue

    except Exception as e:
        print(f"Error parsing FanDuel page: {e}")

    return props_data


def fetch_fanduel_data():
    """Main wrapper with fallback logic."""
    try:
        driver = init_driver()
        props_data = parse_fanduel_props(driver)
        driver.quit()
        if len(props_data) < 10:
            raise ValueError("FanDuel returned too few props.")
        df = pd.DataFrame(props_data)
        df["line"] = pd.to_numeric(df["line"], errors="coerce")
        save_path = os.path.join(os.path.dirname(__file__), "..", "data", "odds_snapshot.json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_json(save_path, orient="records", indent=2)
        print(f"✅ FanDuel scrape success — {len(df)} props saved.")
        return df
    except (WebDriverException, TimeoutException, ValueError) as e:
        print(f"⚠️ FanDuel scrape failed: {e}")
        # Try fallback
        try:
            print("➡️ Falling back to OddsAPI...")
            df = fetch_oddsapi_data()
            if not df.empty:
                return df
            print("➡️ Falling back to PrizePicks...")
            df = fetch_prizepicks_data()
            return df
        except Exception as e2:
            print(f"All fallbacks failed: {e2}")
            return pd.DataFrame()


if __name__ == "__main__":
    df = fetch_fanduel_data()
    if not df.empty:
        print(df.head())
    else:
        print("❌ No data available from any source.")
