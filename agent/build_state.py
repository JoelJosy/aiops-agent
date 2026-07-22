from typing import cast
import numpy as np
import pandas as pd

from agent.state import DiagnosisState

from detector.evaluate import evaluate_incident
from detector.rootcause.analysis import (
    extract_events,
    rank_root_causes
)

def make_json_serializable(obj):
    """Recursively convert objects to JSON-serializable types."""
    if isinstance(obj, np.generic):
        return obj.item()

    if isinstance(obj, pd.Timestamp):
        return obj.to_pydatetime()

    if isinstance(obj, dict):
        return {
            k: make_json_serializable(v)
            for k, v in obj.items()
        }

    if isinstance(obj, list):
        return [
            make_json_serializable(v)
            for v in obj
        ]

    return obj


def build_diagnosis_state(detector, baseline_df, incident_file_path) -> DiagnosisState:
    """Builds the diagnosis state from the incident data and detector configuration."""

    _, _, incident_results, raw_window = evaluate_incident(detector, baseline_df, incident_file_path)
    events = extract_events(incident_results, raw_window)
    ranked_candidates = rank_root_causes(events, raw_window)

    top_candidate = ranked_candidates[0] if ranked_candidates else None
    if top_candidate:
        confidence_gap = (
            top_candidate["confidence"] - ranked_candidates[1]["confidence"]
            if len(ranked_candidates) > 1
            else 1.0
        )
    else:
        confidence_gap = 0.0

    # candidates close enough to challenge the winner
    comparison_candidates = []
    if top_candidate:
        top_conf = top_candidate["confidence"]

        comparison_candidates = [
            c for c in ranked_candidates
            if top_conf - c["confidence"] <= 0.15
        ]


    if events:
        start = min(e["onset"] for e in events)
        end = max(e["offset"] for e in events)
    else:
        start = raw_window.index.min()
        end = raw_window.index.max()


    state = {

        "incident_window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "metrics": {},
            "alerts": [
                e["metric"]
                for e in events
            ],
        },

        "ranked_candidates": make_json_serializable(ranked_candidates),
        "phase3_top_candidate": make_json_serializable(top_candidate["metric"] 
                                                       if top_candidate else None),
        "phase3_candidate_comparison": make_json_serializable(comparison_candidates),
        "phase3_confidence_gap": make_json_serializable(confidence_gap),
        "evidence_gathered": [],
        "hypothesis": None,
        "confidence": 0.0,
        "iterations": 0,
        "remediation_action": "none",
        "requires_approval": False,
        "approval_status": None,
        "remediation_result": None,
        "diagnosed_root_cause": None,
        "needs_more_evidence": False,
        "reasoning": "",
    }

    return cast(DiagnosisState, state)