from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from memory_cache import MemoryCache
import uvicorn
import json
import os
import logging
import time
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

logger = logging.getLogger(__name__)

cors_origins = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != [''] else [],
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type", "Authorization"]
)

def read_cache(key):
    cached = MemoryCache.get(key)
    if cached:
        return json.loads(cached)
    return None

@app.get("/")
async def root():
    return {"status": "ok", "message": "API working with Upstash Redis cache"}

@app.get("/api/v1/monedas")
async def consulta():
    data = read_cache("monedas_data")
    if not data:
        return JSONResponse(status_code=503, content={"success": False, "message": "No data available. Scraper has not run yet or cache expired."})
    return data

@app.get("/api/v1/usd")
async def usd():
    data = read_cache("monedas_data")
    if not data:
        return JSONResponse(status_code=503, content={"success": False, "message": "No USD data available. Scraper has not run yet or cache expired."})

    usd_data = next((item["USD"] for item in data.get("datos", []) if "USD" in item), None)
    
    if "valor_final_usd" in data:
        return {"usd": data["valor_final_usd"], "fecha": usd_data if usd_data else data.get("fecha")}
    if "usd" in data:
        return {"usd": data["usd"], "fecha": data.get("fecha")}
    return JSONResponse(status_code=404, content={"success": False, "message": "USD rate not found in cached data"})

@app.get("/api/v1/eur")
async def eur():
    data = read_cache("monedas_data")
    if not data:
        return JSONResponse(status_code=503, content={"success": False, "message": "No EUR data available. Scraper has not run yet or cache expired."})

    eur_data = next((item["EUR"] for item in data.get("datos", []) if "EUR" in item), None)
    
    if "valor_final_eur" in data:
        return {"eur": data["valor_final_eur"], "fecha": eur_data if eur_data else data.get("fecha")}
    if "eur" in data:
        return {"eur": data["eur"], "fecha": data.get("fecha")}
    return JSONResponse(status_code=404, content={"success": False, "message": "EUR rate not found in cached data"})

@app.get("/api/v1/convert")
async def convert(
    currency: str = Query(..., description="Currency to convert: usd, eur, or ves"),
    amount: float = Query(..., gt=0, description="Amount to convert")
):
    currency = currency.lower().strip()
    if currency not in ("usd", "eur", "ves"):
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid currency. Use: usd, eur, or ves"})

    data = read_cache("monedas_data")
    if not data:
        return JSONResponse(status_code=503, content={"success": False, "message": "No exchange rate data available. Scraper has not run yet or cache expired."})

    usd_rate = data.get("valor_final_usd") or data.get("usd")
    eur_rate = data.get("valor_final_eur") or data.get("eur")
    fecha = data.get("fecha")

    if not usd_rate and not eur_rate:
        return JSONResponse(status_code=404, content={"success": False, "message": "Exchange rates not found in cache"})

    try:
        usd_rate = float(usd_rate)
        eur_rate = float(eur_rate) if eur_rate else None
    except (TypeError, ValueError):
        return JSONResponse(status_code=500, content={"success": False, "message": "Invalid rate format in cache"})

    result = {"success": True, "date": fecha, "amount": amount, "from": currency}

    if currency == "usd":
        result["to"] = "ves"
        result["result"] = round(amount * usd_rate, 2)
        result["rate"] = usd_rate
        if eur_rate:
            result["eur_equivalent"] = round(amount * (usd_rate / eur_rate), 2)
    elif currency == "eur":
        if not eur_rate:
            return JSONResponse(status_code=404, content={"success": False, "message": "EUR rate not available"})
        result["to"] = "ves"
        result["result"] = round(amount * eur_rate, 2)
        result["rate"] = eur_rate
        result["usd_equivalent"] = round(amount * (eur_rate / usd_rate), 2)
    elif currency == "ves":
        result["usd"] = {"to": "usd", "result": round(amount / usd_rate, 2), "rate": usd_rate}
        if eur_rate:
            result["eur"] = {"to": "eur", "result": round(amount / eur_rate, 2), "rate": eur_rate}

    return result

@app.get("/api/v1/tasa_inf")
async def tasa_inf():
    data = read_cache("tasa_inf")
    if not data:
        return JSONResponse(status_code=503, content={"success": False, "message": "No bank rates available. Scraper has not run yet or cache expired."})
    return data

if __name__ == "__main__":
    uvicorn.run("app:app", port=int(os.getenv('API_PORT', 8000)), reload=os.getenv('DEBUG', 'False').lower() == 'true')
