"""Fetch tickers from Polygon and write them to CSV.

This module is organized with small functions and a CLI entrypoint.
Usage examples:
    python script.py                 # runs with env POLYGON_API_KEY
    python script.py --output out.csv --limit 500
    python script.py --use-sample    # write a small sample CSV without calling the API
"""

from __future__ import annotations

import csv
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

try:
    import requests
except Exception as exc:  # pragma: no cover - runtime env may not have requests
    requests = None  # type: ignore

from dotenv import load_dotenv


load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
SAMPLE_TICKERS: List[Dict[str, Any]] = [
    {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "market": "stocks",
        "locale": "us",
        "primary_exchange": "XNAS",
        "active": True,
    }
]


def ensure_api_key(url: str, api_key: Optional[str]) -> str:
    """Append apiKey only if it's not already in the URL and an API key is provided."""
    if not api_key:
        return url
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "apiKey" not in qs:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}apiKey={api_key}"
    return url


def fetch(url: str, session: Any, api_key: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch a single page from Polygon with basic retry and rate-limit handling.

    Returns the parsed JSON (dict) when successful, or None on unrecoverable error.
    """
    if requests is None:
        raise RuntimeError("requests library is not installed")

    url = ensure_api_key(url, api_key)
    while True:
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 401:
                logging.error("Unauthorized (401). Check your API key.")
                return None
            if r.status_code != 200:
                logging.warning("HTTP %s: retrying in 10s...", r.status_code)
                time.sleep(10)
                continue

            data = r.json()
            if "results" in data:
                return data

            if isinstance(data, dict) and data.get("error", "").startswith("You've exceeded the maximum requests"):
                logging.info("Rate limit hit — waiting 65 seconds...")
                time.sleep(65)
                continue

            logging.warning("Unexpected response: %s", data)
            return None

        except requests.exceptions.RequestException as exc:
            logging.warning("Network error: %s — retrying in 20s...", exc)
            time.sleep(20)


def fetch_all_tickers(limit: int = 1000, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch all tickers (iterating pages) and return a list of dicts.

    If the requests library isn't available or an API key isn't provided, this
    function can be skipped by using the --use-sample flag in the CLI.
    """
    if requests is None:
        raise RuntimeError("requests library is not available in this environment")

    session = requests.Session()
    tickers: List[Dict[str, Any]] = []

    base = (
        "https://api.polygon.io/v3/reference/tickers?"
        f"market=stocks&active=true&order=asc&limit={limit}&sort=ticker"
    )

    data = fetch(base, session, api_key)
    if data:
        tickers.extend(data.get("results", []))

    while data and data.get("next_url"):
        logging.info("Fetching: %s", data["next_url"])
        data = fetch(data["next_url"], session, api_key)
        if data:
            tickers.extend(data.get("results", []))

    return tickers


def _serialize_value(v: Any) -> str:
    """Serialize non-primitive values to JSON for CSV safety."""
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return str(v)


def write_tickers_to_csv(tickers: List[Dict[str, Any]], output_path: str) -> None:
    """Write a list of ticker dicts to CSV using the first item keys as field order.

    If no tickers are present, the CSV will not be created.
    """
    if not tickers:
        logging.info("No tickers provided — nothing to write to CSV.")
        return

    example = tickers[0]
    fieldnames = list(example.keys()) if example else []
    if not fieldnames:
        all_keys = set()
        for t in tickers:
            all_keys.update(t.keys())
        fieldnames = sorted(all_keys)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for t in tickers:
            row = {k: _serialize_value(t.get(k)) for k in fieldnames}
            writer.writerow(row)

    logging.info("Wrote %d tickers to %s", len(tickers), output_path)


def cli() -> None:
    """Parse CLI args and run the flow."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch Polygon tickers and write them to CSV")
    parser.add_argument("--output", "-o", default=os.path.join(os.path.dirname(__file__), "tickers.csv"), help="Output CSV path")
    parser.add_argument("--limit", "-l", type=int, default=1000, help="Page limit per request")
    parser.add_argument("--use-sample", action="store_true", help="Write a small sample CSV without calling the API")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(levelname)s: %(message)s")

    if args.use_sample:
        logging.info("Using sample tickers (no external API calls)")
        write_tickers_to_csv(SAMPLE_TICKERS, args.output)
        return

    if not POLYGON_API_KEY:
        logging.error("POLYGON_API_KEY is not set in the environment. Use --use-sample to generate a sample.")
        return

    try:
        tickers = fetch_all_tickers(limit=args.limit, api_key=POLYGON_API_KEY)
    except Exception as exc:
        logging.error("Failed to fetch tickers: %s", exc)
        return

    write_tickers_to_csv(tickers, args.output)


if __name__ == "__main__":
    cli()