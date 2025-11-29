from __future__ import annotations
from typing import List, Dict, Tuple
from collections import Counter
from datetime import datetime

def _minute_key(ts: str | None) -> str | None:
    if not ts:
        return None
    # accept ISO strings; keep to the minute
    s = str(ts)
    return s[:16]  # YYYY-MM-DDTHH:MM

def _percent(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.1f}%" if d else "0%"

def summarize_events(events: List[Dict]) -> Dict:
    total = len(events or [])
    per_min = Counter()
    reasons = Counter()
    users = Counter()
    examples: List[str] = []

    error_like = 0

    for i, e in enumerate(events or []):
        msg = (e.get("message") or "").strip()
        lvl = (e.get("level") or "").upper()
        if i < 4 and msg:
            examples.append(msg)

        low = msg.lower()
        if "invalidtoken" in low:
            reasons["InvalidToken"] += 1
        if "expired" in low:
            reasons["Expired"] += 1
        if "user=" in low:
            try:
                user = msg.split("user=")[1].split()[0].strip(",;.")
                if user:
                    users[user] += 1
                    reasons[f"user={user}"] += 1  # also count as a reason bucket
            except Exception:
                pass

        if lvl == "ERROR" or "failed" in low or "error" in low:
            error_like += 1

        mk = _minute_key(e.get("timestamp"))
        if mk:
            per_min[mk] += 1

    # spikes (top 2)
    spikes = per_min.most_common(2)
    top_spikes = [{"timestamp": f"{t}:00Z", "count": c} for t, c in spikes]

    # reasons (top 3)
    top_reasons = [{"reason": r, "count": c} for r, c in reasons.most_common(3)]

    # top users (top 3)
    top_users = [{"user": u, "count": c} for u, c in users.most_common(3)]

    # Build a clear multi-line summary (bullets)
    lines: List[str] = []
    lines.append(f"• Window size: {total} events; error-like: {error_like} ({_percent(error_like, total)}).")
    if top_spikes:
        spike_bits = [f"{s['timestamp']} ×{s['count']}" for s in top_spikes]
        lines.append("• Spikes: " + ", ".join(spike_bits) + ".")
    if top_reasons:
        reason_bits = [f"{r['reason']} ×{r['count']} ({_percent(r['count'], total)})" for r in top_reasons]
        lines.append("• Top reasons: " + ", ".join(reason_bits) + ".")
    if top_users:
        user_bits = [f"{u['user']} ×{u['count']}" for u in top_users]
        lines.append("• Affected users: " + ", ".join(user_bits) + ".")
    if not (top_spikes or top_reasons):
        lines.append("• No obvious spikes or dominant reasons detected.")
    
    lines.append("• Next steps: add alert InvalidToken>10/min(5m); review token TTL/refresh; add auth-failure panel.")

    summary_text = "\n".join(lines)

    return {
        "analysis": {
            "total_events": total,
            "error_like": error_like,
            "top_spikes": top_spikes,
            "top_reasons": top_reasons,
            "top_users": top_users,
            "examples": examples,
        },
        "summary": summary_text,
        "actions": [
            "Alert if InvalidToken > 10/min for 5m",
            "Review token TTL and client refresh flow",
            "Add dashboard: auth failure rate per minute",
        ],
    }

# Compatibility wrapper 
def summarize(prompt: str, events: List[Dict], log_group: str, mock: bool) -> str:
    return summarize_events(events).get("summary", "No summary available.")
