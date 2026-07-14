from fastapi import FastAPI

from routes import router

app = FastAPI(
    title="AIOps Agent Service",
    version="0.1.0",
)

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}