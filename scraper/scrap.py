import requests
from bs4 import BeautifulSoup
from datetime import datetime
from playwright.sync_api import sync_playwright, Playwright
from playwright.async_api import async_playwright
import time
import random
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import sys
import bd
import logging
import os
import argparse
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(module)s - %(levelname)s - %(message)s',
                    filename='scraper.log',
                    filemode='a',  
                    datefmt="%d-%m-%y %H:%M:%S",
                    force=True)

def verificar_proxies_scheduler():

    try:
        if not verificar_proxies_disponibles():
            logging.critical("CRÍTICO: Verificación de proxies falló - sistema en riesgo")
            return {"estado": "crítico", "proxies_disponibles": 0}
        else:
            logging.info("Verificación de proxies exitosa")
            return {"estado": "ok", "proxies_disponibles": "todos"}
    except Exception as e:
        logging.error(f"Error en verificación de proxies: {e}")
        return {"estado": "error", "error": str(e)}

def formatear(precio):
    precio = precio.replace(",", ".")
    precio = float(precio)
    return round(precio, 2)

def dar_proxy():   
    proxy_username = os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('PROXY_PASSWORD')
    proxy_servers = os.getenv('PROXY_SERVERS', '').split(',') if os.getenv('PROXY_SERVERS') else []
    
    if not proxy_username or not proxy_password or not proxy_servers:
        logging.error("Proxy credentials or servers not found in environment variables")
        return None
    
    proxies = []
    for server in proxy_servers:
        if server.strip():
            proxies.append(f"http://{proxy_username}:{proxy_password}@{server.strip()}/")
    
    if not proxies:
        logging.error("No valid proxy servers configured")
        return None
    
    opcion = random.choice(proxies)
    return opcion

