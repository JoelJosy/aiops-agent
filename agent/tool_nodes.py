from datetime import timedelta, datetime
import os
from pathlib import Path
import json
import pandas as pd

from agent.utils import load_logs, query_deploys
from detector.metric_queries import QUERIES
from detector.prometheus_api import fetch_metric
from agent.state import DiagnosisState
from service.logger import LOG_FILE

def summarize_metric_evidence(state: DiagnosisState) -> DiagnosisState:
    """Summarizes quantitative evidence from Prometheus API for each ranked candidate."""

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
                "peak_time": str(df["value"].idxmax()),
                "peak_change": float(df["value"].max() - df["value"].iloc[0])
            }
        }
        state["evidence_gathered"].append(evidence)

    return state

def query_recent_app_logs(state):
    """
    Collects application log evidence from the incident time window.
    Summarizes event frequency and attaches representative log samples.
    """

    start = state["incident_window"]["start"]
    end = state["incident_window"]["end"]

    logs = load_logs(start, end)

    event_counts = {}
    samples = []

    for log in logs:
        event = log.get("event")

        if event:
            event_counts[event] = (
                event_counts.get(event, 0) + 1
            )

            if event in {
                "redis_get",
                "redis_set",
                "downstream_call",
                "request"
            } and len(samples) < 10:
                samples.append({
                    "timestamp": log["timestamp"],
                    "event": event,
                    "details": {
                        k: v
                        for k, v in log.items()
                        if k not in {"timestamp", "level", "message", "event"}
                    }
                })

    state["evidence_gathered"].append({
        "source":"application_logs",
        "events":event_counts,
        "samples":samples
    })

    return state

def query_deploy_history(state):
    """
    Checks whether any deployments happened close to the incident window.
    Adds deployment context as evidence for diagnosis.
    """

    start = datetime.fromisoformat(
        state["incident_window"]["start"].replace("Z", "+00:00")
    )
    end = datetime.fromisoformat(
        state["incident_window"]["end"].replace("Z", "+00:00")
    )
    

    # look 15 minutes before and after incident
    search_start = start - timedelta(minutes=15)
    search_end = end + timedelta(minutes=15)


    deploys = query_deploys(search_start, search_end)


    evidence = {
        "source": "deploy_history",
        "recent_deploys": deploys,
        "count": len(deploys)
    }

    state["evidence_gathered"].append(evidence)


    return state