import pandas as pd
import numpy as np
from detector.rootcause.topology import DEPENDENCY_PRIOR
from detector.mad_detector import DRIFT_METRICS

FAULT_TO_ROOT_METRIC = {
    "redis_latency": "redis_average_latency_seconds",
    "redis_outage": "redis_average_latency_seconds",  
    "app_outage": "app_availability",
    "downstream_latency": "downstream_average_latency_seconds",
    "downstream_failure": "downstream_error_rate",
    "cpu_spike": "process_cpu_rate",
    "memory_leak": "process_resident_memory_bytes",
    "memory_spike": None, 
}

HARD_OUTAGE_METRICS = {"app_availability"}

def extract_events(inc_results: pd.DataFrame, full_window_df: pd.DataFrame) -> list[dict]:
    """Extracts a list of all metrics that triggered anomalies, along with their onset, offset, and peak score."""
    events = []
    for col in inc_results.columns:
        if col.endswith("_anomaly"):
            metric = col.replace("_anomaly", "")
            flagged = inc_results[inc_results[col] == 1]
            if not flagged.empty:
                score_col = f"{metric}_score"

                if metric in DRIFT_METRICS and full_window_df is not None:
                    onset_frac = detect_growth_onset(full_window_df[metric])
                    n = len(full_window_df)
                    onset_idx = min(int(onset_frac * n), n - 1)
                    onset_time = full_window_df.index[onset_idx]
                else:
                    onset_time = flagged.index.min()

                events.append({
                    "metric": metric,
                    "onset": onset_time,
                    "offset": flagged.index.max(),
                    "peak_score": inc_results.loc[flagged.index, score_col].max() if score_col in inc_results else None,
                })
    return events


def best_lag_correlation(series_a: pd.Series, series_b: pd.Series, max_lag_steps=4):
    """Returns (best_lag, correlation) — best_lag > 0 means series_a leads series_b."""

    std_a = series_a.std()
    std_b = series_b.std()

    # Constant signals have undefined correlation.
    if pd.isna(std_a) or pd.isna(std_b):
        return 0, 0.0

    if std_a < 1e-9 or std_b < 1e-9:
        return 0, 0.0

    # normalize series
    a = (series_a - series_a.mean()) / (series_a.std() + 1e-9)
    b = (series_b - series_b.mean()) / (series_b.std() + 1e-9)

    best_lag, best_corr = 0, 0.0
    # upto 4 steps, 4 is 4 * 30s = 2 minute window
    for lag in range(-max_lag_steps, max_lag_steps + 1):
        shifted = b.shift(-lag)
        corr = a.corr(shifted)

        if pd.notna(corr) and abs(corr) > abs(best_corr):
            best_lag, best_corr = lag, corr

    return best_lag, best_corr



def rank_root_causes(events: list[dict], full_window_df: pd.DataFrame) -> list[dict]:
    if len(events) == 1:
        ev = events[0]
        return [{
            "metric": ev["metric"], "confidence": 1.0, "prior": 1.0, "corr": 1.0, "onset_rank": 1.0,
            "onset": ev["onset"], "offset": ev["offset"], "peak_score": ev["peak_score"],
            "explains": [], "reason": "sole_event",
        }]

    hard_hit = next((e for e in events if e["metric"] in HARD_OUTAGE_METRICS), None)
    if hard_hit:
        return [{
            "metric": hard_hit["metric"], "confidence": 1.0, "prior": 1.0, "corr": 1.0, "onset_rank": 1.0,
            "onset": hard_hit["onset"], "offset": hard_hit["offset"], "peak_score": hard_hit["peak_score"],
            "explains": [], "reason": "hard_outage_signal",
        }]

    candidates = []
    for ev in events:
        metric = ev["metric"]
        prior_targets = DEPENDENCY_PRIOR.get(metric, {}).get("can_cause", [])
        explained = [e for e in events if e["metric"] in prior_targets]
        prior_score = len(explained) / max(1, len(events) - 1)

        corr_scores = []
        for other in explained:
            series_a = full_window_df[metric].diff().fillna(0) if metric in DRIFT_METRICS else full_window_df[metric]
            lag, corr = best_lag_correlation(series_a, full_window_df[other["metric"]])
            if lag >= 0:
                corr_scores.append(abs(corr))
        corr_score = np.mean(corr_scores) if corr_scores else 0.0

        onset_rank = 1.0 / (1 + (ev["onset"] - min(e["onset"] for e in events)).total_seconds() / 30)

        confidence = 0.5 * prior_score + 0.35 * corr_score + 0.15 * onset_rank

        print("Root cause candidate:", metric)
        print(f"  prior={prior_score:.2f} corr={corr_score:.2f} onset={onset_rank:.2f} -> conf={confidence:.3f}")

        candidates.append({
            "metric": metric,
            "confidence": round(confidence, 3),
            "prior": round(prior_score, 3),
            "corr": round(float(corr_score), 3),
            "onset_rank": round(onset_rank, 3),
            "onset": ev["onset"],
            "offset": ev["offset"],
            "peak_score": ev["peak_score"],
            "explains": [e["metric"] for e in explained],
        })

    return sorted(candidates, key=lambda c: -c["confidence"])


def detect_growth_onset(series):
    """
    Detect abnormal change in growth rate.
    Used for metrics like memory where normal drift exists.
    """

    values = series.values

    if len(values) < 5:
        return 1.0

    velocity = np.diff(values)

    acceleration = np.diff(velocity)

    median = np.median(acceleration)
    mad = np.median(np.abs(acceleration - median))

    threshold = median + 3 * mad

    for i, change in enumerate(acceleration):
        if abs(change) > threshold:
            return (i + 2) / len(values)

    return 1.0