import json
from pathlib import Path
from datetime import datetime
from service.logger import LOG_FILE

DEPLOY_FILE = Path("logs/deploys.jsonl")
INCIDENT_LOG = Path("chaos/incidents.log")

def load_incident_history():
    incidents = []

    if not INCIDENT_LOG.exists():
        return incidents

    with open(INCIDENT_LOG) as f:
        for line in f:
            incidents.append(json.loads(line))

    return incidents

def load_deploy_history():

    events = []

    if not DEPLOY_FILE.exists():
        return events

    with open(DEPLOY_FILE) as f:
        for line in f:
            events.append(json.loads(line))

    return events

def query_deploys(start, end):

    nearby = []

    for event in load_deploy_history():

        ts = datetime.fromisoformat(event["timestamp"])

        if start <= ts <= end:
            nearby.append(event)

    return nearby

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