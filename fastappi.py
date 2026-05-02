from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from scraper.scrap import primera_p, segunda_p, play_primera
from pydantic import BaseModel
from typing import Text, Optional
from bd import *
from memory_cache import memory_cache
import uvicorn
import asyncio
from datetime import datetime
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

    if process_time > 2.0:
        logger.warning(f"Peticion Lenta: {request.method} {request.url.path} tomó {process_time:.4f}s")
    elif response.status_code >= 400:
        logger.error(f"Peticion fallida: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
    elif process_time > 1.0:
        logger.info(f"Peticion: {request.method} {request.url.path} tomó {process_time:.4f}s")

    return response

appi.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != [''] else [],
    allow_methods=["GET"],
    allow_headers=[
        "Accept",
        "Content-Type",
        "Authorization",
        "X-RapidAPI-Key",
        "X-RapidAPI-Host"
    ]
)

async def monedas():
    try:
        data_from_db = await play_primera()
        cache_key = "monedas_data"
        memory_cache.setex(name=cache_key, time=43200, value=json.dumps(data_from_db))
        logger.info("Datos de monedas almacenados en la caché en memoria.")
    except Exception as e:
        logger.error(f"Error al guardar en memoria: {e}")

@appi.on_event("startup")
async def startup_event():
    try:
        conexion_pool = await asyncio.to_thread(pool.get_connection)
        await asyncio.to_thread(crear_tablas, conexion_pool)
        asyncio.create_task(monedas())
        logger.info("Tarea de carga de monedas iniciada en segundo plano")
    except Exception as e:
        logger.critical("error en el startup", e)
    finally:
        if 'conexion_pool' in locals() and conexion_pool:
            await asyncio.to_thread(conexion_pool.close)

@appi.get("/")
async def primera():
    return {"status": "ok", "message": "API working"}

@appi.get("/api/v1/monedas")
async def consulta():
    cache_key = "monedas_data"
    cached_data = memory_cache.get(cache_key)

    if cached_data:
        return json.loads(cached_data)

    try:
        data_from_db = await play_primera()
        if isinstance(data_from_db, dict) and "error" in data_from_db:
            return {
                "success": False,
                "error": {
                    "status_code": "503",
                    "message": "Service temporarily unavailable",
                    "details": "Unable to fetch currency data from external service. Please try again later."
                }
            }
        
        if data_from_db:
            memory_cache.setex(name=cache_key, time=43200, value=json.dumps(data_from_db))
            logger.info(f"Datos de {cache_key} almacenados en la caché en memoria.")
        
        return data_from_db
    except Exception as e:
        logger.error(f"Error al obtener datos: {e}")
        return {
            "success": False,
            "error": {
                "status_code": "503",
                "message": "Service temporarily unavailable",
                "details": "Unable to fetch currency data from external service. Please try again later."
            }
        }

