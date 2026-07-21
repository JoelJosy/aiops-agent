from datetime import datetime, timezone
from agent.state import DiagnosisState

LOW_RISK_ACTIONS = {
    "flush_cache",
}

HIGH_RISK_ACTIONS = {
    "restart_service",
    "scale_out",
    "rollback_deploy",
}


def finalize_diagnosis(state: DiagnosisState) -> DiagnosisState:
    if state["needs_more_evidence"]:
        state["remediation_action"] = "none"
        
    action = state["remediation_action"]

    state["requires_approval"] = (action in HIGH_RISK_ACTIONS)
    state["approval_status"] = ("pending" if state["requires_approval"] else "approved")

    return state


def execute_remediation(state: DiagnosisState) -> DiagnosisState:
    action = state["remediation_action"]

    result = {
        "action": action,
        "status": "executed",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    state["remediation_result"] = result

    return state

def remediation_router(state: DiagnosisState):

    action = state["remediation_action"]

    if action == "none":
        return "finish"

    if state["requires_approval"]:
        return "approval"

    return "execute"

def route_after_approval(state: DiagnosisState):

    if state["approval_status"] == "approved":
        return "execute_remediation"

    return "reject_remediation"