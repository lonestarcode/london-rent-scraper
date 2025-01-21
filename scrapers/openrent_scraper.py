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
            # Use multiple selectors to find property cards
            property_cards = (
                soup.select("div.property") or 
                soup.select("[data-listing]") or
                soup.select(".listing-item")
            )

            for card in property_cards:
                if len(listings) >= 1000:
                    break

                # Extract data with multiple fallback selectors
                address = extract_text(card, [
                    "div.location", 
                    ".listing-address",
                    "[data-address]"
                ])
                
                price = extract_price(card, [
                    "div.price strong",
                    ".listing-price",
                    "[data-price]"
                ])
                
                property_type = extract_text(card, [
                    "div.property-type",
                    ".listing-type",
                    "[data-property-type]"
                ])
                
                size = extract_size_from_element(card, [
                    "div.size",
                    ".listing-size",
                    "[data-size]"
                ])
                
                # Get coordinates with fallbacks
                lat = (
                    card.get('data-latitude') or 
                    card.get('data-lat') or 
                    '0'
                )
                lng = (
                    card.get('data-longitude') or 
                    card.get('data-lng') or 
                    '0'
                )
                
                # Only add listing if we have essential data
                if address and price:
                    listings.append({
                        "url": extract_url(card),
                        "address": clean_address(address),
                        "monthly_price": price,
                        "property_type": property_type,
                        "size_sqm": size,
                        "latitude": float(lat),
                        "longitude": float(lng),
                        "deposit": price * 5 if price else None,
                        "available_from": extract_text(card, [
                            "div.available-date",
                            ".listing-available-date",
                            "[data-available-date]"
                        ])
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

def extract_text(element, selectors):
    """Try multiple selectors to extract text"""
    for selector in selectors:
        found = element.select_one(selector)
        if found:
            return found.text.strip()
    return None

def extract_price(element, selectors):
    """Try multiple selectors to extract and clean price"""
    price_text = extract_text(element, selectors)
    return clean_price(price_text) if price_text else None

def extract_size_from_element(element, selectors):
    """Try multiple selectors to extract size"""
    size_text = extract_text(element, selectors)
    return extract_size(size_text) if size_text else None

def extract_url(card):
    """Extract listing URL with fallbacks"""
    link = (
        card.select_one('h2 a') or
        card.select_one('.listing-title a') or
        card.select_one('[data-listing-url]')
    )
    if link:
        href = link.get('href')
        if href:
            return f"https://www.openrent.co.uk{href}"
    return None