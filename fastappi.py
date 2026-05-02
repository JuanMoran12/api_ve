from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from scraper.scrap import primera_p, segunda_p, tercera_p
from memory_cache import memory_cache
import uvicorn
import asyncio
import json
import os
import logging
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

appi = FastAPI()

logger = logging.getLogger(__name__)

cors_origins = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []

@appi.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

appi.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != [''] else [],
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type", "Authorization"]
)

@appi.on_event("startup")
async def startup_event():
    # Tarea de carga inicial simplificada
    logger.info("API iniciada en memoria")

@appi.get("/")
async def root():
    return {"status": "ok", "message": "API working in memory mode"}

@appi.get("/api/v1/monedas")
async def consulta():
    cache_key = "monedas_data"
    cached_data = memory_cache.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    try:
        data = await asyncio.to_thread(primera_p)
        memory_cache.setex(name=cache_key, time=43200, value=json.dumps(data))
        return data
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"success": False, "error": "Service unavailable"}

if __name__ == "__main__":
    uvicorn.run(
        "fastappi:appi",
        port=int(os.getenv('API_PORT', 8000)),
        reload=os.getenv('DEBUG', 'False').lower() == 'true'
    )
