# app/mcp_client.py
import subprocess, json, time

def fetch_from_mcp(log_group: str, time_range: str):
    """
    Fetch logs from AWS CloudWatch using AWS CLI.
    """

    if not log_group:
        return []

    # convert time_range like "2h" or "15m" into seconds
    if time_range.endswith("h"):
        seconds = int(time_range[:-1]) * 3600
    elif time_range.endswith("m"):
        seconds = int(time_range[:-1]) * 60
    else:
        seconds = 3600  # default 1 hour

    start_ms = int((time.time() - seconds) * 1000)

    try:
        # run AWS CLI command
        res = subprocess.run(
            ["aws", "logs", "filter-log-events",
             "--log-group-name", log_group,
             "--start-time", str(start_ms),
             "--limit", "20"],
            capture_output=True, text=True, check=True
        )

        data = json.loads(res.stdout or "{}")

        events = []
        for e in data.get("events", []):
            events.append({
                "timestamp": str(e.get("timestamp")),
                "message": e.get("message", "").strip(),
                "level": "INFO"
            })
        return events

    except Exception as e:
        print("CloudWatch fetch failed:", e)
        return []