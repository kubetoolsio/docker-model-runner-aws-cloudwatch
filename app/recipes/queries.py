from datetime import datetime

def error_spikes(log_group: str):
    now = datetime.utcnow().isoformat()
    return {"recipe": "error_spikes", "log_group": log_group, "events": [
        {"timestamp": now, "message": "5 errors detected in last 2h", "level": "ERROR"}
    ]}

def slow_queries(log_group: str):
    now = datetime.utcnow().isoformat()
    return {"recipe": "slow_queries", "log_group": log_group, "events": [
        {"timestamp": now, "message": "Detected queries exceeding 3s latency", "level": "WARNING"}
    ]}

def traffic_summary(log_group: str):
    now = datetime.utcnow().isoformat()
    return {"recipe": "traffic_summary", "log_group": log_group, "events": [
        {"timestamp": now, "message": "Traffic steady at 1200 req/min", "level": "INFO"}
    ]}
