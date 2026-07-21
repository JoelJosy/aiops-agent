from dataclasses import dataclass
from typing import Optional


@dataclass
class DiagnosisReport:
    root_cause: str
    confidence: float
    hypothesis: str
    action: str
    approval: str
    remediation: Optional[dict]
    iterations: int

def build_report(state):
    return DiagnosisReport(
        root_cause=state["diagnosed_root_cause"],
        confidence=state["confidence"],
        hypothesis=state["hypothesis"],
        action=state["remediation_action"],
        approval=state["approval_status"],
        remediation=state["remediation_result"],
        iterations=state["iterations"]
    )