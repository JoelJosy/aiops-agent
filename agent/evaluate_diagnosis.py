from langgraph.types import Command
import glob
import os
import pandas as pd

from agent.build_state import build_diagnosis_state
from agent.graph import graph

from detector.mad_detector import MADDetector
from detector.rootcause.analysis import FAULT_TO_ROOT_METRIC
from detector.evaluate_rootcause import get_fault_type

def run_incident_headless(graph, state, config, auto_approve=True):
    result = graph.invoke(
        state,
        config=config
    )

    snapshot = graph.get_state(config)

    if snapshot.interrupts:
        decision = "approved" if auto_approve else "rejected"
        result = graph.invoke(
            Command(resume=decision),
            config=config
        )
    else:
        result = snapshot.values

    return result

baseline_df = pd.read_parquet("data/baseline.parquet")
baseline_df.index = pd.to_datetime(baseline_df.index, utc=True)
mad_detector = MADDetector(persistence_steps=3)

incident_files = sorted(
    glob.glob("data/incidents/train/*.parquet") + 
    glob.glob("data/incidents/test/*.parquet")
)
# incident_files = [
#     "data/incidents/test/downstream_failure_fd739d70.parquet"
# ]

rows = []

for path in incident_files:

    print("\nRunning:", path)

    state = build_diagnosis_state(mad_detector, baseline_df, path)
    print("Build state top:", state["phase3_top_candidate"])

    config = {
        "configurable":{
            "thread_id": f"eval-{os.path.basename(path)}"
        }
    }

    result = run_incident_headless(graph, state, config, auto_approve=True)

    fault_type = get_fault_type(path)
    expected = FAULT_TO_ROOT_METRIC.get(fault_type, None) # type: ignore
    if expected is None:
        print(f"Skipping {fault_type}: no ground truth")
        continue

    print("\nFINAL DIAGNOSIS:")
    print("Expected:", expected)
    print("Phase3:", state["phase3_top_candidate"])
    print("LLM:", result["diagnosed_root_cause"])

    print("\nEvidence:")
    for e in result["evidence_gathered"]:
        print(e)

    rows.append({
        "file": os.path.basename(path),
        "expected": expected,
        "predicted": result["diagnosed_root_cause"],
        "correct": expected == result["diagnosed_root_cause"],
        "confidence": result["confidence"],
        "iterations": result["iterations"],
        "action": result["remediation_action"],
        "needs_more_evidence": result["needs_more_evidence"],
        "phase3_top_candidate": state["phase3_top_candidate"],
        "agent_agrees_with_phase3": result["diagnosed_root_cause"] == state["phase3_top_candidate"],
        "requires_approval": result["requires_approval"],

        "phase3_agreement": result["phase3_top_candidate"] == result["diagnosed_root_cause"],

        "approval_status": result["approval_status"],

        "remediation_status":
            result["remediation_result"]["status"] if result["remediation_result"]
            else None,
    })


df = pd.DataFrame(rows)
print(df)

print("\n========== Evaluation Summary ==========")
accuracy = df["correct"].mean() * 100

agreement = (df["agent_agrees_with_phase3"].mean() * 100)

print(f"""Ground Truth Accuracy:
        {accuracy:.2f}%

        Agreement with Phase 3:
        {agreement:.2f}%

        Average Confidence:
        {df["confidence"].mean():.3f}

        Average Iterations:
        {df["iterations"].mean():.2f}""")

escalated = df["needs_more_evidence"].sum()

total = len(df)

print(f"""Evidence escalation: {escalated}/{total} 
        incidents required additional evidence""")

full_iterations = (
    df["iterations"] == 3
).sum()


print(f"Maximum iteration cases: {full_iterations}/{total}")

print("\n========== Remediation Review ==========")

print(df[["file", "expected", "action", "confidence"]].to_string(index=False))


print(df[["file", "action", "requires_approval", "approval_status", "remediation_status"]])

print(pd.crosstab(df["expected"], df["predicted"]))