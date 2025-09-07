from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup

app = FastAPI()

def scrape_page(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        products = []
        product_titles = soup.find_all("span", class_="product--title")
        actual_prices = soup.find_all("span", class_="price--default is--nowrap is--discount")
        old_prices = soup.find_all("span", class_="product--price--additional -history-price is--neutral")

        for title, actual_price, old_price in zip(product_titles, actual_prices, old_prices):
            product_name = title.get_text(strip=True)
            new_price = actual_price.get_text(strip=True)
            old_price_text = old_price.get_text(strip=True)

            products.append({
                "Proizvod": product_name,
                "nova cijena": new_price,
                "stara cijena": old_price_text
            })

        return products
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return []

@app.get("/")
async def scrape_all_pages():
    base_url = "https://www.douglas.hr/c/akcije-i-pokloni/akcije/"
    stranica = 1
    all_products = []

    while True:
        url = f"{base_url}?p=1&o=1&n=60&min=0&max=1339.24"
        #url = f"{base_url}?p={stranica}&o=1&n=60&min=0&max=1339.24"

        print(f"Scraping stranicu {stranica}...")
        products = scrape_page(url)

        if not products:
            print("Kraj")
            break

        all_products.extend(products)
        page_number += 1

    return {"data": all_products}