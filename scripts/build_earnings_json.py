from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


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
    try:
        if x is None or pd.isna(x):
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


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    watchlist_path = root / "data" / "watchlist.json"
    out_path = root / "data" / "earnings.json"

    tickers = load_watchlist(watchlist_path)
    if not tickers:
        raise RuntimeError("watchlist.json has no tickers. Expected: {\"tickers\": [\"AAPL\", ...]}")

    this_year = datetime.now().date().year
    generated_at = _utc_iso()

    results: dict[str, list[dict]] = {}
    notes: dict[str, str] = {}

    for sym in tickers:
        country = get_country(sym)

        next_date = None
        eps_est = None
        eps_rep = None
        surprise = None
        note = "ok"

        try:
            t = yf.Ticker(sym)
            edf = t.get_earnings_dates(limit=1)

            if edf is None or edf.empty:
                note = "no earnings date"
            else:
                next_date = edf.index[0].date()
                row = edf.iloc[0]

                # These are the columns yfinance returns here:
                eps_est = row.get("EPS Estimate", None) if hasattr(row, "get") else None
                eps_rep = row.get("Reported EPS", None) if hasattr(row, "get") else None
                surprise = row.get("Surprise(%)", None) if hasattr(row, "get") else None

                # optional: drop past-year dates
                if next_date and next_date.year < this_year:
                    next_date = None
                    note = "earnings date before this year"

        except Exception as e:
            note = f"error: {e}"

        notes[sym] = note

        if next_date is None:
            results[sym] = []
            continue

        results[sym] = [{
            # Apps Script expects these keys:
            "symbol": sym,
            "date": pd.to_datetime(next_date).strftime("%Y-%m-%d"),
            "epsEstimate": _num_or_none(eps_est),
            "epsActual": _num_or_none(eps_rep),
            "surprisePct": _num_or_none(surprise),
            "lastUpdated": generated_at,
            "source": "yfinance.get_earnings_dates",
            "country": country,
        }]

    payload = {"generated_at": generated_at, "results": results, "notes": notes}
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
