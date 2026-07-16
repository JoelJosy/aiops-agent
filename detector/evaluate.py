# detector/evaluate.py
import os
import glob
import json
import pandas as pd
import numpy as np
from mad_detector import MADDetector
from forecast_detector import ForecastResidualDetector 

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
    """Evaluates a single incident file against the provided detector and baseline, returning the first triggered metric and detection delay in seconds."""
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
    
    # Instantiate both detectors to compare side-by-side
    mad_detector = MADDetector(persistence_steps=3)
    forecast_detector = ForecastResidualDetector(persistence_steps=3)
    
    # Evaluate False Positive Rate on Pure Baseline 
    print("Part 1: Evaluating False Alarm Rate on Clean Baseline...")
    baseline_clean = baseline_df.resample("30s").max().ffill().bfill()
    
    # 1a. Run Baseline for MAD
    baseline_results_mad = mad_detector.fit_predict(baseline_clean)
    false_positives_mad = sum(baseline_results_mad[col].sum() for col in baseline_results_mad.columns if "anomaly" in col)
    fp_rate_mad = (false_positives_mad / len(baseline_results_mad)) * 100
    
    # 1b. Run Baseline for Forecasting Residuals
    baseline_results_fc = forecast_detector.fit_predict(baseline_clean)
    false_positives_fc = sum(baseline_results_fc[col].sum() for col in baseline_results_fc.columns if "anomaly" in col)
    fp_rate_fc = (false_positives_fc / len(baseline_results_fc)) * 100
    
    print(f"   Clean Steps Evaluated: {len(baseline_clean)}")
    print(f"   MAD False Alarms Triggered: {false_positives_mad} ({fp_rate_mad:.2f}% FPR)")
    print(f"   Forecast False Alarms Triggered: {false_positives_fc} ({fp_rate_fc:.2f}% FPR)")
    print("-" * 75)
    
    # Loop and Benchmark Train Incidents
    print("Part 2: Evaluating Training Chaos Incident Matrix...")
    incident_files = glob.glob(os.path.join(TRAIN_INCIDENTS_DIR, "*.parquet"))
    
    results_matrix = []
    for f_path in incident_files:
        name = os.path.basename(f_path)
        
        # Evaluate using the Robust MAD detector
        mad_metric, mad_delay = evaluate_incident(mad_detector, baseline_df, f_path)
        mad_delay_str = f"{int(mad_delay)}s" if mad_delay is not None else "N/A"
        
        # Evaluate using the Adaptive Forecast detector
        fc_metric, fc_delay = evaluate_incident(forecast_detector, baseline_df, f_path)
        fc_delay_str = f"{int(fc_delay)}s" if fc_delay is not None else "N/A"
        
        results_matrix.append({
            "File Name": name[:30],
            "MAD Metric": mad_metric[:20],
            "MAD Delay": mad_delay_str,
            "Forecast Metric": fc_metric[:20],
            "Forecast Delay": fc_delay_str
        })
        
    df_matrix = pd.DataFrame(results_matrix)
    print(df_matrix.to_string(index=False))

if __name__ == "__main__":
    main()