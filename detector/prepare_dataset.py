import os
import json
import pandas as pd
from datetime import datetime, timezone, timedelta
from prometheus_api import fetch_feature_table


RAW_PARQUET = "data/telemetry_48h_raw.parquet"
INCIDENTS_LOG = "chaos/incidents.log"

def parse_incidents_log():
    """Parses JSON Lines from incidents.log and returns clean UTC datetimes."""
    incidents = []
    if not os.path.exists(INCIDENTS_LOG):
        print(f"{INCIDENTS_LOG} not found!")
        return incidents

    with open(INCIDENTS_LOG, "r") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                start = pd.to_datetime(data["start"], utc=True)
                end = pd.to_datetime(data["end"], utc=True)
                incidents.append({
                    "id": data["incident_id"],
                    "fault": data["fault_type"],
                    "start": start,
                    "end": end
                })
            except Exception as e:
                print(f"Error parsing line {idx}: {line}. Error: {e}")
    return incidents

def main():
    # Setup directories
    os.makedirs("data/incidents/train", exist_ok=True)
    os.makedirs("data/incidents/test", exist_ok=True)

    # 1. Load raw telemetry
    if os.path.exists(RAW_PARQUET):
        print(f"Loading raw historical data from {RAW_PARQUET}...")
        df = pd.read_parquet(RAW_PARQUET)
    else:
        # Fallback query
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=48)
        print(f"Fetching raw 48h data...")
        df = fetch_feature_table(start_time, end_time, step="30s")
        df.to_parquet(RAW_PARQUET)

    print(f"Total Raw Data Points: {len(df)}")
    df.index = pd.to_datetime(df.index, utc=True)

    # 2. Parse JSON incidents
    incidents = parse_incidents_log()
    total_incidents = len(incidents)
    print(f"Successfully parsed {total_incidents} chaos incidents from log.")

    # 3. Define the Train/Test split 
    # We reserve 3 distinct incidents for untouched testing:
    # - 1 downstream_latency (idx 4)
    # - 1 downstream_failure (idx 5)
    # - 1 cpu_spike (idx 6)
    test_indices = {4, 5, 6} 

    exclude_mask = pd.Series(False, index=df.index)

    for idx, inc in enumerate(incidents):
        buffer_start = inc["start"] - timedelta(minutes=3)
        buffer_end = inc["end"] + timedelta(minutes=3)

        # Exclude this entire window from the baseline
        exclude_mask.loc[buffer_start:buffer_end] = True

        # Extract incident window + buffer padding
        incident_session = df.loc[buffer_start:buffer_end].copy()
        
        # Decide folder based on split
        split_folder = "test" if idx in test_indices else "train"
        short_id = inc["id"][:8]  
        
        filename = f"data/incidents/{split_folder}/{inc['fault']}_{short_id}.parquet"
        incident_session.to_parquet(filename)
        print(f"Saved [{split_folder}] session: {filename} ({len(incident_session)} rows)")

    # 4. Filter and Export Pure Baseline
    is_active = df["request_rate"] > 0.05
    is_online = df["app_availability"] == 1.0
    is_clean = ~exclude_mask

    baseline_df = df[is_active & is_online & is_clean].copy()

    # Create session IDs to group continuous sections of baseline data 
    # (gaps > 15s indicate new session)
    time_deltas = baseline_df.index.to_series().diff()
    session_splits = (time_deltas > pd.Timedelta(seconds=120))
    baseline_df["session_id"] = session_splits.cumsum()

    baseline_df.to_parquet("data/baseline.parquet")
    print("-" * 60)
    print("Dataset Preparation Complete!")
    print(f"Clean baseline: data/baseline.parquet ({len(baseline_df)} rows, {baseline_df['session_id'].nunique()} active sessions)")
    print(f"Train Incidents: {total_incidents - len(test_indices)} files in data/incidents/train/")
    print(f"Untouched Test Incidents: {len(test_indices)} files in data/incidents/test/")

if __name__ == "__main__":
    main()