from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

app = FastAPI()


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def scrape_page(page_number: int) -> List[Dict[str, Optional[str]]]:
    # Cijeli URL sastavljen ovdje (ne koristimo vise BASE/COMMON konstante)
    url = f"https://www.links.hr/hr/links-akcija?pagenumber={page_number}&orderby=0&pagesize=48&viewmode=grid&price=29-3629"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return []

    soup = BeautifulSoup(resp.content, "html.parser")

    proizvodi: List[Dict[str, Optional[str]]] = []
    cards = soup.select("div.row.product-grid div.card.mobile-card")
    if not cards:
        return proizvodi

    for card in cards:
        naziv_el = card.select_one("h3.mt-2")
        if not naziv_el:
            continue
        naziv = naziv_el.get_text(strip=True)

        nova_el = card.select_one("div.product-price span.active")
        stara_el = card.select_one("div.product-price span.inactive")
        nova_cijena = nova_el.get_text(strip=True) if nova_el else None
        stara_cijena = stara_el.get_text(strip=True) if stara_el else None

        proizvodi.append({
            "naziv_li": naziv,
            "nova_cijena_li": nova_cijena,
            "stara_cijena_li": stara_cijena
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
    return {"data": proizvodi, "title": "Links"}

#uvicorn scraper_svijetmedija:app --reload --port 8002