@appi.get("/api/v1/usd")
async def usd(date: str | None = None, source: str | None = None,
              convert : str | None = None, value: float | None = None,
              conexion: mariadb.Connection = Depends(get_db_connection)):

    fecha_obj = None
    if date:
        formatos = ["%Y-%m-%d", "%d-%m-%Y"]
        fecha_obj = None
        for fmt in formatos:
            try:
                fecha_obj = datetime.strptime(date, fmt).date()
                break
            except ValueError:
                continue
        if not fecha_obj:
            return {
                  "success": False,
                  "error": {
                    "status_code": "400",
                    "message": "Date format invalide",
                    "details": "Use one of the formats: yyyy-mm-dd (2025-08-07) or dd-mm-yyyy (07-08-2025) do not use {fecha}"
                  }
            }

    if fecha_obj and source:
        data_from_db = await asyncio.to_thread(buscar_fecha, conexion, str(fecha_obj), "usd", source)

        if convert and value is not None:
            if not data_from_db or "update_price" not in data_from_db:
                return {"success": False,
                            "error": {
                                "status_code": "404",
                                "message": "USD price data not found",
                                "details": f"No data available for date {fecha_obj} from source {source}"
                            }}

            try:
                precio_con = float(data_from_db["update_price"])
                if precio_con <= 0:
                    return {"success": False,
                            "error": {
                                "status_code": "400",
                                "message": "USD price data not found",
                                "details": f"No data available for date {fecha_obj} from source {source}"
                            }}

                if convert == "bs":
                    resultado = precio_con * value
                    return {"bs_amount": round(resultado, 2), "usd": value, "date": data_from_db["fecha"],
                     "usd": data_from_db["update_price"], "source" : data_from_db["source"]}
                elif convert == "usd":
                    resultado = value / precio_con
                    return {"usd_amount": round(resultado, 2), "bs" : value, "date": data_from_db["update_date"], "usd": data_from_db["update_price"], "source" : data_from_db["source"]}
                else:
                    return {
                        "success": False,
                        "error": {
                            "status_code": "400",
                            "message": "Invalid Parameter",
                            "details": "Invalid Parameter 'convert' Use 'bs' or 'usd'"
                        }
                    }
            except (ValueError, TypeError) as e:
                return {
                    "success": False,
                    "error": {
                        "status_code": "400",
                        "message": "Conversion Error",
                        "details": f"Conversion Error: {str(e)}"
                    }
                }

        return data_from_db

    elif fecha_obj:
        data_from_db = await asyncio.to_thread(buscar_fecha, conexion, str(fecha_obj), "usd")
        return data_from_db

    pre = await asyncio.to_thread(leer_usd, conexion, source, str(fecha_obj) if fecha_obj else None)

    if convert and value is not None:
        if not pre or "update_price" not in pre:
            return {"success": False,
                    "error": {
                        "status_code": "404",
                        "message": "USD price data not found",
                        "details": f"No data available for date {fecha_obj} from source {source}"
                    }}

        try:
            precio_float = float(pre["update_price"])
            if precio_float <= 0:
                return {"success": False,
                        "error": {
                            "status_code": "400",
                            "message": "USD price data not found",
                            "details": f"No data available for date {fecha_obj} from source {source}"
                        }}

            if convert == "bs":
                resultado = precio_float * value
                return {"bs_amount": round(resultado, 2), "usd": value, "date": pre["update_date"], "source": pre["source"]}
            elif convert == "usd":
                resultado = value / precio_float
                return {"usd_amount": round(resultado, 2), "bs" : value, "date": pre["update_date"], "source": pre["source"]}
            else:
                return {
                    "success": False,
                    "error": {
                        "status_code": "400",
                        "message": "Invalid Parameter",
                        "details": "Invalid Parameter 'convert' Use 'bs' or 'usd'"
                    }
                }
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": {
                    "status_code": "400",
                    "message": "Conversion Error",
                    "details": f"Conversion Error: {str(e)}"
                }
            }

    nom_cache = "pre_usd"
    cached_data = memory_cache.get(nom_cache)
    if cached_data:
        return json.loads(cached_data)

    precio = await asyncio.to_thread(leer_usd, conexion, source, None)

    if precio:
        memory_cache.setex(name=nom_cache, time=43200, value=json.dumps(precio))

    if not precio:
        return {"success": False,
                "error": {
                    "status_code": "404",
                    "message": "USD price data not found",
                    "details": f"No data available for date {fecha_obj} from source {source}"
                }}

    return precio

