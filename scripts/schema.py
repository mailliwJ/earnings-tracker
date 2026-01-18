from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import Any, Dict, Optional


def ymd(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def utc_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class EarningsEvent:
    symbol: str
    date: str
    time: str = ""
    epsEstimate: Optional[float] = None
    epsActual: Optional[float] = None
    revenueEstimate: Optional[float] = None
    revenueActual: Optional[float] = None
    lastUpdated: str = ""
    source: str = "yfinance"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
