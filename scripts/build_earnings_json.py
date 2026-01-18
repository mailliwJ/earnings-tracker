from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf


UA_POOL = [
    # a few common desktop browser UAs (rotating can reduce 429/blocks)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


def get_country(symbol: str) -> str:
    if not symbol:
        return ""
    if symbol.endswith(".AX"):
        return "Australia"
    if symbol.endswith(".HE"):
        return "Finland"
    if symbol.endswith(".PA"):
        return "France"
    if symbol.endswith(".DE"):
        return "Germany"
    if symbol.endswith(".HK"):
        return "Hong Kong"
    if symbol.endswith(".MI"):
        return "Italy"
    if symbol.endswith(".T"):
        return "Japan"
    if symbol.endswith(".AS"):
        return "Netherlands"
    if symbol.endswith(".SI"):
        return "Singapore"
    if symbol.endswith(".MC"):
        return "Spain"
    if symbol.endswith(".ST"):
        return "Sweden"
    if symbol.endswith(".L"):
        return "United Kingdom"
    return "United States"


def _utc_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _num_or_none(x):
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def load_watchlist(path: Path) -> list[str]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    tickers = obj.get("tickers", [])
    out, seen = [], set()
    for t in tickers:
        s = str(t or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(UA_POOL),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })
    return s


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    watchlist_path = root / "data" / "watchlist.json"
    out_path = root / "data" / "earnings.json"

    tickers = load_watchlist(watchlist_path)
    if not tickers:
        # fail fast so you don’t silently commit an empty file
        raise RuntimeError("watchlist.json has no tickers. Expected: {\"tickers\": [\"AAPL\", ...]}")

    generated_at = _utc_iso()

    # One shared session for all tickers (with a browser UA)
    session = make_session()

    results: dict[str, list[dict]] = {}
    notes: dict[str, str] = {}

    for i, sym in enumerate(tickers, start=1):
        country = get_country(sym)

        next_date = None
        eps_est = None
        eps_rep = None
        surprise = None
        note = "ok"

        try:
            t = yf.Ticker(sym, session=session)
            edf = t.get_earnings_dates(limit=1)

            if edf is None or edf.empty:
                note = "no earnings date (empty response)"
            else:
                next_date = edf.index[0].date()
                row = edf.iloc[0]
                eps_est = row.get("EPS Estimate", None) if hasattr(row, "get") else None
                eps_rep = row.get("Reported EPS", None) if hasattr(row, "get") else None
                surprise = row.get("Surprise(%)", None) if hasattr(row, "get") else None

        except Exception as e:
            note = f"error: {e.__class__.__name__}: {e}"

        notes[sym] = note

        # Only create an event if we have a date (Apps Script expects events with date)
        if next_date is None:
            results[sym] = []
        else:
            results[sym] = [{
                "symbol": sym,
                "date": pd.to_datetime(next_date).strftime("%Y-%m-%d"),
                "epsEstimate": _num_or_none(eps_est),
                "epsActual": _num_or_none(eps_rep),
                "surprisePct": _num_or_none(surprise),
                "lastUpdated": generated_at,
                "source": "yfinance.get_earnings_dates",
                # optional metadata (Apps Script can ignore)
                "country": country,
            }]

        # gentle pacing to reduce rate-limits / blocks on runners
        time.sleep(0.35)

    payload = {
        "generated_at": generated_at,
        "results": results,
        "notes": notes,  # diagnostics without breaking Apps Script event parsing
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
