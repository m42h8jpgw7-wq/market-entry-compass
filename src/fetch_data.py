"""Download the indicator data from the World Bank API.

Run once (and again whenever you want fresh data):

    python -m src.fetch_data

Result: data/processed/indicators.csv in "long" format, one row per
country / indicator / year.
"""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

from src.config import COUNTRIES, DATA_FILE, END_YEAR, INDICATORS, START_YEAR

API = "https://api.worldbank.org/v2/country/{countries}/indicator/{code}"


def fetch_indicator(key: str, spec: dict) -> pd.DataFrame:
    """Download one indicator. If the main code fails, try the fallback code."""
    attempts = [{"code": spec["code"], "source": spec.get("source")}]
    if "fallback" in spec:
        attempts.append(spec["fallback"])

    last_error = None
    for attempt in attempts:
        try:
            return _download(key, attempt["code"], attempt.get("source"))
        except RuntimeError as error:
            print(f"  code {attempt['code']} did not work, trying the next option")
            last_error = error
    raise last_error


def _download(key: str, code: str, source: int | None) -> pd.DataFrame:
    """Download one indicator for all countries, following API pages."""
    url = API.format(countries=";".join(COUNTRIES), code=code)
    params = {
        "format": "json",
        "per_page": 5000,
        "date": f"{START_YEAR}:{END_YEAR}",
    }
    if source is not None:
        params["source"] = source

    rows, page = [], 1
    while True:
        params["page"] = page
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()

        # A valid answer is [metadata, data]. Errors come back as a single dict.
        if len(payload) < 2 or payload[1] is None:
            raise RuntimeError(f"No data for {code}: {payload}")

        meta, data = payload
        for item in data:
            if item["value"] is None:
                continue
            rows.append(
                {
                    "iso3": item["countryiso3code"],
                    "country": item["country"]["value"],
                    "indicator": key,
                    "year": int(item["date"]),
                    "value": float(item["value"]),
                }
            )
        if page >= meta["pages"]:
            break
        page += 1
        time.sleep(0.2)  # be polite to the API

    return pd.DataFrame(rows)


def main() -> None:
    frames = []
    for key, spec in INDICATORS.items():
        print(f"Downloading {key} ({spec['code']}) ...", flush=True)
        frame = fetch_indicator(key, spec)
        print(f"  -> {len(frame)} data points")
        frames.append(frame)

    data = pd.concat(frames, ignore_index=True)
    data = data[data["iso3"].isin(COUNTRIES)]  # drop aggregates like "World"

    out = Path(DATA_FILE)
    out.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(out, index=False)
    print(f"\nSaved {len(data)} rows for {data['iso3'].nunique()} countries to {out}")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as error:
        sys.exit(f"Network problem while calling the World Bank API: {error}")
