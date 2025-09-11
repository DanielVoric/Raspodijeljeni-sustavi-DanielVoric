from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .celery_app import app

app_scraper_links = FastAPI()


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def scrape_page(page_number: int) -> List[Dict[str, Optional[str]]]:
    url = f"https://www.links.hr/hr/links-akcija?pagenumber={page_number}&orderby=0&pagesize=48&viewmode=grid&price=29-3629"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return []

    soup = BeautifulSoup(resp.content, "html.parser")

    products: List[Dict[str, Optional[str]]] = []
    cards = soup.select("div.row.product-grid div.card.mobile-card")
    if not cards:
        return products

    for card in cards:
        title_el = card.select_one("h3.mt-2")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        new_el = card.select_one("div.product-price span.active")
        old_el = card.select_one("div.product-price span.inactive")
        price_new = new_el.get_text(strip=True) if new_el else None
        price_old = old_el.get_text(strip=True) if old_el else None

        products.append({
            "name": title,
            "price_new": price_new,
            "price_old": price_old,
            "source": "links",
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


@app.task(name='scraperi.scraper_links.scrape_links_chunk')
def scrape_links_chunk(start_page: int, end_page: int):
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


@app_scraper_links.get("/")
async def scrape_all_pages():
    last = detect_last_page()
    if last == 0:
        return {"data": [], "title": "Links", "count": 0}
    full: List[Dict[str, Optional[str]]] = []
    for p in range(1, last + 1):
        items = scrape_page(p)
        if not items:
            break
        full.extend(items)
    return {"data": full, "title": "Links", "count": len(full)}

#uvicorn scraper_svijetmedija:app --reload --port 8002