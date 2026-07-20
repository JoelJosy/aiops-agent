from datetime import timedelta
from detector.metric_queries import QUERIES
from detector.prometheus_api import fetch_metric
from agent.state import DiagnosisState

def summarize_metric_evidence(state: DiagnosisState) -> DiagnosisState:
    """Summarizes evidence for each ranked candidate."""

    for candidate in state["ranked_candidates"]:
        if candidate["confidence"] < 0.3:
            continue

        start = candidate["onset"] - timedelta(seconds=30)
        end = candidate["offset"] + timedelta(seconds=30)

        df = fetch_metric(QUERIES[candidate["metric"]], start, end)

        evidence = {
            "source": "metric_analysis",
            "metric": candidate["metric"],
            "confidence": candidate["confidence"],
            "prior": candidate["prior"],
            "correlation": candidate["corr"],
            "summary": {
                "min": float(df["value"].min()),
                "max": float(df["value"].max()),
                "mean": float(df["value"].mean()),
                "first": float(df["value"].iloc[0]),
                "last": float(df["value"].iloc[-1]),
                "change": float(df["value"].iloc[-1] - df["value"].iloc[0]),
                "peak_time": str(df["value"].idxmax()),
            }
        }
        state["evidence_gathered"].append(evidence)

    return state
