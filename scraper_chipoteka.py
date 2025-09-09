from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

app = FastAPI()

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

    proizvodi: List[Dict[str, Optional[str]]] = []
    cards = soup.select("div.product-card-wrapper div.card.product-card")
    if not cards:
        return proizvodi

    for card in cards:
        body = card.select_one('div.card-body')
        if not body:
            continue
        naziv_el = body.select_one('h2.product-title')
        if not naziv_el:
            continue
        naziv = naziv_el.get_text(strip=True)

        stara_el = body.select_one('div.product-price del')
        stara_cijena = stara_el.get_text(strip=True) if stara_el else None

        nova_wrap = body.select_one('div.product-price--web')
        nova_cijena = None
        if nova_wrap:
            spans = nova_wrap.select('span')
            if len(spans) >= 2:
                nova_cijena = spans[1].get_text(strip=True)

        proizvodi.append({
            "naziv_ch": naziv,
            "nova_cijena_ch": nova_cijena,
            "stara_cijena_ch": stara_cijena
        })

    return proizvodi

@app.get("/")
async def scrape_all_pages():
    proizvodi: List[Dict[str, Optional[str]]] = []
    page = 1
    while True:
        items = scrape_page(page)
        if not items:
            break
        proizvodi.extend(items)
        page += 1
    return {"data": proizvodi, "title": "Chipoteka", "count": len(proizvodi)}

#uvicorn scraper_chipoteka:app --reload --port 8003

