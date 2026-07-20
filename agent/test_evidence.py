from agent.tool_nodes import query_incident_history


state = {
    "ranked_candidates": [
        {
            "metric":"redis_average_latency_seconds",
            "confidence":0.6
        }
    ],
    "evidence_gathered":[]
}


result = query_incident_history(state) #type: ignore

print(result["evidence_gathered"])