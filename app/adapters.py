# app/adapters.py
from __future__ import annotations
from typing import List, Dict
from datetime import datetime, timedelta, timezone

# Data builders

def _iso(dt: datetime) -> str:
    """ISO string, minute precision, with timezone."""
    return dt.replace(second=0, microsecond=0).isoformat()

def _mock_logs() -> List[Dict]:
    """
    Deterministic  dataset (auth failures w/ InvalidToken).
    Pattern: clear InvalidToken spike, users alice/bob/carol.
    """
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    return [
        {"timestamp": _iso(now - timedelta(minutes=50)), "level": "INFO",
         "message": "Auth failed for user=alice reason=InvalidToken"},
        {"timestamp": _iso(now - timedelta(minutes=50, seconds=30)), "level": "INFO",
         "message": "Auth failed for user=bob reason=InvalidToken"},
        {"timestamp": _iso(now - timedelta(minutes=20)), "level": "INFO",
         "message": "Token refresh succeeded for user=carol"},
        {"timestamp": _iso(now - timedelta(minutes=10)), "level": "ERROR",
         "message": "Auth failed for user=carol reason=InvalidToken"},
        {"timestamp": _iso(now - timedelta(minutes=10, seconds=10)), "level": "ERROR",
         "message": "Auth failed for user=carol reason=InvalidToken"},
    ]

def _realish_logs() -> List[Dict]:
    """
    Realish dataset with DIFFERENT shape and reasons.
    Pattern: Gateway timeouts + db errors + different users (dave/erin) and fewer InvalidToken.
    """
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    return [
        {"timestamp": _iso(now - timedelta(minutes=41)), "level": "ERROR",
         "message": "Gateway timeout while calling /api/orders user=dave"},
        {"timestamp": _iso(now - timedelta(minutes=39)), "level": "ERROR",
         "message": "DatabaseError: connection pool exhausted on writer"},
        {"timestamp": _iso(now - timedelta(minutes=38)), "level": "INFO",
         "message": "Retry succeeded for job=order_sync batch=42"},
        {"timestamp": _iso(now - timedelta(minutes=17)), "level": "ERROR",
         "message": "Auth failed for user=erin reason=Expired"},
        {"timestamp": _iso(now - timedelta(minutes=16)), "level": "ERROR",
         "message": "Payment service timeout user=erin route=/pay/charge"},
    ]

# Public adapter API 

def fetch_events(log_group: str, time_range: str, *, mock: bool = False) -> List[Dict]:
    """
    Minimal adapter used by main.py.
    If mock=True  -> return deterministic dataset (InvalidToken spike).
    If mock=False -> return REALISH dataset (timeouts/db errors/expired).
    """
    return _mock_logs() if mock else _realish_logs()