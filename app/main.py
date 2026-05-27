from fastapi import FastAPI

app = FastAPI(title="Moxo Workflow Agent", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
