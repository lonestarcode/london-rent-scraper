"""
Contains helper functions for cleaning and transforming scraped data.
"""

import random
import requests
import time

def clean_price(price_str):
    if not price_str:
        return None
    return float(
        price_str.replace('£', '')
                 .replace(',', '')
                 .split()[0]
    )

def clean_address(address_str):
    if not address_str:
        return None
    return address_str.strip()

def extract_size(size_str):
    if not size_str:
        return None
    try:
        # Extract numeric value and convert to sqm
        numeric = float(''.join(filter(str.isdigit, size_str)))
        if 'sq ft' in size_str.lower():
            return round(numeric * 0.092903, 2)  # Convert sq ft to sqm
        return numeric
    except:
        return None

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        # Add more user agents
    ]
    return random.choice(user_agents)

def get_request_headers():
    return {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

def random_delay():
    time.sleep(random.uniform(2, 5))