@appi.get("/api/v1/eur")
async def eur(date : str | None = None, convert : str | None = None, value: float | None = None,
              conexion: mariadb.Connection = Depends(get_db_connection)):

    fecha_obj = None
    if date:
        formatos = ["%Y-%m-%d", "%d-%m-%Y"]
        fecha_obj = None
        for fmt in formatos:
            try:
                fecha_obj = datetime.strptime(date, fmt).date()
                break
            except ValueError:
                continue
        if not fecha_obj:
            return {"success": False,
                    "error": {
                        "status_code": "400",
                        "message": "Date format invalide",
                        "details": "Use one of the formats: yyyy-mm-dd (2025-08-07) or dd-mm-yyyy (07-08-2025) do not use {fecha}"
                    }}

    if fecha_obj:
        data_from_db = await asyncio.to_thread(buscar_fecha, conexion, str(fecha_obj), "eur")

        if convert and value is not None:
            if not data_from_db or "update_price" not in data_from_db:
                return {"success": False,
                        "error": {
                            "status_code": "404",
                            "message": "EUR price data not found",
                            "details": f"No data available for date {fecha_obj}"
                        }}

            try:
                precio_con = float(data_from_db["update_price"])
                if precio_con <= 0:
                    return {"success": False,
                            "error": {
                                "status_code": "400",
                                "message": "EUR price data not found",
                                "details": f"No data available for date {fecha_obj}"
                            }}

                if convert == "bs":
                    resultado = precio_con * value
                    return {"bs_amount": round(resultado, 2), "eur": value, "date": data_from_db["fecha"], "eur_price": data_from_db["update_price"]}
                elif convert == "eur":
                    resultado = value / precio_con
                    return {"eur_amount": round(resultado, 2), "bs" : value, "date": data_from_db["fecha"], "eur_price": data_from_db["update_price"]}
                else:
                    return {
                        "success": False,
                        "error": {
                            "status_code": "400",
                            "message": "Invalid Parameter",
                            "details": "Invalid Parameter 'convert' Use 'bs' or 'eur'"
                        }
                    }
            except (ValueError, TypeError) as e:
                return {
                    "success": False,
                    "error": {
                        "status_code": "400",
                        "message": "Conversion Error",
                        "details": f"Conversion Error: {str(e)}"
                    }
                }

        return data_from_db

    pre = await asyncio.to_thread(leer_eur, conexion, "eur")

    if convert and value is not None:
        if not pre or "update_price" not in pre:
            return {"success": False,
                    "error": {
                        "status_code": "404",
                        "message": "EUR price data not found",
                        "details": f"No data available for date {fecha_obj}"
                    }}

        try:
            precio_float = float(pre["update_price"])
            if precio_float <= 0:
                return {"success": False,
                        "error": {
                            "status_code": "400",
                            "message": "EUR price data not found",
                            "details": f"No data available for date {fecha_obj}"
                        }}

            if convert == "bs":
                resultado = precio_float * value
                return {"bs_amount": resultado, "eur": value}
            elif convert == "eur":
                resultado = value / precio_float
                return {"eur_amount": resultado, "bs" : value}
            else:
                return {
                    "success": False,
                    "error": {
                        "status_code": "400",
                        "message": "Invalid Parameter",
                        "details": "Invalid Parameter 'convert' Use 'bs' or 'eur'"
                    }
                }
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": {
                    "status_code": "400",
                    "message": "Conversion Error",
                    "details": f"Conversion Error: {str(e)}"
                }
            }

    nom_cache = "pre_eur"
    cached_data = memory_cache.get(nom_cache)
    if cached_data:
        return json.loads(cached_data)

    precio = await asyncio.to_thread(leer_eur, conexion, "eur")

    if precio:
        memory_cache.setex(name=nom_cache, time=43200, value=json.dumps(precio))

    if not precio:
        return {"success": False,
                "error": {
                    "status_code": "404",
                    "message": "EUR price data not found",
                    "details": f"No data available for date {fecha_obj}"
                }}

    return {"eur": precio}

