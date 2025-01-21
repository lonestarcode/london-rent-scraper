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
    """Extract data from a property card with multiple fallback selectors"""
    try:
        # Extract address with fallbacks
        address = extract_text(card, [
            "address.propertyCard-address",
            ".property-address",
            "[data-test='address']",
            "[itemprop='address']"
        ])

        # Extract price with fallbacks
        price = extract_price(card, [
            "div.propertyCard-priceValue",
            ".property-price",
            "[data-test='price']",
            "[itemprop='price']"
        ])

        # Extract property type with fallbacks
        property_type = extract_text(card, [
            "h2.propertyCard-title",
            ".property-type",
            "[data-test='property-type']"
        ])

        # Extract size with fallbacks
        size = extract_size_from_element(card, [
            "div.propertyCard-size",
            ".property-size",
            "[data-test='size']"
        ])

        # Extract coordinates with fallbacks
        coordinates = (
            card.get('data-lat-lng') or
            card.get('data-coordinates') or
            '0,0'
        ).split(',')

        # Extract URL with fallbacks
        url = extract_url(card, [
            "a.propertyCard-link",
            ".property-link",
            "[data-test='property-link']"
        ])

        # Only return listing if we have essential data
        if address and price and url:
            return {
                "url": url,
                "address": clean_address(address),
                "monthly_price": price,
                "property_type": property_type,
                "size_sqm": size,
                "latitude": float(coordinates[0]),
                "longitude": float(coordinates[1]),
                "deposit": price * 5 if price else None,
                "available_from": extract_text(card, [
                    "div.propertyCard-available",
                    ".property-available",
                    "[data-test='available-from']"
                ])
            }
    except Exception as e:
        logging.error(f"Error parsing property card: {e}")
    return None

def extract_url(card, selectors):
    """Extract listing URL with fallbacks"""
    for selector in selectors:
        link = card.select_one(selector)
        if link and link.get('href'):
            return f"https://www.rightmove.co.uk{link['href']}"
    return None

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