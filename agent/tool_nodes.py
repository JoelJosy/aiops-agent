from datetime import timedelta, datetime
from langgraph.types import interrupt

from agent.utils import load_incident_history, load_logs, query_deploys
from detector.metric_queries import QUERIES
from detector.prometheus_api import fetch_metric
from agent.state import DiagnosisState
from detector.rootcause.analysis import FAULT_TO_ROOT_METRIC
from service.logger import LOG_FILE
from agent.utils import get_related_metrics

def summarize_metric_evidence(state: DiagnosisState) -> DiagnosisState:
    """Summarizes quantitative evidence from Prometheus API for each ranked candidate."""

    for candidate in state["ranked_candidates"]:
        if candidate["confidence"] < 0.3:
            continue

        start = candidate["onset"] - timedelta(seconds=30)
        end = candidate["offset"] + timedelta(seconds=30)

        df = fetch_metric(QUERIES[candidate["metric"]], start, end)

        if df.empty:
            continue

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

def query_incident_history(state: DiagnosisState):

    history = load_incident_history()

    if not history:
        return state


    # Metrics detected in current incident
    current_metrics = {
        c["metric"]
        for c in state["ranked_candidates"]
    }


    matches = []

    for incident in history:

        # use fault type as historical signature
        fault_type = incident["fault_type"]

        similarity = 0.0

        expected_metric = FAULT_TO_ROOT_METRIC.get(fault_type)
        expected = {expected_metric} if expected_metric else set()


        if expected:
            overlap = current_metrics.intersection(expected)

            similarity = len(overlap) / len(expected)


        if similarity > 0:
            matches.append({
                "fault_type": fault_type,
                "similarity": round(similarity,2),
                "occurred_at": incident["start"],
                "params": incident["params"]
            })


    matches = sorted(
        matches,
        key=lambda x: -x["similarity"]
    )[:3]


    state["evidence_gathered"].append({
        "source": "incident_history",
        "similar_cases": matches
    })


    return state

def investigate_additional_metrics(state: DiagnosisState) -> DiagnosisState:
    """Escalation node: expand investigation to metrics topologically related
    to the top candidate. Used only if the top candidate is not conclusive and more evidence is needed."""

    if not state["ranked_candidates"]:
        return state

    top_candidate = state["ranked_candidates"][0]["metric"]
    already_checked = {c["metric"] for c in state["ranked_candidates"]}
    related = get_related_metrics(top_candidate) - already_checked

    if not related:
        state["evidence_gathered"].append({
            "source": "extended_metrics",
            "note": f"no topologically related metrics to check for {top_candidate}",
        })
        return state

    start = datetime.fromisoformat(state["incident_window"]["start"].replace("Z","+00:00")) - timedelta(minutes=10)
    end = datetime.fromisoformat(state["incident_window"]["end"].replace("Z","+00:00"))


    findings = []
    for metric in related:
        if metric not in QUERIES:
            continue
        df = fetch_metric(QUERIES[metric], start, end)
        if df.empty:
            continue
        findings.append({
            "metric": metric,
            "min": float(df["value"].min()),
            "max": float(df["value"].max()),
            "mean": float(df["value"].mean()),
            "first": float(df["value"].iloc[0]),
            "last": float(df["value"].iloc[-1]),
            "change": float(df["value"].iloc[-1] - df["value"].iloc[0])
        })

    state["evidence_gathered"].append({
        "source": "extended_metrics",
        "reason": f"related to top candidate {top_candidate}",
        "findings": findings,
    })
    return state

def approval_gate(state: DiagnosisState) -> DiagnosisState:
    """
    Human approval before executing high-risk remediation.
    """

    decision = interrupt({
        "recommended_action": state["remediation_action"],
        "root_cause": state["diagnosed_root_cause"],
        "confidence": state["confidence"],
        "hypothesis": state["hypothesis"],
        "reasoning": state["reasoning"],
    })

    state["approval_status"] = decision

    return state

