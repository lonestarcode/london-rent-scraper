import requests
from utils.data_cleaner import clean_price, clean_address, extract_size, get_random_user_agent, get_request_headers, random_delay
from bs4 import BeautifulSoup
import csv
import time
from utils.proxy_captcha_handler import ProxyCaptchaHandler
import logging
from datetime import datetime

def scrape_rightmove(output_csv='rightmove_data.csv'):
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=f'rightmove_scraping_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )
    
    logging.info("Starting Rightmove scraping...")
    listings = []
    failed_pages = []
    
    # Initialize handler with your 2captcha API key
    handler = ProxyCaptchaHandler('YOUR_2CAPTCHA_API_KEY')
    
    base_url = "https://www.rightmove.co.uk/property-to-rent/find.html"
    params = {
        "locationIdentifier": "REGION^93917",
        "propertyType": "flat",
        "maxPrice": 5000,
        "index": 0
    }

    while len(listings) < 1000:
        try:
            response = handler.handle_request(
                base_url,
                params=params,
                headers=get_request_headers()
            )
            
            soup = BeautifulSoup(response.text, "html.parser")
            property_cards = soup.select("div.propertyCard")
            
            if not property_cards:
                logging.warning(f"No properties found on page {params['index']//24 + 1}")
                failed_pages.append(params['index']//24 + 1)
                params["index"] += 24
                continue

            for card in property_cards:
                try:
                    if len(listings) >= 1000:
                        break

                    listing = parse_property_card(card)
                    if listing:
                        listings.append(listing)
                        logging.info(f"Scraped property: {listing['address']}")
                except Exception as e:
                    logging.error(f"Error parsing property card: {e}")
                    continue

            params["index"] += 24

        except Exception as e:
            logging.error(f"Error during scraping: {e}")
            failed_pages.append(params['index']//24 + 1)
            continue

    # Save results
    save_results(listings, output_csv)
    
    # Log summary
    logging.info(f"Scraping completed. Total listings: {len(listings)}")
    if failed_pages:
        logging.warning(f"Failed pages: {failed_pages}")

def parse_property_card(card):
    """Extract data from a property card"""
    try:
        address = card.select_one("address.propertyCard-address").text.strip()
        price = clean_price(card.select_one("div.propertyCard-priceValue").text)
        property_type = card.select_one("h2.propertyCard-title").text.strip()
        size = extract_size(card.select_one("div.propertyCard-size").text if card.select_one("div.propertyCard-size") else None)
        coordinates = card.get('data-lat-lng', '0,0').split(',')
        
        return {
            "url": f"https://www.rightmove.co.uk{card.select_one('a.propertyCard-link')['href']}",
            "address": clean_address(address),
            "monthly_price": price,
            "property_type": property_type,
            "size_sqm": size,
            "latitude": float(coordinates[0]),
            "longitude": float(coordinates[1]),
            "deposit": price * 5 if price else None,
            "available_from": card.select_one("div.propertyCard-available").text.strip() if card.select_one("div.propertyCard-available") else None
        }
    except Exception as e:
        logging.error(f"Error parsing property card: {e}")
        return None

def save_results(listings, output_csv):
    """Save results to CSV file"""
    fieldnames = ["url", "address", "monthly_price", "property_type", "size_sqm", 
                 "latitude", "longitude", "deposit", "available_from"]
    try:
        with open(output_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(listings[:1000])
        logging.info(f"Results saved to {output_csv}")
    except Exception as e:
        logging.error(f"Error saving results: {e}")