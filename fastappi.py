from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from scraper.scrap import primera_p, segunda_p, precios_ban, precios_p2p
from memory_cache import MemoryCache
import uvicorn
import asyncio
import json
import os
import logging
import time
from dotenv import load_dotenv

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

async def get_data_with_fallback(primary_func, fallback_func, cache_key):
    cached = MemoryCache.get(cache_key)
    if cached: return json.loads(cached)
    
    # Intento Primario
    data = await asyncio.to_thread(primary_func)
    if not data or "error" in data:
        # Fallback
        logger.warning(f"Primaria falló, usando fallback para {cache_key}")
        data = await asyncio.to_thread(fallback_func)
    
    if data and "error" not in data:
        MemoryCache.setex(name=cache_key, time=43200, value=json.dumps(data))
    return data

@appi.get("/")
async def root():
    return {"status": "ok", "message": "API working in memory mode"}

@appi.get("/api/v1/monedas")
async def consulta():
    return await get_data_with_fallback(primera_p, segunda_p, "monedas_data")

@appi.get("/api/v1/usd")
async def usd():
    data = await get_data_with_fallback(primera_p, segunda_p, "monedas_data")
    # Buscar especificamente USD en datos
    usd_data = next((item["USD"] for item in data.get("datos", []) if "USD" in item), None)
    
    if "valor_final_usd" in data:
        return {"usd": data["valor_final_usd"], "fecha": usd_data if usd_data else data.get("fecha")}
    if "usd" in data:
        return {"usd": data["usd"], "fecha": data.get("fecha")}
    return {"success": False, "error": "Could not fetch USD"}

@appi.get("/api/v1/eur")
async def eur():
    data = await get_data_with_fallback(primera_p, segunda_p, "monedas_data")
    # Buscar especificamente EUR en datos
    eur_data = next((item["EUR"] for item in data.get("datos", []) if "EUR" in item), None)
    
    if "valor_final_eur" in data:
        return {"eur": data["valor_final_eur"], "fecha": eur_data if eur_data else data.get("fecha")}
    if "eur" in data:
        return {"eur": data["eur"], "fecha": data.get("fecha")}
    return {"success": False, "error": "Could not fetch EUR"}

@appi.get("/api/v1/p2p")
async def p2p():
    cached = MemoryCache.get("pre_p2p")
    if cached: return json.loads(cached)
    try:
        data = await asyncio.to_thread(precios_p2p)
        if data:
            MemoryCache.setex(name="pre_p2p", time=43200, value=json.dumps(data))
        return data
    except Exception: return {"success": False, "error": "Service unavailable"}

@appi.get("/api/v1/tasa_inf")
async def tasa_inf():
    cached = MemoryCache.get("tasa_inf")
    if cached: return json.loads(cached)
    try:
        data = await asyncio.to_thread(precios_ban)
        if data:
            MemoryCache.setex(name="tasa_inf", time=43200, value=json.dumps(data))
        return data
    except Exception: return {"success": False, "error": "Service unavailable"}

if __name__ == "__main__":
    uvicorn.run("fastappi:appi", port=int(os.getenv('API_PORT', 8000)), reload=os.getenv('DEBUG', 'False').lower() == 'true')
