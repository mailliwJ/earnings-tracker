from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

from scripts.schema import EarningsEvent, utc_iso, ymd


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, float) and pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def fetch_next_event(symbol: str, today: date) -> Optional[EarningsEvent]:
    """
    Returns the next upcoming earnings event for a symbol, or None if unavailable.
    Strategy:
      1) get_earnings_dates(limit=12) -> choose first date >= today
      2) fallback to ticker.calendar earnings date if needed
    """
    t = yf.Ticker(symbol)

    # 1) Primary: earnings dates dataframe
    df = None
    try:
        df = t.get_earnings_dates(limit=12)
    except Exception:
        df = None

    if df is not None and not df.empty:
        idx = df.index
        for i, ts in enumerate(idx):
            d = pd.to_datetime(ts).date()
            if d >= today:
                row = df.iloc[i]
                return EarningsEvent(
                    symbol=symbol,
                    date=ymd(d),
                    epsEstimate=_safe_float(row.get("EPS Estimate")) if hasattr(row, "get") else None,
                    epsActual=_safe_float(row.get("Reported EPS")) if hasattr(row, "get") else None,
                    lastUpdated=utc_iso(),
                    source="yfinance.get_earnings_dates",
                )

    # 2) Fallback: calendar
    cal = None
    try:
        cal = t.calendar
    except Exception:
        cal = None

    if isinstance(cal, dict):
        ed = cal.get("Earnings Date") or cal.get("EarningsDate")
        if ed is not None:
            candidates = ed if isinstance(ed, (list, tuple)) else [ed]
            parsed = []
            for x in candidates:
                try:
                    parsed.append(pd.to_datetime(x).date())
                except Exception:
                    pass
            parsed.sort()
            for d in parsed:
                if d >= today:
                    return EarningsEvent(
                        symbol=symbol,
                        date=ymd(d),
                        lastUpdated=utc_iso(),
                        source="yfinance.calendar",
                    )

    return None
