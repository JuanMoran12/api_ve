import requests
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
from datetime import datetime
#from playwright.sync_api import sync_playwright
import random
import asyncio
import logging
import os
import re
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
#from camoufox.sync_api import Camoufox
#from .precios_2p import precios_p2p

load_dotenv()

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(module)s - %(levelname)s - %(message)s',
                    filename='scraper.log',
                    filemode='a',  
                    datefmt="%d-%m-%y %H:%M:%S",
                    force=True)

# Lista de User-Agents modernos para evitar bloqueos
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

def get_proxies_list():
    """Retorna la lista completa de proxies configurados en el .env"""
    proxy_username = os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('PROXY_PASSWORD')
    proxy_servers = os.getenv('PROXY_SERVERS', '').split(',') if os.getenv('PROXY_SERVERS') else []
    
    if not proxy_username or not proxy_password or not proxy_servers:
        return []
        
    return [f"http://{proxy_username}:{proxy_password}@{s.strip()}/" for s in proxy_servers if s.strip()]

def get_request(url, use_proxy=True, **kwargs):
    # Inyectar User-Agent aleatorio si no se especifica uno
    headers = kwargs.get('headers', {})
    if 'User-Agent' not in headers:
        headers['User-Agent'] = random.choice(USER_AGENTS)
    kwargs['headers'] = headers

    # Definir un timeout por defecto si no existe
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 15

    if use_proxy:
        proxies = get_proxies_list()
        if proxies:
            random.shuffle(proxies) # Rotación aleatoria
            for proxy_url in proxies:
                proxy_host = proxy_url.split('@')[-1] # Para loguear sin mostrar credenciales
                try:
                    logging.info(f"Intentando con proxy: {proxy_host}")
                    respuesta = requests.get(url, proxies={"http": proxy_url, "https": proxy_url}, **kwargs)
                    if respuesta.status_code == 200:
                        return respuesta
                    logging.warning(f"Proxy {proxy_host} devolvió status {respuesta.status_code}")
                except Exception as e:
                    logging.warning(f"Falla de conexión con proxy {proxy_host}: {e}")
            
            logging.warning("Todos los proxies fallaron. Intentando conexión directa...")
        else:
            logging.info("No hay proxies configurados. Usando conexión directa.")

    return requests.get(url, **kwargs)

paginas = {
    "primera": os.getenv('SCRAPING_URL_PRIMERA', 'https://www.bcv.org.ve/'),
    "tercera": os.getenv('SCRAPING_URL_TERCERA', 'https://criptodolar.net/'),
}

async def play_primera():
    try:
        respuesta = get_request(url=paginas["primera"], verify=False, timeout=15)
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.content, "html.parser")
            nombres = [n.get_text(strip=True) for n in soup.find_all("div", class_="col-sm-6 col-xs-6") if n.find("span")]
            valores = [v.get_text(strip=True) for v in soup.find_all("div", class_="col-sm-6 col-xs-6 centrado textp") if v.find("strong")]
            
            # Busqueda especifica
            usd_idx = nombres.index("USD") if "USD" in nombres else -1
            eur_idx = nombres.index("EUR") if "EUR" in nombres else -1
            
            valor_final_usd = float(valores[usd_idx].replace(",", ".")) if usd_idx != -1 else 0.0
            valor_final_eur = float(valores[eur_idx].replace(",", ".")) if eur_idx != -1 else 0.0

            fecha = datetime.today().strftime("%Y-%m-%d")
            hora = datetime.today().strftime("%H:%M:%S")
            return {
                "datos": [{n: {"valor": val, "fecha": fecha, "hora": hora}} for n, val in zip(nombres, valores)],
                "valor_final_usd": valor_final_usd,
                "valor_final_eur": valor_final_eur
            }
        return {"error": respuesta.status_code}
    except Exception as e:
        return {"error": str(e)}

def primera_p():
    return asyncio.run(play_primera())

def segunda_p():
    # Extraer valores para Dolar y Euro de criptodolar.net usando selectores
    try:
        respuesta = get_request("https://criptodolar.net/", verify=False, timeout=15)
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.content, "html.parser")
            
            # Buscar todas las tarjetas con la clase específica
            cards = soup.find_all("div", class_="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6")
            
            res = {"fecha": datetime.today().strftime("%Y-%m-%d")}
            
            for card in cards:
                card_text = card.get_text()
                # Buscar precio en formato "Bs. XXX,XX"
                match = re.search(r'Bs\.\s*([\d,.]+)', card_text)
                
                if match:
                    price = float(match.group(1).replace(",", "."))
                    
                    if "Dólar BCV" in card_text or "BCV (USD)" in card_text:
                        res["usd"] = price
                    elif "Euro BCV" in card_text or "BCV (EUR)" in card_text:
                        res["eur"] = price
            
            return res
        return {"error": "No se pudo extraer el valor de las divisas"}
    except Exception as e:
        return {"error": str(e)}
        
def precios_ban():
    try:
        respuesta = get_request(url="https://www.bcv.org.ve/tasas-informativas-sistema-bancario", verify=False, timeout=15)
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.content, "html.parser")
            col1 = soup.find_all("td", class_="views-field views-field-field-fecha-del-indicador")
            col2 = soup.find_all("td", class_="views-field views-field-views-conditional")
            col3 = soup.find_all("td", class_="views-field views-field-field-tasa-compra")
            col4 = soup.find_all("td", class_="views-field views-field-field-tasa-venta")
            filas = [[datetime.strptime(c1.get_text(strip=True), "%d-%m-%Y").strftime("%Y-%m-%d"), c2.get_text(strip=True), c3.get_text(strip=True), c4.get_text(strip=True)] for c1, c2, c3, c4 in zip(col1, col2, col3, col4)]
            return {"datos": filas}
        return {"error": "Respuesta no exitosa"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print(primera_p())
    #print(segunda_p())
    #print(precios_ban())
