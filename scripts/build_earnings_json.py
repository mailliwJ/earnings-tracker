from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict, List

from scripts.schema import utc_iso
from scripts.yf_fetch import fetch_next_event


ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT / "data" / "watchlist.json"
OUT_PATH = ROOT / "data" / "earnings.json"


def load_watchlist() -> List[str]:
    obj = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    tickers = obj.get("tickers", [])
    # normalize, dedupe preserve order
    out = []
    seen = set()
    for t in tickers:
        s = str(t or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def main() -> None:
    today = date.today()
    tickers = load_watchlist()

    results: Dict[str, List[dict]] = {}
    for sym in tickers:
        try:
            ev = fetch_next_event(sym, today)
            results[sym] = [ev.to_dict()] if ev else []
        except Exception:
            results[sym] = []

    payload = {
        "generated_at": utc_iso(),
        "results": results
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
