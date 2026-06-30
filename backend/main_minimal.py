#!/usr/bin/env python3
"""Test frontend directly without enhanced_rag causing crash"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

print("[APP] Initializing FastAPI app...")

app = FastAPI(
    title="Asistente de Integración Cultural - KubGU",
    description="Backend para soporte inteligente a estudiantes extranjeros",
    version="0.5.0"
)

print("[APP] Mounting static files...")
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "Backend is running but RAG module disabled due to compatibility issues"
    }

@app.get("/api/status")
async def api_status():
    return {"status": "operational"}

if __name__ == "__main__":
    import uvicorn
    print("[APP] Starting uvicorn on http://0.0.0.0:8000")
    print("[APP] Frontend will be at http://localhost:8000/frontend/")
    uvicorn.run(app, host="0.0.0.0", port=8000)
