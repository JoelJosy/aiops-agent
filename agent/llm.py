import requests


def call_llm(prompt: str):

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:7b",
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json()["response"]