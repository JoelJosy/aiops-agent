import uuid
import json
from typing import Union, Any, Dict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG_FILE_PATH = Path(__file__).parent / "incidents.log"


# convert datetime to ISO 8601 format with UTC timezone
def format_timestamp(dt: Union[datetime, str]) -> str:
    if isinstance(dt, datetime):
        # If  no timezone info, assume it's UTC and attach UTC timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # If it already has a timezone, convert it to UTC 
            dt = dt.astimezone(timezone.utc)
    else:
        # Input is string, parse it as ISO format then convert to UTC
        clean_str = dt.replace("Z", "+00:00") if dt.endswith("Z") else dt
        dt = datetime.fromisoformat(clean_str).astimezone(timezone.utc)
    
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def log_incident(fault_type: str,
    target: str,
    start: Union[datetime, str],
    end: Union[datetime, str],
    params: Dict[str, Any]
) -> Dict[str, Any]:

    incident_record = {
        "incident_id": str(uuid.uuid4()),
        "fault_type": fault_type,
        "target": target,
        "start": format_timestamp(start),
        "end": format_timestamp(end),
        "params": params
    }

    # Open the file in append mode to prevent overwriting previous data
    with open(LOG_FILE_PATH, mode="a", encoding="utf-8") as file:
        file.write(json.dumps(incident_record) + "\n")

    return incident_record