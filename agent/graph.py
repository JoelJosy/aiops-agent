from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import DiagnosisState
from agent.diagnosis import diagnose, confidence_check
from agent.remediation import finalize_diagnosis, execute_remediation, remediation_router, route_after_approval
from agent.tool_nodes import (
    summarize_metric_evidence,
    query_recent_app_logs,
    query_deploy_history,
    query_incident_history,
    investigate_additional_metrics,
    approval_gate
)

# Init graph builder 
builder = StateGraph(DiagnosisState)

# Nodes
builder.add_node("summarize_metric_evidence", summarize_metric_evidence)
builder.add_node("query_recent_app_logs", query_recent_app_logs)
builder.add_node("query_deploy_history", query_deploy_history)
builder.add_node("query_incident_history", query_incident_history)
builder.add_node("investigate_additional_metrics", investigate_additional_metrics)
builder.add_node("diagnose", diagnose)
builder.add_node("finalize", finalize_diagnosis)
builder.add_node("approval_gate", approval_gate)
builder.add_node("execute_remediation", execute_remediation)

# Edges
builder.add_edge(START, "summarize_metric_evidence")
builder.add_edge("summarize_metric_evidence", "query_recent_app_logs")
builder.add_edge("query_recent_app_logs", "query_deploy_history")
builder.add_edge("query_deploy_history", "query_incident_history")
builder.add_edge("query_incident_history", "diagnose")

builder.add_conditional_edges("diagnose", confidence_check, {
    "finalize": "finalize",
    "gather_evidence": "investigate_additional_metrics",
})

builder.add_edge("investigate_additional_metrics", "diagnose")

builder.add_conditional_edges("finalize", remediation_router, {
    "approval": "approval_gate",
    "execute": "execute_remediation",
    "finish": END
})

builder.add_conditional_edges("approval_gate", route_after_approval, {
    "execute_remediation": "execute_remediation",
    "reject_remediation": END
})

builder.add_edge("execute_remediation", END)


memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
