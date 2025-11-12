# scripts/fetch_fanduel.py
"""
Fetch FanDuel NBA player props using Selenium + Chrome.

Outputs:
 - returns a pandas.DataFrame with columns:
    ['player', 'prop_type', 'line', 'odds', 'team', 'game', 'bookmaker']
 - writes JSON snapshot to ../data/odds_snapshot.json

Notes:
 - Requires: selenium, webdriver-manager, beautifulsoup4, pandas
 - Works headless; set environment variables CHROME_BINARY and/or CHROMEDRIVER_PATH
   if you need to use a custom chromium/chrome binary or driver on your VPS.
"""

import os
import json
import time
import logging
from typing import Tuple, List, Dict
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# webdriver-manager to auto-install driver
from webdriver_manager.chrome import ChromeDriverManager

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# output path (relative to repo root)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ODDS_SNAPSHOT_PATH = DATA_DIR / "odds_snapshot.json"

# FanDuel NBA player props landing pages to try (may change over time)
FANDUEL_NBA_PROPS_URLS = [
    # common structure for FanDuel sport pages; one of these will usually redirect or load the player props
    "https://www.fanduel.com/sports/basketball/nba/player-props",
    "https://www.fanduel.com/en/sports/basketball/nba/player-props",  # alt
    "https://www.fanduel.com/sports",  # fallback: open main and then nav (we try direct first)
]

