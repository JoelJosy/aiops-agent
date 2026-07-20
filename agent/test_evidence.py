from agent.evidence import summarize_metric_evidence
from datetime import datetime, timezone


state = {
    "incident_window": {
        "start": "2026-07-15T20:03:00Z",
        "end": "2026-07-15T20:07:00Z",
        "metrics": {},
        "alerts": []
    },

    "ranked_candidates": [
        {
            "metric": "process_cpu_rate",
            "confidence": 0.427,
            "prior": 0.25,
            "corr": 0.92,
            "onset": datetime(2026,7,15,20,6,30,tzinfo=timezone.utc),
            "offset": datetime(2026,7,15,20,6,30,tzinfo=timezone.utc),
            "peak_score": 117
        },
        {
            "metric": "downstream_average_latency_seconds",
            "confidence": 0.535,
            "prior": 0.25,
            "corr": 0.95,
            "onset": datetime(2026,7,15,20,3,tzinfo=timezone.utc),
            "offset": datetime(2026,7,15,20,6,tzinfo=timezone.utc),
            "peak_score": 46
        }
    ],

    "evidence_gathered": []
}


result = summarize_metric_evidence(state) # type: ignore


for evidence in result["evidence_gathered"]:
    print(evidence)