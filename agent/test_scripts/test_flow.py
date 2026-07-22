from langgraph.types import Command
from agent.graph import graph
from agent.build_state import build_diagnosis_state
from detector.mad_detector import MADDetector
import pandas as pd
from agent.output import build_report

baseline_df = pd.read_parquet("data/baseline.parquet")
baseline_df.index = pd.to_datetime(baseline_df.index, utc=True)
mad_detector = MADDetector(persistence_steps=3)
incident_path = "data/incidents/test/downstream_failure_fd739d70.parquet"

state = build_diagnosis_state(mad_detector, baseline_df, incident_path)
print("Initial state:")
print(state)

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

snapshot = graph.get_state(config) # type: ignore

if snapshot.interrupts:

    print("\nGraph interrupted!")
    print("Interrupt data:")
    print(snapshot.interrupts[0].value)

    decision = input("\nApprove remediation? (approved/rejected): ")

    result = graph.invoke(
        Command(resume=decision),
        config=config # type: ignore
    )

else:
    print("\nGraph completed without approval.")
    result = snapshot.values


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
