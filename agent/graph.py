from langgraph.graph import StateGraph, START, END

from agent.state import DiagnosisState
from agent.diagnosis import diagnose, confidence_check
from agent.remediation import finalize_diagnosis
from agent.tool_nodes import (
    summarize_metric_evidence,
    query_recent_app_logs,
    query_deploy_history,
    query_incident_history,
    investigate_additional_metrics,
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
builder.add_edge("finalize", END)

graph = builder.compile()
