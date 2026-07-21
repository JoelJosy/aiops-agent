from langgraph.types import Command
from agent.graph import graph
from datetime import datetime, timezone

from agent.output import build_report

state = {

    "incident_window": {
        "start": "2026-07-20T18:49:15Z",
        "end": "2026-07-20T18:50:15Z",
        "metrics": {},
        "alerts": []
    },

    "ranked_candidates": [
    {
        "metric": "redis_average_latency_seconds",
        "confidence": 0.62,
        "prior": 0.5,
        "corr": 0.92,
        "onset": datetime(
            2026, 7, 20, 18, 49, 20,
            tzinfo=timezone.utc
        ),
        "offset": datetime(
            2026, 7, 20, 18, 50, 0,
            tzinfo=timezone.utc
        )
    }
    ],

    "evidence_gathered": [
        {
            "source": "metric_analysis",
            "metric": "redis_average_latency_seconds",
            "summary": {
                "first": 0.006,
                "last": 0.5,
                "change": 0.49
            }
        }
    ],

    "hypothesis": None,
    "confidence": 0.0,

    "iterations": 0,

    "remediation_action": None,
    "requires_approval": False,

    "approval_status": None,
    "remediation_result": None,

    "diagnosed_root_cause": None,
    "needs_more_evidence": False,
    "reasoning": ""
}

config = {
    "configurable": {
        "thread_id": "test-incident-001"
    }
}


print("Running graph...\n")

result = graph.invoke(
    state, # type: ignore
    config=config # type: ignore
)

print("\nGraph interrupted!")

snapshot = graph.get_state(config) # type: ignore

print("Interrupt data:")
print(snapshot)


decision = input(
    "\nApprove remediation? (approved/rejected): "
)


result = graph.invoke(
    Command(resume=decision),
    config=config # type: ignore
)


report = build_report(result)

print("\nFinal Diagnosis")
print("----------------")
print(f"Root Cause: {report.root_cause}")
print(f"Confidence: {report.confidence}")
print(f"Hypothesis: {report.hypothesis}")
print(f"Action: {report.action}")
print(f"Approval: {report.approval}")
print(f"Iterations: {report.iterations}")
print(f"Remediation: {report.remediation}")
