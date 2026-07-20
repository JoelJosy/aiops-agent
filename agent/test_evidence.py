from agent.evidence import query_recent_logs


state = {
    "incident_window": {
        "start": "2026-07-20T18:45:00Z",
        "end": "2026-07-20T18:51:00Z"
    },
    "evidence_gathered": []
}


result = query_recent_logs(state)

print(result["evidence_gathered"])
