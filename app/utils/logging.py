"""Structured JSON logging for Film-Agent."""

import json
import sys
from datetime import datetime, timezone


def log_event(event: str, **kwargs):
    """Print a single JSON line to stdout with timestamp."""
    record = {
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "event": event,
        **kwargs,
    }
    json.dump(record, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
