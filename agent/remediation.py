from datetime import datetime, timezone
import subprocess

from agent.state import DiagnosisState

LOW_RISK_ACTIONS = {
    "flush_cache",
}

HIGH_RISK_ACTIONS = {
    "restart_service",
    "scale_out",
    "rollback_deploy",
}

SERVICE_NAME = "aiops-app"
DRY_RUN = True


def finalize_diagnosis(state: DiagnosisState) -> DiagnosisState:
    if state["needs_more_evidence"]:
        state["remediation_action"] = "none"
        
    action = state["remediation_action"]

    state["requires_approval"] = (action in HIGH_RISK_ACTIONS)
    state["approval_status"] = ("pending" if state["requires_approval"] else "approved")

    return state


def execute_remediation(state: DiagnosisState):
    action = state["remediation_action"]

    timestamp = datetime.now(timezone.utc).isoformat()


    if DRY_RUN:
        state["remediation_result"] = {
            "action": action,
            "status": "dry_run",
            "timestamp": timestamp
        }

        return state


    try:
        if action == "none": 
            state["remediation_result"] = {
                    "action": "none",
                    "status": "skipped",
                    "timestamp": timestamp
            }
            return state
        
        if action == "restart_service": 
            subprocess.run(
                ["docker","compose","restart",SERVICE_NAME],
                check=True,
                timeout=30
            )


        elif action == "flush_cache": 
            subprocess.run(
                ["docker","compose","exec","-T","redis","redis-cli","FLUSHALL"],
                check=True,
                timeout=15
            )

        else:
            raise ValueError(f"Unknown action {action}")
        
        status = "executed"


    except Exception as e:
        status = f"failed: {str(e)}"


    state["remediation_result"] = {
        "action": action,
        "status": status,
        "timestamp": timestamp
    }


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