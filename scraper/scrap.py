import requests
from bs4 import BeautifulSoup
from datetime import datetime
#from playwright.sync_api import sync_playwright
import random
import asyncio
import logging
import os
import re
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

def get_request(url, use_proxy=True, **kwargs):
    # Inyectar User-Agent aleatorio si no se especifica uno
    headers = kwargs.get('headers', {})
    if 'User-Agent' not in headers:
        headers['User-Agent'] = random.choice(USER_AGENTS)
    kwargs['headers'] = headers

    if use_proxy:
        proxy = dar_proxy()
        if proxy:
            try:
                return requests.get(url, proxies={"http": proxy, "https": proxy}, **kwargs)
            except Exception as e:
                logging.warning(f"Proxy falló, intentando conexión directa: {e}")
    return requests.get(url, **kwargs)

def dar_proxy():   
    proxy_username = os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('PROXY_PASSWORD')
    proxy_servers = os.getenv('PROXY_SERVERS', '').split(',') if os.getenv('PROXY_SERVERS') else []
    if not proxy_username or not proxy_password or not proxy_servers:
        return None
    proxies = [f"http://{proxy_username}:{proxy_password}@{s.strip()}/" for s in proxy_servers if s.strip()]
    return random.choice(proxies) if proxies else None

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
            valores = [v.get_text(strip=True) for v in soup.find_all("div", class_="col-sm-6 col-xs-6 centrado") if v.find("strong")]
            
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
    # Extraer valores para Dolar y Euro de criptodolar.net
    try:
        respuesta = get_request("https://criptodolar.net/", verify=False, timeout=15)
        if respuesta.status_code == 200:
            # Buscar Dolar y Euro (ajustando regex para mayor precisión)
            match_usd = re.search(r'USD.*?Bs\.\s*([\d,.]+)', respuesta.text)
            match_eur = re.search(r'EUR.*?Bs\.\s*([\d,.]+)', respuesta.text)
            
            res = {"fecha": datetime.today().strftime("%Y-%m-%d")}
            if match_usd:
                res["usd"] = float(match_usd.group(1).replace(",", "."))
            if match_eur:
                res["eur"] = float(match_eur.group(1).replace(",", "."))
            
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
    #print(primera_p())
    print(segunda_p())
    #print(precios_ban())