@appi.get("/api/v1/p2p")
async def p2p(fecha: str | None = None,
              convertir : str | None = None, valor: float | None = None,
              conexion: mariadb.Connection = Depends(get_db_connection)):

    fecha_obj = None
    if fecha:
        formatos = ["%Y-%m-%d", "%d-%m-%Y"]
        fecha_obj = None
        for fmt in formatos:
            try:
                fecha_obj = datetime.strptime(fecha, fmt).date()
                break
            except ValueError:
                continue
        if not fecha_obj:
            return {
                "success": False,
                "error": {
                    "status_code": "400",
                    "message": "Date format invalide",
                    "details": f"Use one of the formats: yyyy-mm-dd (2025-08-07) or dd-mm-yyyy (07-08-2025) do not use {fecha}"
                }
            }

    if fecha_obj:
        data_from_db = await asyncio.to_thread(buscar_fecha, conexion, str(fecha_obj), "e_m")

        if convertir and valor is not None:
            if not data_from_db or "update_price" not in data_from_db:
                return {"success": False,
                        "error": {
                            "status_code": "404",
                            "message": "EUR price data not found",
                            "details": f"No data available for date {fecha_obj}"
                        }}

            try:
                precio_con = float(data_from_db["update_price"])
                if precio_con <= 0:
                    return {"success": False,
                            "error": {
                                "status_code": "400",
                                "message": "EUR price data not found",
                                "details": f"No data available for date {fecha_obj}"
                            }}

                if convertir == "bs":
                    resultado = precio_con * valor
                    return {"bs_amount": round(resultado, 2), "usd": valor, "date": data_from_db["fecha"], "p2p_price": data_from_db["update_price"]}
                elif convertir == "usd":
                    resultado = valor / precio_con
                    return {"usd_amount": round(resultado, 2), "bs" : valor, "date": data_from_db["fecha"], "p2p_price": data_from_db["update_price"]}
                else:
                    return {
                        "success": False,
                        "error": {
                            "status_code": "400",
                            "message": "Invalid Parameter",
                            "details": "Invalid Parameter 'convert' Use 'bs' or 'usd'"
                        }
                    }
            except (ValueError, TypeError) as e:
                return {
                    "success": False,
                    "error": {
                        "status_code": "400",
                        "message": "Conversion Error",
                        "details": f"Conversion Error: {str(e)}"
                    }
                }

        return data_from_db

    pre = await asyncio.to_thread(leer_usd, conexion, "e_m", str(fecha_obj) if fecha_obj else None)

    if convertir and valor is not None:
        if not pre or "update_price" not in pre:
            return {"success": False,
                    "error": {
                        "status_code": "404",
                        "message": "EUR price data not found",
                        "details": f"No data available for date {fecha_obj}"
                    }}

        try:
            precio_float = float(pre["update_price"])
            if precio_float <= 0:
                return {"success": False,
                        "error": {
                            "status_code": "400",
                            "message": "EUR price data not found",
                            "details": f"No data available for date {fecha_obj}"
                        }}

            if convertir == "bs":
                resultado = precio_float * valor
                return {"bs_amount": round(resultado, 2), "usd": valor}
            elif convertir == "usd":
                resultado = valor / precio_float
                return {"usd_amount": round(resultado, 2), "bs" : valor}
            else:
                return {
                    "success": False,
                    "error": {
                        "status_code": "400",
                        "message": "Invalid Parameter",
                        "details": "Invalid Parameter 'convert' Use 'bs' or 'usd'"
                    }
                }
        except (ValueError, TypeError) as e:
            return {
                "success": False,
                "error": {
                    "status_code": "400",
                    "message": "Conversion Error",
                    "details": f"Conversion Error: {str(e)}"
                }
            }

    nom_cache = "pre_p2p"
    cached_data = memory_cache.get(nom_cache)
    if cached_data:
        return json.loads(cached_data)

    precio = await asyncio.to_thread(leer_usd, conexion, "e_m", None)

    if precio:
        memory_cache.setex(name=nom_cache, time=43200, value=json.dumps(precio))

    if not precio:
        return {"success": False,
                "error": {
                    "status_code": "404",
                    "message": "EUR price data not found",
                    "details": f"No data available for date {fecha_obj}"
                }}

    return {"p2p": precio}

@appi.get("/api/v1/tasa_inf")
async def tasa_inf(fecha: str | None = None, banco: str | None = None,
                  conexion: mariadb.Connection = Depends(get_db_connection)):

    fecha_obj = None
    if fecha:
        formatos = ["%Y-%m-%d", "%d-%m-%Y"]
        fecha_obj = None
        for fmt in formatos:
            try:
                fecha_obj = datetime.strptime(fecha, fmt).date()
                break
            except ValueError:
                continue
        if not fecha_obj:
            return {
                "success": False,
                "error": {
                    "status_code": "400",
                    "message": "Date format invalide",
                    "details": "Use one of the formats: yyyy-mm-dd (2025-08-07) or dd-mm-yyyy (07-08-2025) do not use {fecha}"
                }
            }

    if banco:
        banco = banco.upper()

        pre_banco = await asyncio.to_thread(ver_tasa, conexion, fecha_obj, banco)
        if pre_banco:
            return pre_banco
        else:
            return {"success": False,
                    "error": {
                        "status_code": "404",
                        "message": "Data not found",
                        "details": f"No data available for {banco} bank"
                    }}

    elif fecha_obj:
        if banco:
            banco = banco.upper()
        else:
            banco = None
        pre_fecha = await asyncio.to_thread(ver_tasa, conexion, fecha_obj, banco)
        if pre_fecha:
            return pre_fecha
        else:
            return {"success": False,
                    "error": {
                        "status_code": "404",
                        "message": "Data not found",
                        "details": f"No data available for date {fecha_obj}"
                    }}

    nom_cache = "tasa_inf"
    cached_data = memory_cache.get(nom_cache)
    if cached_data:
        return json.loads(cached_data)

    precios = await asyncio.to_thread(ver_tasa, conexion, fecha_obj, banco)

    if precios:
        memory_cache.setex(name=nom_cache, time=43200, value=json.dumps(precios))

    if not precios:
        return {"success": False,
                "error": {
                    "status_code": "404",
                    "message": "Data not found",
                    "details": f"No data available for date {fecha_obj}"
                }}

    return precios

if __name__ == "__main__":
    uvicorn.run(
        "fastappi:appi",
        port=int(os.getenv('API_PORT', 8000)),
        reload=os.getenv('DEBUG', 'False').lower() == 'true',
        workers=1
    )
