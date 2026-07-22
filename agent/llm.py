import time
import requests
import boto3
from botocore.config import Config


LLM_PROVIDER = "nova_pro"  # Options: "ollama", "nova_lite", "nova_pro", "llama3"

bedrock = boto3.client(
    "bedrock-runtime",
    region_name="ap-south-1",
    config=Config(
        read_timeout=120
    )
)

MODELS = {

    "nova_lite": "global.amazon.nova-2-lite-v1:0",
    "llama3" : "meta.llama3-70b-instruct-v1:0",
    "nova_pro": "apac.amazon.nova-pro-v1:0",
}


def call_llm(prompt: str):
    start = time.time()
    if LLM_PROVIDER == "ollama":
        result = call_ollama(prompt)

    elif LLM_PROVIDER in MODELS:
        result = call_bedrock(prompt, MODELS[LLM_PROVIDER])

    else:
        raise ValueError(
            f"Unknown LLM provider {LLM_PROVIDER}"
        )

    latency=time.time()-start
    print(f"{LLM_PROVIDER} latency: {latency:.2f}s")

    return result


def call_ollama(prompt: str):

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:7b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature":0
            }
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json()["response"]



def call_bedrock(prompt: str, model_id: str):
    response = bedrock.converse(
        modelId=model_id,
        messages=[
            {
                "role":"user",
                "content":[
                    {
                        "text":prompt
                    }
                ]
            }
        ],
        inferenceConfig={
            "maxTokens":700,
            "temperature":0,
            "topP":1
        }
    )

    return (
        response["output"]
        ["message"]
        ["content"][0]
        ["text"]
    )
