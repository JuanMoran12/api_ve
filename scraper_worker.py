import json
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from upstash_redis import Redis
from scraper.scrap import primera_p, segunda_p, precios_ban

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(module)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
CACHE_TTL = 43200  # 12 hours


def get_redis():
    if not REDIS_URL or not REDIS_TOKEN:
        logger.error("Upstash Redis credentials not configured")
        return None
    return Redis(url=REDIS_URL, token=REDIS_TOKEN)


def scrape_and_cache(key, primary_func, fallback_func):
    redis = get_redis()
    if not redis:
        logger.error(f"Cannot scrape {key}: Redis unavailable")
        return False

    # Try primary
    data = primary_func()
    if not data or "error" in data:
        logger.warning(f"Primary failed for {key}, trying fallback")
        data = fallback_func()

    if not data or "error" in data:
        logger.error(f"Both sources failed for {key}")
        return False

    redis.setex(name=key, seconds=CACHE_TTL, value=json.dumps(data))
    logger.info(f"Scraped and cached {key} (TTL: {CACHE_TTL}s)")
    return True


def main():
    logger.info(f"=== Scraper worker started at {datetime.utcnow().isoformat()} ===")

    results = {}

    # monedas_data: USD/EUR rates
    ok = scrape_and_cache("monedas_data", primera_p, segunda_p)
    results["monedas_data"] = "OK" if ok else "FAILED"

    # tasa_inf: bank rates
    ok = scrape_and_cache("tasa_inf", precios_ban, precios_ban)
    results["tasa_inf"] = "OK" if ok else "FAILED"

    logger.info(f"=== Scraper worker results: {results} ===")
    return results


if __name__ == "__main__":
    main()
