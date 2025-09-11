import requests
from bs4 import BeautifulSoup
import re
from .celery_app import app

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
        new_el = card.select_one("span.standard-price.price-akcija")
        price_new = new_el.get_text(strip=True) if new_el else "unknown"

        old_container = card.select_one("div.pricelistpriceLow")
        old_span = old_container.find("span") if old_container else None
        price_old_text = old_span.get_text(strip=True) if old_span else "unknown"

        def _parse_price(text: str | None):
            if not text:
                return None
            s = text.strip()
            s = ''.join(ch for ch in s if ch.isdigit() or ch in ',.')
            s = s.replace('.', '').replace(',', '.')
            try:
                return float(s)
            except ValueError:
                return None

        new_val = _parse_price(price_new)
        old_val = _parse_price(price_old_text)
        discount = None
        if new_val is not None and old_val and old_val > 0:
            discount = round((old_val - new_val) / old_val * 100, 2)

        products.append({
            "name": product_title,
            "price_new": price_new,
            "price_old": price_old_text,
            "discount_pct": discount,
            "source": "instar",
        })

    return products


#Pronalazi zadnju stranicu
def find_total_pages_from_indicator(soup: BeautifulSoup) -> int | None:
    el = soup.select_one("span.pageNo")
    text = el.get_text(" ", strip=True) if el else soup.get_text(" ", strip=True)
    page_num = re.search(r"str\.?\s*\d+\s*/\s*(\d+)", text, flags=re.IGNORECASE)
    if page_num:
        try:
            return int(page_num.group(1))
        except ValueError:
            return None
    return None




@app.task(name='scraperi.scraper_instar.scrape_instar')
def scrape_instar():
    url = "https://www.instar-informatika.hr/hit-proizvod/13/offer/?p={page}&s=70"
    first_soup = fetch_soup(url.format(page=1))
    total_pages = find_total_pages_from_indicator(first_soup)
    last_page = total_pages if total_pages else 1
    final_soup = first_soup if last_page == 1 else fetch_soup(url.format(page=last_page))
    products = parse_products(final_soup)
    return products
