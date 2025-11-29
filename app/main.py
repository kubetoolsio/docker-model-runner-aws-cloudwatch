# app/main.py
from __future__ import annotations

from typing import List, Optional, Any, Dict
import os
import re
import logging

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# -----FastAPI & Models-----
from fastapi import FastAPI, HTTPException, Path, Body, Query
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

from .adapters import fetch_events
from .summarizer import summarize, summarize_events
from .guardrails_layer import validate_prompt_content

#  INLINE prompts (no package import) 
RECIPE_PROMPTS = {
    "error_spikes": (
        "Summarize authentication or system error spikes in the given log group "
        "for the requested time window. Highlight main causes, frequency spikes, "
        "affected users if visible, and suggest next steps."
    ),
    "slow_queries": (
        "Summarize slow database or API query performance issues. Include typical "
        "durations, any frequency patterns, and likely bottlenecks."
    ),
    "traffic_summary": (
        "Summarize overall service traffic trends. Highlight peaks, dips, and any "
        "anomalies worth investigating."
    ),
}

def normalize_recipe(name: str) -> str:
    return (name or "").strip().lower()

#  ---- FastAPI app & env flags -------
app = FastAPI(title="Conversational CloudWatch")

APP_VERSION = "1.1.0"
MODE_MOCK = os.environ.get("MOCK", "true").lower() == "true"
USE_LLM = os.environ.get("USE_LLM", "false").lower() == "true"
logger.info("Startup mode: MOCK=%s USE_LLM=%s", MODE_MOCK, USE_LLM)

# Schemas
class LogEvent(BaseModel):
    timestamp: Any = None
    message: str = ""
    level: str = "INFO"

class QueryRequest(BaseModel):
    prompt: str = Field(..., example="error_spikes")
    log_group: Optional[str] = Field("/aws/lambda/auth-service")
    time_range: Optional[str] = Field("2h")
    mock: Optional[bool] = Field(False, description="Overrides env MOCK")

class QueryResponse(BaseModel):
    request_echo: Dict
    raw_events: List[LogEvent]
    summary: str

# Guardrails 
_MAX_PROMPT = 300
_TIME_RE = re.compile(r"^\d+[smhd]$")  # 15m, 2h, 7d

def _to_log_event(e: Any) -> LogEvent:
    if isinstance(e, LogEvent):
        return e
    if isinstance(e, dict):
        return LogEvent(
            timestamp=e.get("timestamp"),
            message=e.get("message", ""),
            level=e.get("level", "INFO"),
        )
    return LogEvent(timestamp=None, message=str(e), level="INFO")

#  Routes 
@app.get("/health_status", tags=["ops"])
def health_check():
    return {"status": "ok"}

@app.get("/version", tags=["ops"])
def version_info():
    return {
    "app": "Conversational-Cloudwatch"
    "versions:" "1.1.0",
    "mode"
    : "LLM" if USE_LLM else "Mock",
    }

import logging
logger = logging.getLogger("uvicorn")

@app.on_event("startup")
async def announce_startup():
   logger.info(
      f"Conversational CloudWatch starting - v1.1.0  | mode= {'LLM' if USE_LLM else 'Mock'}"
)
   logger.info("Health check OK -API responding normally ( startup)")

#   ----Routes: Analysis------

@app.post("/query", response_model=QueryResponse, tags=["analysis"])
def query_logs(req: QueryRequest = Body(...)):
    # Guardrails
    if len(req.prompt or "") > _MAX_PROMPT:
        raise HTTPException(status_code=400, detail="Prompt too long. Keep under 300 characters.")
    if req.time_range and not _TIME_RE.match(req.time_range):
        raise HTTPException(status_code=400, detail="Invalid time_range. Use like 15m, 2h, 7d.")
    
    # Resolve recipe -> instruction text
    recipe = normalize_recipe(req.prompt)
    prompt_text = RECIPE_PROMPTS.get(recipe, req.prompt)
    
    # debug log for testing guardrails
    logger.info("VALIDATING PROMPT: %s", prompt_text)
       
    # NEW: semantic guardrails (block off-topic/risky content)
    validate_prompt_content(prompt_text)

    # Mode & fetch
    mock_mode = MODE_MOCK if req.mock is None else bool(req.mock)
    lg = req.log_group or "/aws/lambda/auth-service"
    tr = req.time_range or "2h"
    raw = fetch_events(lg, tr, mock=mock_mode)
    if isinstance(raw, list) and len(raw) > 200:
        raw = raw[:200]
    events = [_to_log_event(e).model_dump() for e in (raw or [])]

    # Summarize (string)
    summary_text = summarize(prompt_text, events, lg, mock_mode)

    return QueryResponse(
        request_echo={"prompt": req.prompt, "log_group": lg, "time_range": tr, "mock": mock_mode, "resolved_recipe": recipe},
        raw_events=events,
        summary=summary_text,
    )

# -----Routes: recipes ------------------
@app.get("/recipes", tags=["recipes"])
def list_recipes():
    # Use inline dict RECIPE_PROMPTS 
    names = sorted(list(RECIPE_PROMPTS.keys()))
    return JSONResponse(content={"available_recipes": names})


@app.get("/recipes/{name}", response_model=QueryResponse, tags=["recipes"])
def run_recipe(
    name: str = Path(..., description="error_spikes | slow_queries | traffic_summary"),
    log_group: str = Query("/aws/lambda/auth-service"),
    time_range: str = Query("2h"),
    mock: bool = Query(False),
):
    if time_range and not _TIME_RE.match(time_range):
        raise HTTPException(status_code=400, detail="Invalid time_range. Use like 15m, 2h, 7d.")

    recipe = normalize_recipe(name)
    prompt_text = RECIPE_PROMPTS.get(recipe, f"Summarize logs for {log_group} over {time_range}.")

        # semantic guardrails
    validate_prompt_content(prompt_text)

    raw = fetch_events(log_group, time_range, mock=mock)
    events = [_to_log_event(e).model_dump() for e in (raw or [])]
    summary_text = summarize(prompt_text, events, log_group, mock)

    return QueryResponse(
        request_echo={"prompt": recipe, "log_group": log_group, "time_range": time_range, "mock": mock, "resolved_recipe": recipe},
        raw_events=events,
        summary=summary_text,
    )
