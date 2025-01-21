import requests
from utils.data_cleaner import clean_price, clean_address, extract_size
from bs4 import BeautifulSoup
import csv
import time
from utils.data_cleaner import clean_price, clean_address, extract_size

def scrape_openrent(output_csv='openrent_data.csv'):
    print("Starting OpenRent scraping...")
    listings = []
    page = 1
    
    base_url = "https://www.openrent.co.uk/properties-to-rent/london"
    
    while len(listings) < 1000:
        response = requests.get(base_url, params={"page": page})
        time.sleep(2)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            property_cards = soup.select("div.property")

            for card in property_cards:
                if len(listings) >= 1000:
                    break

                address = card.select_one("div.location").text.strip()
                price = clean_price(card.select_one("div.price strong").text)
                property_type = card.select_one("div.property-type").text.strip()
                size = extract_size(card.select_one("div.size").text if card.select_one("div.size") else None)
                lat = card.get('data-latitude', '0')
                lng = card.get('data-longitude', '0')
                
                listings.append({
                    "url": f"https://www.openrent.co.uk{card.select_one('h2 a')['href']}",
                    "address": clean_address(address),
                    "monthly_price": price,
                    "property_type": property_type,
                    "size_sqm": size,
                    "latitude": float(lat),
                    "longitude": float(lng),
                    "deposit": price * 5 if price else None,
                    "available_from": card.select_one("div.available-date").text.strip() if card.select_one("div.available-date") else None
                })

            page += 1
        else:
            print(f"Failed to retrieve page {page}. Status code: {response.status_code}")
            break

    fieldnames = ["url", "address", "monthly_price", "property_type", "size_sqm", 
                 "latitude", "longitude", "deposit", "available_from"]
    with open(output_csv, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(listings[:1000])

    print(f"Finished scraping OpenRent. Results saved to {output_csv}")