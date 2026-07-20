import json
from pathlib import Path
from datetime import datetime
from service.logger import LOG_FILE


def load_logs(start, end):

    if isinstance(start, str):
        start = datetime.fromisoformat(start)

    if isinstance(end, str):
        end = datetime.fromisoformat(end)

    events = []

    with open(LOG_FILE) as f:
        for line in f:
            record = json.loads(line)

            ts = datetime.fromisoformat(
                record["timestamp"]
            )

            if start <= ts <= end:
                events.append(record)

    return events