def verificar_proxies_disponibles():
    proxy_username = os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('PROXY_PASSWORD')
    proxy_servers = os.getenv('PROXY_SERVERS', '').split(',') if os.getenv('PROXY_SERVERS') else []
    
    if not proxy_username or not proxy_password or not proxy_servers:
        logging.error("Proxy credentials or servers not found in environment variables")
        return False
    
    proxies = []
    for server in proxy_servers:
        if server.strip():
            proxies.append(f"http://{proxy_username}:{proxy_password}@{server.strip()}/")
    
    if not proxies:
        logging.error("No valid proxy servers configured")
        return False
    
    proxies_funcionando = 0
    
    for proxy in proxies:
        try:
            response = requests.get("http://httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=10)
            if response.status_code == 200:
                proxies_funcionando += 1
                logging.info(f"Proxy funcionando: {proxy}")
            else:
                logging.warning(f"Proxy con problemas: {proxy} - Status: {response.status_code}")
        except Exception as e:
            logging.error(f"Proxy fallido: {proxy} - Error: {str(e)}")
    
    if proxies_funcionando == 0:
        logging.critical("CRÍTICO: Ningún proxy disponible - el sistema no puede funcionar")
        return False
    elif proxies_funcionando < len(proxies) / 2:
        logging.warning(f"Solo {proxies_funcionando}/{len(proxies)} proxies funcionando")
    
    return True

def dar_proxy_play():
    proxy_username = os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('PROXY_PASSWORD')
    proxy_servers = os.getenv('PROXY_SERVERS', '').split(',') if os.getenv('PROXY_SERVERS') else []
    
    if not proxy_username or not proxy_password or not proxy_servers:
        logging.error("Proxy credentials or servers not found in environment variables")
        return None
    
    proxies = []
    for server in proxy_servers:
        if server.strip():
            proxies.append({
                "username": proxy_username,
                "password": proxy_password,
                "server": server.strip()
            })
    
    if not proxies:
        logging.error("No valid proxy servers configured")
        return None
    
    proxy = random.choice(proxies)
    logging.info(f"Proxy seleccionado para Playwright: {proxy['server']}")
    return proxy

paginas = {
    "primera": os.getenv('SCRAPING_URL_PRIMERA', 'https://www.bcv.org.ve/'),
    "segunda": os.getenv('SCRAPING_URL_SEGUNDA', 'https://www.italcambio.com/servicios.php'),
    "tercera": os.getenv('SCRAPING_URL_TERCERA', 'https://criptodolar.net/'),
    "Sexta": os.getenv('SCRAPING_URL_SEXTA', 'https://www.bcv.org.ve/tasas-informativas-sistema-bancario'),
    "septima": os.getenv('SCRAPING_URL_SEPTIMA', 'https://exchangemonitor.net/dolar-venezuela'),
}

async def play_primera():
    tiempo_inicio = time.time()

    pro = await asyncio.to_thread(dar_proxy)
    logging.info(f"Iniciando función play_primera desde: {ver_ip(pro)}")

    try:
        respuesta = requests.get(url=paginas["primera"], verify=False, proxies={
            "http" : pro,
            "https" : pro
        })

        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.content, "html.parser")

            elementos_nombre = soup.find_all("div", class_="col-sm-6 col-xs-6")
            elementos_valor = soup.find_all("div", class_="col-sm-6 col-xs-6 centrado")

            nombres = []
            for i in elementos_nombre:

                nom_span = i.find("span")
                if nom_span: 
                    nombres.append(nom_span.get_text(strip=True))

            valores = []
            for i in elementos_valor:
                val_strong = i.find("strong")
                if val_strong: 
                    valores.append(val_strong.get_text(strip=True))

            datos = []
            fecha = datetime.today()
            fecha = str(fecha)[:-7]

            fecha_dia = fecha[:-8]
            hora = fecha[10:]

            usd = ["bcv", "criptodolar", "italcambio"]
            clave_valor = {
                "EUR": "Euro", "CNY" : "Yuan chino", "TRY" : "Lira turca", "RUB": "Rublo ruso", "USD": "Dolar estadounidense"
            }

            for n, val in zip(nombres, valores):

                if n == "USD":
                    par = {n: {"valor": val, "fecha": fecha_dia.strip(), "hora" : hora.strip(), "fuente" : usd, "nombre" : clave_valor[n]}}
                    datos.append(par)
                else:
                    par = {n: {"valor": val, "fecha": fecha_dia.strip(), "hora" : hora.strip(), "fuente" : "bcv", "nombre" : clave_valor[n]}} 
                    datos.append(par)

            tiempo_fin = time.time()
            tiempo_total = tiempo_fin - tiempo_inicio

            logging.info(f"⏱️ Tiempo de ejecución de play_primera: {tiempo_total:.2f} segundos desde {pro}")
            return datos

        else:
            tiempo_fin = time.time()
            tiempo_total = tiempo_fin - tiempo_inicio
            
            logging.error(f"Error en play_primera: Respuesta no exitosa con código {respuesta.status_code} desde {pro}")
            return {"error": respuesta.status_code}

    except Exception as e:
        tiempo_fin = time.time()
        tiempo_total = tiempo_fin - tiempo_inicio
        
        logging.error(f"Error en play_primera después de {tiempo_total:.2f} segundos: {e}")
        return {"error": str(e)}

