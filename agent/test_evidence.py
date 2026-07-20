from agent.tool_nodes import query_deploy_history


state = {
    "incident_window": {
        "start": "2026-07-20T18:40:00Z",
        "end": "2026-07-20T18:51:00Z"
    },
    "evidence_gathered": []
}


result = query_deploy_history(state)

print(result["evidence_gathered"])
