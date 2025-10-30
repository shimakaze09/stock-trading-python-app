import requests
import os
import time
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import csv
import json

load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
LIMIT = 1000

def ensure_api_key(url):
    """Append apiKey only if it's not already in the URL."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if 'apiKey' not in qs:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}apiKey={POLYGON_API_KEY}"
    return url

def fetch(url):
    """Fetch data safely with retry and rate-limit handling."""
    url = ensure_api_key(url)
    while True:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 401:
                print("❌ Unauthorized (401). Check your API key.")
                return None
            if r.status_code != 200:
                print(f"⚠️ HTTP {r.status_code}: Retrying in 10s...")
                time.sleep(10)
                continue

            try:
                data = r.json()
            except ValueError:
                print("⚠️ Non-JSON or empty response, retrying in 15s...")
                time.sleep(15)
                continue

            if 'results' in data:
                return data

            if data.get('error', '').startswith("You've exceeded the maximum requests"):
                print("⏳ Rate limit hit — waiting 65 seconds...")
                time.sleep(65)
                continue

            print("⚠️ Unexpected response:", data)
            return None

        except requests.exceptions.RequestException as e:
            print("⚠️ Network error:", e, "Retrying in 20s...")
            time.sleep(20)

tickers = []

url = (
    f"https://api.polygon.io/v3/reference/tickers?"
    f"market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}"
)

data = fetch(url)
if data:
    tickers.extend(data['results'])

while data and 'next_url' in data:
    print("Fetching:", data['next_url'])
    data = fetch(data['next_url'])
    if data:
        tickers.extend(data['results'])

example_ticker = tickers[0] if tickers else None

OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "tickers.csv")

def _serialize_value(v):
    """Serialize values that are not primitive so CSV stays readable."""
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return v

if not tickers:
    print("No tickers found — nothing to write to CSV.")
else:
    # Use the first ticker's keys as the CSV header (preserves API order)
    fieldnames = list(example_ticker.keys()) if example_ticker else []
    if not fieldnames:
        # Fallback: union of all keys
        all_keys = set()
        for t in tickers:
            all_keys.update(t.keys())
        fieldnames = sorted(all_keys)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for t in tickers:
            row = {k: _serialize_value(t.get(k)) for k in fieldnames}
            writer.writerow(row)

    print(f"Wrote {len(tickers)} tickers to {OUTPUT_CSV}")