def primera_p():
    tiempo_inicio = time.time()
    from bd import precio_usd

    pro = dar_proxy()

    try:
        respuesta = requests.get(url=paginas["primera"], verify=False, proxies={
            "http" : pro,
            "https" : pro
        })

        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.content, "html.parser")

            elementos_nombre = soup.find_all("div", class_="col-sm-6 col-xs-6")
            elementos_valor = soup.find_all("div", class_="col-sm-6 col-xs-6 centrado")

            nombres = []
            for i in elementos_nombre:

                nom_span = i.find("span")
                if nom_span: 
                    nombres.append(nom_span.get_text(strip=True))

            valores = []
            for i in elementos_valor:
                val_strong = i.find("strong")
                if val_strong: 
                    valores.append(val_strong.get_text(strip=True))

            datos = []
            fecha = datetime.today()
            fecha = str(fecha)[:-7]

            fecha_dia = fecha[:-8]
            hora = fecha[10:]

            clave_valor = {
                "EUR": "Euro", "CNY" : "Yuan chino", "TRY" : "Lira turca", "RUB": "Rublo ruso", "USD": "Dolar estadounidense"
            }
            usd = ["bcv", "criptodolar", "italcambio"]
            for n, val in zip(nombres, valores):

                if n == "USD":
                    par = {n: {"valor": val, "fecha": fecha_dia.strip(), "hora" : hora.strip(), "fuente" : usd, "clave" : clave_valor[n]}}
                    datos.append(par)
                else:
                    par = {n: {"valor": val, "fecha": fecha_dia.strip(), "hora" : hora.strip(), "fuente" : "bcv", "clave" : clave_valor[n]}} 
                    datos.append(par)

            valor_usd = datos[-1]["USD"]["valor"]
            valor_eur = datos[0]["EUR"]["valor"]
            valor_cny = datos[1]["CNY"]["valor"]
            valor_try = datos[2]["TRY"]["valor"]
            valor_rub = datos[3]["RUB"]["valor"]
            
            precio_usd(fuente=1, moneda=1, valor=formatear(valor_usd), fecha=fecha.strip(), hora=hora.strip())
            precio_usd(fuente=1, moneda=2, valor=formatear(valor_eur), fecha=fecha.strip(), hora=hora.strip())
            precio_usd(fuente=1, moneda=3, valor=formatear(valor_try), fecha=fecha.strip(), hora=hora.strip())
            precio_usd(fuente=1, moneda=4, valor=formatear(valor_rub), fecha=fecha.strip(), hora=hora.strip())
            precio_usd(fuente=1, moneda=5, valor=formatear(valor_cny), fecha=fecha.strip(), hora=hora.strip())

            tiempo_fin = time.time()
            tiempo_total = tiempo_fin - tiempo_inicio

            logging.info(f"⏱️ Tiempo de ejecución de primera_p: {tiempo_total:.2f} segundos desde {pro}")

            return datos

        else:
            logging.error(f"Error en primera_p: Respuesta no exitosa con código {respuesta.status_code} desde {pro}")
            return {"error" : respuesta.status_code}
    except Exception as e:
        logging.error(f"    Error en primera_p: {e}")
        return {"error" : e}

def segunda_p():
    tiempo_inicio = time.time()
    from bd import precio_usd
    
    max_intentos = 3
    for intento in range(max_intentos):
        with sync_playwright() as p:
            pro = dar_proxy_play()
            logging.info(f"Iniciando segunda_p (intento {intento + 1}/{max_intentos}) desde: {pro}")

            try:
                browser = p.firefox.launch(headless=True, slow_mo=10, proxy={
                    "server": f"http://{pro['server']}",
                    "username": pro["username"],
                    "password": pro["password"]
                })
                context = browser.new_context(ignore_https_errors=True)

                page = context.new_page()
                page.goto("https://criptodolar.net/", timeout=30000) 
                logging.debug(f"Título de la página: {page.title()}")

                page.wait_for_load_state("domcontentloaded", timeout=20000)

                soup = BeautifulSoup(page.content(), "html.parser")

                elemento = soup.find_all("td", class_="align-middle font-weight-bold")

                valor = str(elemento)
                resultado = []

                for i in valor:
                    try:
                        entero = int(i)
                        if entero:
                            entero = str(entero)
                            resultado.append(entero)
                    except:
                        pass
                    if i == ",":
                        resultado.append(i)

                resultado_final = "".join(resultado)
                resultado_final = resultado_final.replace(",", ".")

                resultado_final = float(resultado_final)

                fecha = datetime.today()
                fecha = str(fecha)

                fecha = fecha[:-7]
                hora = fecha[10:]

                logging.info(f"Datos extraídos segunda_p: valor={resultado_final}, fecha={fecha}, hora={hora}") 

                browser.close()

                precio_usd(fuente=2, moneda=1, valor=resultado_final, fecha=fecha.strip(), hora=hora.strip())

                tiempo_fin = time.time()
                tiempo_total = tiempo_fin - tiempo_inicio

                logging.info(f"Tiempo de ejecución de segunda_p: {tiempo_total:.2f} segundos desde {pro}")
                return {"success": True, "valor": resultado_final}

            except Exception as e:
                browser.close() if 'browser' in locals() else None
                tiempo_fin = time.time()
                tiempo_total = tiempo_fin - tiempo_inicio
                
                if intento < max_intentos - 1:
                    logging.warning(f"⚠️ Error en segunda_p (intento {intento + 1}): {e} - Reintentando...")
                    time.sleep(2)  # Pausa antes del siguiente intento
                else:
                    logging.error(f"Error final en segunda_p después de {max_intentos} intentos: {e}")
                    return {"error": str(e)}

