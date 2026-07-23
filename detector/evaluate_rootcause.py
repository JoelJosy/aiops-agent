import os
import glob
import json
import pandas as pd
from detector.mad_detector import MADDetector
from detector.evaluate import evaluate_incident, BASELINE_PATH, INCIDENTS_LOG
from detector.rootcause.analysis import extract_events, rank_root_causes, FAULT_TO_ROOT_METRIC

def get_fault_type(file_path):
    base = os.path.basename(file_path).replace(".parquet", "")
    short_id = base.split("_")[-1].strip()
    with open(INCIDENTS_LOG) as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            if str(data.get("incident_id", "")).startswith(short_id):
                return data.get("fault_type")
    return None

def main():
    baseline_df = pd.read_parquet(BASELINE_PATH)
    baseline_df.index = pd.to_datetime(baseline_df.index, utc=True)
    mad_detector = MADDetector(persistence_steps=3)

    incident_files = sorted(
        glob.glob("data/incidents/train/*.parquet") + glob.glob("data/incidents/test/*.parquet")
    )

    rows = []
    for f_path in incident_files:
        fault_type = get_fault_type(f_path)
        expected_metric = FAULT_TO_ROOT_METRIC.get(fault_type) # type: ignore
        if expected_metric is None:
            continue  

        _, _, inc_results, raw_window_df = evaluate_incident(mad_detector, baseline_df, f_path)
        events = extract_events(inc_results, raw_window_df)
        ranked = rank_root_causes(events, raw_window_df) 
        predicted = ranked[0]["metric"] if ranked else None

        rows.append({
            "file": os.path.basename(f_path),
            "fault_type": fault_type,
            "expected": expected_metric,
            "predicted": predicted,
            "correct": predicted == expected_metric,
            "confidence": ranked[0]["confidence"] if ranked else None,
        })

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    acc = df["correct"].mean() * 100
    # print(f"\nRoot-cause accuracy: {df['correct'].sum()}/{len(df)} = {acc:.1f}%")

if __name__ == "__main__":
    main()