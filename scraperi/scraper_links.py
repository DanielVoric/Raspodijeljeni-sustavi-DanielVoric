import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .celery_app import app


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def _parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    s = text.strip()
    s = ''.join(ch for ch in s if ch.isdigit() or ch in ',.')
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None

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

        new_val = _parse_price(price_new)
        old_val = _parse_price(price_old)
        discount = None
        if new_val is not None and old_val and old_val > 0:
            discount = round((old_val - new_val) / old_val * 100, 2)

        products.append({
            "name": title,
            "price_new": price_new,
            "price_old": price_old,
            "discount_pct": discount,
            "source": "links",
        })

    return products


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