def tercera_p():
    tiempo_inicio = time.time()
    from bd import precio_usd

    max_intentos = 3
    for intento in range(max_intentos):
        with sync_playwright() as p:
            pro = dar_proxy_play()
            logging.info(f"Iniciando tercera_p (intento {intento + 1}/{max_intentos}) desde: {pro}")

            try:
                browser = p.firefox.launch(headless=True, slow_mo=10, proxy={
                    "server": f"http://{pro['server']}",
                    "username": pro["username"],
                    "password": pro["password"]
                })

                contexto = browser.new_context(ignore_https_errors=True)

                pagina = contexto.new_page()
                pagina.goto("https://www.italcambio.com/servicios.php", timeout=30000)
                logging.debug(f"Título de la página: {pagina.title()}")

                pagina.wait_for_load_state("domcontentloaded", timeout=20000)
                
                # Manejo mejorado del botón close
                try:
                    boton = pagina.locator(".close")
                    if boton.count() > 0:
                        boton.click()
                        time.sleep(2)
                except:
                    logging.debug("No se encontró botón close o falló el click")

                soup = BeautifulSoup(pagina.content(), "html.parser")

                elemento = soup.find_all("p", class_="small")
                precios = []
                indice = 0

                for i in elemento:
                    while indice < 2:
                        texto = elemento[indice].get_text(strip=True)
                        
                        numeros = []
                        punto_encontrado = False
                        
                        for caracter in texto:
                            if caracter.isdigit():
                                numeros.append(caracter)
                            elif caracter == '.' and not punto_encontrado:
                                numeros.append(caracter)
                                punto_encontrado = True
                            elif caracter == ',' and not punto_encontrado:
                                numeros.append('.')
                                punto_encontrado = True
                        
                        if numeros:
                            numero_str = ''.join(numeros)
                            try:
                                numero_float = float(numero_str)
                                numero_formateado = round(numero_float, 2)
                                precios.append(numero_formateado)
                                logging.debug(f"Precio extraído: {numero_formateado}")
                            except ValueError:
                                logging.warning(f"No se pudo convertir '{numero_str}' a número")
                                precios.append(0.0)
                        else:
                            precios.append(0.0)
                        
                        indice = indice + 1

                fecha_actual = datetime.today()
                fecha = fecha_actual.strftime("%Y-%m-%d")
                hora = fecha_actual.strftime("%H:%M:%S")

                if len(precios) >= 2:
                    p_compra = precios[1]
                else:
                    p_compra = 0.0

                precio_usd(fuente=3, moneda=1, valor=p_compra, fecha=str(fecha), hora=str(hora))

                tiempo_fin = time.time()
                tiempo_total = tiempo_fin - tiempo_inicio

                logging.info(f"Tiempo de ejecución de tercera_p: {tiempo_total:.2f} segundos desde {pro}")
                browser.close()
                return {"success": True, "valor": p_compra}

            except Exception as e:
                browser.close() if 'browser' in locals() else None
                tiempo_fin = time.time()
                tiempo_total = tiempo_fin - tiempo_inicio
                
                if intento < max_intentos - 1:
                    logging.warning(f"⚠️ Error en tercera_p (intento {intento + 1}): {e} - Reintentando...")
                    time.sleep(2)  
                else:
                    logging.error(f"Error final en tercera_p después de {max_intentos} intentos: {e}")
                    return {"error": str(e)}
        
def precios_ban():
    from bd import bancos
    pro = dar_proxy()

    try:
        respuesta = requests.get(url="https://www.bcv.org.ve/tasas-informativas-sistema-bancario", verify=False, proxies={
            "http" : pro,
            "https" : pro
        })

        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.content, "html.parser")

            col1 = soup.find_all("td", class_="views-field views-field-field-fecha-del-indicador")
            col2 = soup.find_all("td", class_="views-field views-field-views-conditional")
            col3 = soup.find_all("td", class_="views-field views-field-field-tasa-compra")
            col4 = soup.find_all("td", class_="views-field views-field-field-tasa-venta")

            filas = []
            c2_vistos = set()  

            for c1, c2, c3, c4 in zip(col1, col2, col3, col4):
                c1_text = c1.get_text(strip=True)
                c2_text = c2.get_text(strip=True)
                c3_text = c3.get_text(strip=True)
                c4_text = c4.get_text(strip=True)   

                fecha = datetime.strptime(c1_text, "%d-%m-%Y").date()
                fecha1 = fecha.strftime("%Y-%m-%d")
                if c2_text not in c2_vistos:
                    fila = [fecha1, c2_text, c3_text, c4_text]
                    filas.append(fila)
                    c2_vistos.add(c2_text)

            print("Filas únicas por c2_text:", len(filas))

        bancos(datos=reversed(filas), valores=c2_vistos)

    except Exception as e:
        logging.error(f"Error al obtener precios del BCV: {e}")
        return {"error": str(e)}
        
