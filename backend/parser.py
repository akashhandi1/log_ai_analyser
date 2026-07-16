# backend/parser.py
import re
from datetime import datetime

# Common Log Regex: [Timestamp] LEVEL [Service] Message
LOG_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+(?P<level>[A-Z]+)\s+\[(?P<service>[^\]]+)\]\s+(?P<message>.+)$"
)

def parse_log_line(line: str) -> dict:
    match = LOG_PATTERN.match(line.strip())
    if match:
        data = match.groupdict()
        return data
    # Fallback if log format is unstructured
    return {
        "timestamp": datetime.now().isoformat(),
        "level": "UNKNOWN",
        "service": "system",
        "message": line.strip()
    }