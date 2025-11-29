# app/guardrails_layer.py
# A tiny, readable validator for user prompts.

import re
from fastapi import HTTPException

# Topics we allow (related to log analysis)
_ALLOWED_TOPICS = [
    "error", "errors", "authentication", "auth",
    "spike", "spikes", "slow", "query", "queries",
    "database", "timeout", "traffic", "summary"
]

# Patterns we block (dangerous, sensitive, or off-topic)
_BLOCK_PATTERNS = [
    r"\b(drop|delete|truncate|shutdown)\b",      # destructive DB verbs
    r"\b(chmod|chown|rm\s+-rf)\b",               # shell delete commands
    r"(?:AKIA|ASIA)[A-Z0-9]{16}",                # AWS access-key-like
    r"(?i)password|api[_-]?key|secret",          # sensitive tokens
    r"(?i)\b(poem|story|lyrics|love|games)\b"    # off-topic prompts
]

def validate_prompt_content(prompt: str) -> None:
    """
    Checks that the user prompt is safe and relevant.
    Raises HTTP 400 if it is too short, risky, or off-topic.
    """
    p = (prompt or "").strip()

    # 1. Too short
    if len(p) < 8:
        raise HTTPException(400, "Guardrails: prompt too short or unclear.")

    # 2.  Contains blocked patterns
    for pat in _BLOCK_PATTERNS:
        if re.search(pat, p):
            raise HTTPException(400, "Guardrails: prompt contains unsupported or sensitive content.")

    # 3.  Must mention a log-analysis topic
    if not any(k in p.lower() for k in _ALLOWED_TOPICS):
        raise HTTPException(400, "Guardrails: prompt must relate to log analysis (errors/slow queries/traffic).")

    # Passed all checks
    return
