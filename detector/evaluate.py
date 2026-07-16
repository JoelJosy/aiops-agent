# detector/evaluate.py
import os
import glob
import json
import pandas as pd
import numpy as np
from mad_detector import MADDetector

BASELINE_PATH = "data/baseline.parquet"
TRAIN_INCIDENTS_DIR = "data/incidents/train"
INCIDENTS_LOG = "chaos/incidents.log"

def get_ground_truth_start(incident_filename):
    """Matches the unique filename hash to the true start time in incidents.log cleanly."""
    if not os.path.exists(INCIDENTS_LOG):
        print(f"Cannot find {INCIDENTS_LOG} in current path.")
        return None
    
    # Extract the short hash from the filename (e.g., memory_leak_35c25d43.parquet -> 35c25d43)
    base = os.path.basename(incident_filename).replace(".parquet", "")
    short_id = base.split("_")[-1].strip()
    
    with open(INCIDENTS_LOG, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                # Ensure we match string characters cleanly regardless of casing
                if str(data.get("incident_id", "")).startswith(short_id):
                    # Strip any potential 'Z' or timezone text and force a uniform timestamp comparison
                    return pd.to_datetime(data["start"]).tz_localize(None)
            except Exception as e:
                continue
    return None

def evaluate_incident(detector, baseline_df, file_path):
    incident_df = pd.read_parquet(file_path)
    incident_df.index = pd.to_datetime(incident_df.index, utc=True)
    
    # Clean and isolate the simulation window
    # We assign a matching single session ID so the rolling calculations roll naturally
    sim_baseline = baseline_df.copy()
    sim_baseline["session_id"] = 0
    
    sim_incident = incident_df.copy()
    sim_incident["session_id"] = 0
    
    # Combine chronologically ensuring no cross-contamination
    combined = pd.concat([sim_baseline, sim_incident])
    # Use max in 30s windows
    combined_clean = combined.resample("30s").max()
    
    # Patch raw zeroes to Nan since these cannot be 0
    for col in ["process_resident_memory_bytes", "process_cpu_rate", "app_p95_latency_seconds"]:
        if col in combined_clean.columns:
            combined_clean[col] = combined_clean[col].replace(0, np.nan).ffill().bfill()
            
    combined_clean["session_id"] = 0
    
    # Run Detector
    results = detector.fit_predict(combined_clean)
    
    # Extract just the specific incident window results
    inc_results = results.loc[incident_df.index.min():incident_df.index.max()]
    
    # Identify which metric triggered first
    earliest_trigger = None
    trigger_metric = "None"
    
    for col in inc_results.columns:
        if "anomaly" in col:
            flagged_rows = inc_results[inc_results[col] == 1]
            if not flagged_rows.empty:
                first_flag_time = flagged_rows.index.min()
                if earliest_trigger is None or first_flag_time < earliest_trigger:
                    earliest_trigger = first_flag_time
                    trigger_metric = col.replace("_anomaly", "")
                    
    # Calculate detection delay against ground truth start
    gt_start = get_ground_truth_start(file_path)
    delay_seconds = None
    if earliest_trigger is not None and gt_start is not None:
        # Strip timezone context from pandas timestamps so subtraction doesn't error out
        t1 = earliest_trigger.tz_localize(None) if earliest_trigger.tzinfo else earliest_trigger
        t2 = gt_start.tz_localize(None) if gt_start.tzinfo else gt_start
        delay_seconds = max(0, (t1 - t2).total_seconds())
        
    return trigger_metric, delay_seconds

def main():
    if not os.path.exists(BASELINE_PATH):
        print("baseline.parquet not found!")
        return
        
    baseline_df = pd.read_parquet(BASELINE_PATH)
    baseline_df.index = pd.to_datetime(baseline_df.index, utc=True)
    
    detector = MADDetector(persistence_steps=3)
    
    # Evaluate False Positive Rate on Pure Baseline 
    print("Part 1: Evaluating False Alarm Rate on Clean Baseline...")
    baseline_clean = baseline_df.resample("30s").max().ffill().bfill()
    baseline_results = detector.fit_predict(baseline_clean)
    
    total_baseline_rows = len(baseline_results)
    false_positives = 0
    for col in baseline_results.columns:
        if "anomaly" in col:
            false_positives += baseline_results[col].sum()
            
    fp_rate = (false_positives / total_baseline_rows) * 100
    print(f"   Clean Steps Evaluated: {total_baseline_rows}")
    print(f"   False Alarms Triggered: {false_positives} ({fp_rate:.2f}% False Positive Rate)")
    print("-" * 75)
    
    # Loop and Benchmark Train Incidents
    print("Part 2: Evaluating Training Chaos Incident Matrix...")
    incident_files = glob.glob(os.path.join(TRAIN_INCIDENTS_DIR, "*.parquet"))
    
    results_matrix = []
    for f_path in incident_files:
        name = os.path.basename(f_path)
        metric, delay = evaluate_incident(detector, baseline_df, f_path)
        
        delay_str = f"{int(delay)}s" if delay is not None else "N/A"
        results_matrix.append({
            "File Name": name[:35],
            "Primary Trigger Metric": metric,
            "Detection Delay": delay_str
        })
        
    df_matrix = pd.DataFrame(results_matrix)
    print(df_matrix.to_string(index=False))

if __name__ == "__main__":
    main()