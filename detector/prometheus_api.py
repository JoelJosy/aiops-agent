import requests
import pandas as pd
from datetime import datetime, timezone
from typing import Union

PROMETHEUS_URL = "http://localhost:9090/api/v1/query_range"


def format_timestamp(dt: Union[str, datetime]) -> float:
    """
    Convert either datetime objects or ISO-8601 strings 
    into Unix Epoch timestamps (seconds as a float), as expected by Prometheus.
    """
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # If it already has a timezone, convert it to UTC 
            dt = dt.astimezone(timezone.utc)
        return dt.timestamp()

    # If it is an ISO string, parse it
    clean_str = dt.replace("Z", "+00:00") if dt.endswith("Z") else dt
    parsed_dt = datetime.fromisoformat(clean_str)
    
    # Attach UTC if naive before calling astimezone to prevent local system bias
    if parsed_dt.tzinfo is None:
        parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
        
    parsed_dt = parsed_dt.astimezone(timezone.utc)
    return parsed_dt.timestamp()


def fetch_metric(query: str, start: Union[datetime, str], end: Union[datetime, str], step: str = "5s") -> pd.DataFrame:
    """
    Fetch metric data from Prometheus for a given query and time range.
    """
    start_ts = format_timestamp(start)
    end_ts = format_timestamp(end)

    params = {
        "query": query,
        "start": start_ts,
        "end": end_ts,
        "step": step
    }

    response = requests.get(PROMETHEUS_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()
    
    if data.get("status") != "success":
        raise ValueError(f"Prometheus query failed: {data.get('error', 'Unknown error')}")
    
    results = data.get("data", {}).get("result", [])
    
    if not results:
        return pd.DataFrame(columns=["timestamp", "value"]).set_index("timestamp")

    all_series_dfs = []

    for series in results:
        labels = series.get("metric", {})
        values = series.get("values", [])

        if not values:
            continue
            
        timestamps, numeric_values = zip(*values)

        # Convert raw timestamps to UTC pandas DatetimeIndex
        df_timestamps = pd.to_datetime(timestamps, unit="s", utc=True)

        # Create the base DataFrame for this time-series
        series_df = pd.DataFrame(
            {"value": pd.to_numeric(numeric_values, errors="coerce")},
            index=df_timestamps
        )
        
        # Inject all labels as static columns for this series
        for label_key, label_val in labels.items():
            series_df[label_key] = label_val
            
        all_series_dfs.append(series_df)

    # return empty DataFrame before pd.concat to prevent ValueError
    if not all_series_dfs:
        return pd.DataFrame(columns=["timestamp", "value"]).set_index("timestamp")

    combined_df = pd.concat(all_series_dfs)
    combined_df.index.name = "timestamp"
    
    return combined_df.sort_index()