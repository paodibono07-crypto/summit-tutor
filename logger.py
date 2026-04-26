import json
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path("logs.jsonl")


def log_interaction(query: str, response: str, latency: float) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "response": response,
        "latency_seconds": round(latency, 3),
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
