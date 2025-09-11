
#uvicorn scraper_instar:app --reload --port 8000

from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import re
from .celery_app import app

app_scraper_instar= FastAPI()

# header - ne radi bez
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}

# dohvaca cijeli html sadrzaj stranice
def fetch_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def parse_products(soup: BeautifulSoup):
    products = []

    cards = soup.find_all("div", class_="product-item-box")

    for card in cards:
        title_el = (
            card.find("h2", class_="title")
        )
        if not title_el:
            continue
        product_title = title_el.get_text(strip=True)
        # current price
        new_el = card.select_one("span.standard-price.price-akcija")
        price_new = new_el.get_text(strip=True) if new_el else "unknown"

        # old price
        old_container = card.select_one("div.pricelistpriceLow")
        old_span = old_container.find("span") if old_container else None
        price_old_text = old_span.get_text(strip=True) if old_span else "unknown"

        products.append({
            "name": product_title,
            "price_new": price_new,
            "price_old": price_old_text,
            "source": "instar",
        })

    return products


#Pronalazi zadnju stranicu
def find_total_pages_from_indicator(soup: BeautifulSoup) -> int | None:
    el = soup.select_one("span.pageNo")
    text = el.get_text(" ", strip=True) if el else soup.get_text(" ", strip=True)
    broj_str = re.search(r"str\.?\s*\d+\s*/\s*(\d+)", text, flags=re.IGNORECASE)
    if broj_str:
        try:
            return int(broj_str.group(1))
        except ValueError:
            return None
    return None


@app_scraper_instar.get("/")  
async def scrape_all_pages(): 
    title = "Instar"
    url = "https://www.instar-informatika.hr/hit-proizvod/13/offer/?p={page}&s=70"
    first_soup = fetch_soup(url.format(page=1))
    ukupno_stranica = find_total_pages_from_indicator(first_soup)
    zadnja_stranica = ukupno_stranica if ukupno_stranica else 1
    print(f"Zadnja stranica je: {zadnja_stranica}")

    # Ako je vise stranica, uzmi zadnju, inace samo prva
    final_soup = first_soup if zadnja_stranica == 1 else fetch_soup(url.format(page=zadnja_stranica))

    products = parse_products(final_soup)
    print(f"Scraping page {zadnja_stranica} -> {len(products)} products")
    return {"data": products, "title": title}

#uvicorn scraper_instar:app --reload --port 8000


@app.task(name='scraperi.scraper_instar.scrape_instar')
def scrape_instar():
    url = "https://www.instar-informatika.hr/hit-proizvod/13/offer/?p={page}&s=70"
    first_soup = fetch_soup(url.format(page=1))
    ukupno_stranica = find_total_pages_from_indicator(first_soup)
    zadnja_stranica = ukupno_stranica if ukupno_stranica else 1
    final_soup = first_soup if zadnja_stranica == 1 else fetch_soup(url.format(page=zadnja_stranica))
    products = parse_products(final_soup)
    return products
