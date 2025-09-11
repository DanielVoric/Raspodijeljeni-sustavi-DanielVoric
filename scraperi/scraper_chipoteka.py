from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .celery_app import app 
app_scraper_chipoteka = FastAPI()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def scrape_page(page_number: int) -> List[Dict[str, Optional[str]]]:
    url = (
        "https://www.chipoteka.hr/proizvodi-na-akciji?price%5Bmin%5D=1&price%5Bmax%5D=6723"
        f"&ajax_digitalElephantFilter=1&page={page_number}"
    )
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return []

    soup = BeautifulSoup(resp.content, "html.parser")

    products: List[Dict[str, Optional[str]]] = []
    cards = soup.select("div.product-card-wrapper div.card.product-card")
    if not cards:
        return products

    for card in cards:
        body = card.select_one('div.card-body')
        if not body:
            continue
        title_el = body.select_one('h2.product-title')
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        old_el = body.select_one('div.product-price del')
        price_old = old_el.get_text(strip=True) if old_el else None

        price_wrap = body.select_one('div.product-price--web')
        price_new = None
        if price_wrap:
            spans = price_wrap.select('span')
            if len(spans) >= 2:
                price_new = spans[1].get_text(strip=True)

        products.append({
            "name": title,
            "price_new": price_new,
            "price_old": price_old,
            "source": "chipoteka",
        })

    return products

def detect_last_page(max_probe: int = 200) -> int:
    page = 1
    while page <= max_probe:
        items = scrape_page(page)
        if not items:
            return page - 1
        page += 1
    return max_probe

@app.task(name='scraperi.scraper_chipoteka.scrape_chipoteka_chunk')
def scrape_chipoteka_chunk(start_page: int, end_page: int):
    if end_page < start_page:
        return []
    if end_page - start_page > 4:
        end_page = start_page + 4
    collected: List[Dict[str, Optional[str]]] = []
    for p in range(start_page, end_page + 1):
        part = scrape_page(p)
        if not part:
            break
        collected.extend(part)
    return collected

@app_scraper_chipoteka.get("/")
async def scrape_all_pages():
    last = detect_last_page()
    if last == 0:
        return {"data": [], "title": "Chipoteka", "count": 0}
    products: List[Dict[str, Optional[str]]] = []
    for p in range(1, last + 1):
        items = scrape_page(p)
        if not items:
            break
        products.extend(items)
    return {"data": products, "title": "Chipoteka", "count": len(products)}

#uvicorn scraper_chipoteka:app --reload --port 8003