# Selenium friendly chrome options for headless cloud runs
DEFAULT_CHROME_OPTIONS = [
    "--headless=new",  # newer headless mode (better rendering). Use "--headless" if crash.
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-extensions",
    "--disable-blink-features=AutomationControlled",
    "--disable-background-networking",
    "--disable-client-side-phishing-detection",
    "--disable-default-apps",
    "--disable-sync",
    "--metrics-recording-only",
    "--disable-setuid-sandbox",
    "--window-size=1920,1080",
    # optional: imitate headers via user agent
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

def _init_driver(timeout: int = 30) -> webdriver.Chrome:
    """
    Create and return a configured Selenium Chrome webdriver (headless).
    Respects env vars:
      - CHROME_BINARY: path to chrome/chromium binary
      - CHROMEDRIVER_PATH: path to chromedriver binary (skip webdriver-manager)
    """
    chrome_options = webdriver.ChromeOptions()
    for opt in DEFAULT_CHROME_OPTIONS:
        chrome_options.add_argument(opt)

    chrome_options.add_argument(f"--user-agent={DEFAULT_USER_AGENT}")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Optional: set binary location if provided (e.g., in some containers)
    chrome_binary = os.environ.get("CHROME_BINARY")  # e.g., "/usr/bin/chromium-browser"
    if chrome_binary:
        chrome_options.binary_location = chrome_binary
        logger.info(f"Using CHROME_BINARY: {chrome_binary}")

    # Try using webdriver-manager unless CHROMEDRIVER_PATH specified
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    if chromedriver_path:
        logger.info(f"Using CHROMEDRIVER_PATH: {chromedriver_path}")
        service = Service(chromedriver_path)
    else:
        logger.info("Installing/using ChromeDriver via webdriver-manager")
        # This will download the appropriate chromedriver into cache if necessary
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout)
        # try to reduce detection
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """
        })
        return driver
    except WebDriverException as e:
        logger.exception("Error creating Chrome WebDriver: %s", e)
        raise

def _wait_for_props_to_load(driver: webdriver.Chrome, timeout: int = 20) -> str:
    """
    Wait for main content to load and return page source.
    We wait for common selectors used by FanDuel's UI: market cards, player name nodes, etc.
    """
    wait = WebDriverWait(driver, timeout)
    possible_selectors = [
        # FanDuel often uses elements with 'market' or 'event' or 'player' in data-testid/class
        (By.CSS_SELECTOR, "[data-testid*='player-prop']"),
        (By.CSS_SELECTOR, "[data-testid*='market']"),
        (By.CSS_SELECTOR, ".event-market"),  # fallback class
        (By.CSS_SELECTOR, ".market"),  # very generic fallback
        (By.CSS_SELECTOR, "div[data-testid]"),
    ]

    for by, sel in possible_selectors:
        try:
            logger.debug("Waiting for selector: %s %s", by, sel)
            wait.until(EC.presence_of_element_located((by, sel)))
            time.sleep(0.5)  # small extra buffer
            page_html = driver.page_source
            return page_html
        except TimeoutException:
            continue

    # If none matched, return raw page source (still may have content)
    return driver.page_source

def _parse_props_from_html(html: str) -> List[Dict]:
    """
    Parse props from page HTML using BeautifulSoup.
    Because FanDuel markup changes, this function attempts multiple heuristics:
     - look for market cards with player names and outcomes
     - look for outcome lists with 'name', 'point', 'price' text
    Returns list of dicts: {player, prop_type, line, odds, team, game, bookmaker}
    """
    soup = BeautifulSoup(html, "html.parser")
    records = []

    # Heuristic 1: look for elements that look like a player-market block
    # E.g., elements containing player name, market name, and outcomes
    # We'll look for tags with keywords in class or data-testid
    market_nodes = soup.find_all(
        lambda tag: (
            tag.name in ["div", "section"]
            and (
                (tag.get("data-testid") and "market" in tag.get("data-testid").lower())
                or ("market" in (tag.get("class") or []))
                or ("player" in (tag.get("class") or []))
            )
        )
    )
    # If we found candidate market nodes, try parse them
    logger.debug("Found %s candidate market nodes", len(market_nodes))
    if market_nodes:
        for m in market_nodes:
            # fetch market label
            prop_type = None
            # try common places
            header = m.find(lambda t: t.name in ["h3", "h4", "h5", "span"] and t.text and len(t.text) < 60)
            if header and header.text:
                prop_type = header.text.strip()

            # find outcome entries inside market
            outcomes = m.find_all(lambda t: t.name in ["button", "div", "li", "span"] and t.text and "%" not in t.text)
            for out in outcomes:
                text = out.get_text(separator="|").strip()
                # heuristics: text often looks like "Player Name — OVER 21.5 (+120)" or "L. James 24.5"
                parts = [p.strip() for p in text.split("|") if p.strip()]
                if not parts:
                    continue
                # try to identify player name and line/odds
                # look for numbers (point/line)
                player = None
                line = None
                odds = None
                # find token with parentheses for odds like (+120)
                for tok in parts[::-1]:
                    if "(" in tok and ")" in tok:
                        odds = tok.strip()
                        break
                # find part with a decimal number
                for tok in parts:
                    if any(ch.isdigit() for ch in tok):
                        # token with number, treat as line
                        if "." in tok or tok.strip().replace("+","").replace("-","").replace("O","").replace("U","").isdigit():
                            # crude
                            line = tok
                            break
                # first token as player candidate
                player = parts[0] if parts else None

                records.append({
                    "player": player,
                    "prop_type": prop_type or "UNKNOWN",
                    "line": line,
                    "odds": odds,
                    "team": None,
                    "game": None,
                    "bookmaker": "fanduel",
                })

    # Heuristic 2: look for script tags with JSON data (FanDuel sometimes injects JSON)
    # Search for any <script> that contains "props" or "playerProps" keywords
    scripts = soup.find_all("script")
    for s in scripts:
        if not s.string:
            continue
        txt = s.string
        if "player" in txt.lower() and ("price" in txt.lower() or "point" in txt.lower() or "outcome" in txt.lower()):
            # try to json extract
            try:
                # find first { ... } substring and parse JSON (risky)
                start = txt.find("{")
                end = txt.rfind("}") + 1
                candidate = txt[start:end]
                parsed = json.loads(candidate)
                # attempt to walk parsed structure for props
                # many different shapes possible; we attempt shallow search
                def _walk_for_props(obj):
                    if isinstance(obj, dict):
                        if {"name", "price"}.issubset(set(obj.keys())) or {"name", "point", "price"}.issubset(set(obj.keys())):
                            player_name = obj.get("name")
                            line = obj.get("point") or obj.get("line") or None
                            price = obj.get("price") or obj.get("odds") or None
                            records.append({
                                "player": player_name,
                                "prop_type": obj.get("market") or obj.get("prop_type") or "UNKNOWN",
                                "line": line,
                                "odds": price,
                                "team": obj.get("team"),
                                "game": obj.get("game"),
                                "bookmaker": "fanduel",
                            })
                        for v in obj.values():
                            _walk_for_props(v)
                    elif isinstance(obj, list):
                        for v in obj:
                            _walk_for_props(v)
                _walk_for_props(parsed)
            except Exception:
                # ignore malformed JSON
                continue

    # Deduplicate minimal records and return
    # Clean records: normalize empty strings to None
    cleaned = []
    seen = set()
    for r in records:
        key = (r.get("player"), r.get("prop_type"), str(r.get("line")), str(r.get("odds")))
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({
            "player": r.get("player"),
            "prop_type": r.get("prop_type"),
            "line": r.get("line"),
            "odds": r.get("odds"),
            "team": r.get("team"),
            "game": r.get("game"),
            "bookmaker": r.get("bookmaker", "fanduel"),
        })
    return cleaned

def fetch_fanduel_props(max_attempts: int = 2, wait_between_attempts: int = 2) -> pd.DataFrame:
    """
    Main entry. Attempts to open FanDuel player-props pages and scrape props.
    Returns a pandas DataFrame and writes odds snapshot JSON to data folder.
    """
    driver = None
    last_exception = None
    scraped = []

    try:
        driver = _init_driver()

        for url in FANDUEL_NBA_PROPS_URLS:
            attempt = 0
            while attempt < max_attempts:
                try:
                    logger.info("Opening FanDuel URL: %s (attempt %d)", url, attempt + 1)
                    driver.get(url)
                    # allow dynamic content time to load (adjust if slower)
                    html = _wait_for_props_to_load(driver, timeout=20)
                    logger.debug("Page loaded; parsing HTML length=%d", len(html or ""))
                    parsed = _parse_props_from_html(html)
                    if parsed:
                        logger.info("Parsed %d prop records from %s", len(parsed), url)
                        scraped.extend(parsed)
                        break  # stop retrying this url if we found data
                    else:
                        logger.warning("No parsable props found on page; retrying...")
                        attempt += 1
                        time.sleep(wait_between_attempts)
                except Exception as e:
                    last_exception = e
                    logger.exception("Error scraping %s: %s", url, e)
                    attempt += 1
                    time.sleep(wait_between_attempts)

            # if we successfully scraped something, we can optionally stop
            if scraped:
                break

        # fallback: if nothing scraped, try searching for inline endpoints or alternative page interactions
        if not scraped:
            logger.warning("No props scraped from primary pages. Trying an alternate JS-render fallback.")
            # maybe FanDuel requires opening the sport page then clicking to props. As a last effort we return empty
            # Or you can extend here to implement driver.find_element(...) clicks to navigate UI
            # For now we return empty DataFrame
            scraped = []

        # prepare DataFrame
        df = pd.DataFrame(scraped)
        if df.empty:
            logger.info("No FanDuel props scraped; returning empty DataFrame.")
        else:
            # normalize some fields
            df["player"] = df["player"].astype("string")
            df["prop_type"] = df["prop_type"].astype("string")
            df["line"] = df["line"].astype("string")
            df["odds"] = df["odds"].astype("string")
            df["bookmaker"] = df.get("bookmaker", "fanduel")

        # Save JSON snapshot
        snapshot = {
            "timestamp": int(time.time()),
            "readable_time": datetime.utcnow().isoformat() + "Z",
            "source": "fanduel",
            "count": len(df),
            "records": df.fillna("").to_dict(orient="records") if not df.empty else [],
        }
        with open(ODDS_SNAPSHOT_PATH, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, ensure_ascii=False, indent=2)
        logger.info("Saved FanDuel odds snapshot to %s", ODDS_SNAPSHOT_PATH)

        return df

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == "__main__":
    # quick test run when invoked directly
    try:
        df = fetch_fanduel_props()
        print("Scraped rows:", len(df))
        print(df.head(20).to_dict(orient="records"))
    except Exception as e:
        logger.exception("Error running fetch_fanduel_props: %s", e)