def ver_ip(pro):
    #pro = dar_proxy()
    ip = requests.get(url="https://httpbin.org/ip", proxies={
        "http" : pro,
        "https" : pro
    })

    if ip.status_code == 200:
        return ip.json()
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scraper de tasas de cambio')
    parser.add_argument('--scheduler', '-s', action='store_true', 
                       help='Ejecutar con background schedulers')
    args = parser.parse_args()
    
    if args.scheduler:
        logging.info("Iniciando modo scheduler - ejecución automática programada")
        
        aps_primera = BackgroundScheduler(
            job_defaults={
                'max_instances': 1,          
                'coalesce': True,             
                'misfire_grace_time': 30     
            },
            timezone='America/Caracas'
        )
        aps_primera.add_job(primera_p, "interval", seconds=40)  
        aps_primera.start()

        aps_segunda = BackgroundScheduler(
            job_defaults={
                'max_instances': 1,          
                'coalesce': True,             
                'misfire_grace_time': 30     
            },
            timezone='America/Caracas'
        )
        aps_segunda.add_job(segunda_p, "interval", seconds=50) 
        aps_segunda.start()

        aps_tercera = BackgroundScheduler(
            job_defaults={
                'max_instances': 1,          
                'coalesce': True,             
                'misfire_grace_time': 30     
            },
            timezone='America/Caracas'
        )
        aps_tercera.add_job(tercera_p, "interval", seconds=60) 
        aps_tercera.start()

        aps_bancos = BackgroundScheduler(
            job_defaults={
                'max_instances': 1,          
                'coalesce': True,             
                'misfire_grace_time': 60     
            },
            timezone='America/Caracas'
        )
        aps_bancos.add_job(precios_ban, "interval", seconds=600)  
        #aps_bancos.start()

        aps_p2p = BackgroundScheduler(
            job_defaults={
                'max_instances': 1,          
                'coalesce': True,             
                'misfire_grace_time': 30     
            },
            timezone='America/Caracas'
        )
        aps_p2p.add_job(precios_p2p, "interval", seconds=120)  
        aps_p2p.start()

        aps_monitoreo = BackgroundScheduler(
            job_defaults={
                'max_instances': 1,          
                'coalesce': True,             
                'misfire_grace_time': 30     
            },
            timezone='America/Caracas'
        )
        aps_monitoreo.add_job(verificar_proxies_scheduler, "interval", seconds=300)  
        #aps_monitoreo.start()

        try:
            logging.info("Schedulers iniciados - ejecutando en bucle infinito")
            logging.info("Funciones programadas:")
            logging.info("- primera_p (BCV): cada 5 minutos")
            logging.info("- segunda_p (CriptoDolar): cada 3 minutos")
            logging.info("- tercera_p (ItalCambio): cada 4 minutos")
            logging.info("- precios_ban (Tasas bancarias): cada 10 minutos")
            logging.info("- precios_p2p (Binance P2P): cada 2 minutos")
            logging.info("- verificar_proxies: cada 5 minutos")
            
            while True:
                time.sleep(2)
        except KeyboardInterrupt:
            logging.info("Deteniendo schedulers...")
            aps_primera.shutdown()
            aps_segunda.shutdown()
            aps_tercera.shutdown()
            aps_bancos.shutdown()
            aps_p2p.shutdown()
            aps_monitoreo.shutdown()
            logging.info("Schedulers finalizados")
            sys.exit(0)
    else:
        logging.info("Ejecutando funciones directamente - modo manual")
        
        try:
            precios_ban()
            time.sleep(2)
            segunda_p()
            time.sleep(2)
            tercera_p()
            time.sleep(2)
            primera_p()
            time.sleep(2)
            precios_p2p()
            
            logging.info("Todas las funciones ejecutadas exitosamente")
            
        except Exception as e:
            logging.error(f"Error durante la ejecución: {str(e)}")
            sys.exit(1)

