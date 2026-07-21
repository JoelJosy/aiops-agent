from agent.diagnosis import diagnose


state = {

    "ranked_candidates":[
        {
            "metric":"redis_average_latency_seconds",
            "confidence":0.62,
            "prior":0.5,
            "corr":0.92
        }
    ],

    "evidence_gathered":[

        {
            "source":"metric_analysis",
            "metric":"redis_average_latency_seconds",
            "summary":{
                "first":0.006,
                "last":0.5,
                "change":0.49
            }
        },

        {
            "source":"incident_history",
            "similar_cases":[
                {
                    "fault_type":"redis_latency",
                    "params":{
                        "delay_ms":500
                    }
                }
            ]
        }
    ],

    "hypothesis":None,
    "confidence":0,
    "iterations":0,
    "remediation_action":None,
    "diagnosed_root_cause":None
}


result = diagnose(state) #type: ignore


print(result["hypothesis"])
print(result["confidence"])
print(result["remediation_action"])