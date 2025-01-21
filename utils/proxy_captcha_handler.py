import requests
from twocaptcha import TwoCaptcha
import time
import random
from typing import Dict, Optional, List
import logging
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class ProxyRotator:
    def __init__(self, proxy_list: List[Dict[str, str]] = None):
        self.proxy_list = proxy_list or self._get_default_proxies()
        self.proxy_failures = {}
        self.proxy_last_used = {}
        self.max_failures = 3
        self.cooldown_minutes = 10

    def _get_default_proxies(self) -> List[Dict[str, str]]:
        """Configure multiple proxy services"""
        proxies = []
        # Bright Data proxies
        bright_data = {
            'username': 'YOUR_USERNAME_1',
            'password': 'YOUR_PASSWORD_1',
            'host': 'brd.superproxy.io',
            'port': '22225'
        }
        # IPRoyal proxies
        iproyal = {
            'username': 'YOUR_USERNAME_2',
            'password': 'YOUR_PASSWORD_2',
            'host': 'proxy.iproyal.com',
            'port': '12321'
        }
        proxies.extend([bright_data, iproyal])
        return proxies

    def get_proxy(self) -> Dict[str, str]:
        """Get least recently used working proxy"""
        available_proxies = [p for p in self.proxy_list 
                           if self.proxy_failures.get(str(p), 0) < self.max_failures]
        
        if not available_proxies:
            raise Exception("No working proxies available")

        # Sort by last used time (or never used)
        available_proxies.sort(
            key=lambda p: self.proxy_last_used.get(str(p), datetime.min)
        )
        
        proxy = available_proxies[0]
        self.proxy_last_used[str(proxy)] = datetime.now()
        
        proxy_auth = f"{proxy['username']}:{proxy['password']}"
        return {
            "http": f"http://{proxy_auth}@{proxy['host']}:{proxy['port']}",
            "https": f"http://{proxy_auth}@{proxy['host']}:{proxy['port']}"
        }

    def mark_proxy_failure(self, proxy: Dict[str, str]):
        """Track proxy failures"""
        proxy_key = str(proxy)
        self.proxy_failures[proxy_key] = self.proxy_failures.get(proxy_key, 0) + 1
        if self.proxy_failures[proxy_key] >= self.max_failures:
            logging.warning(f"Proxy {proxy['host']} exceeded failure threshold")

class RateLimiter:
    def __init__(self, requests_per_minute: int = 20):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        
    def wait_if_needed(self):
        """Implement rate limiting"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if req_time > minute_ago]
        
        if len(self.requests) >= self.requests_per_minute:
            sleep_time = (self.requests[0] - minute_ago).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.requests = self.requests[1:]
        
        self.requests.append(now)

class ProxyCaptchaHandler:
    def __init__(self, two_captcha_key: str):
        self.solver = TwoCaptcha(two_captcha_key)
        self.proxy_rotator = ProxyRotator()
        self.rate_limiter = RateLimiter()
        
        # Configure retry strategy
        self.retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        self.adapter = HTTPAdapter(max_retries=self.retry_strategy)
        
        # Configure session
        self.session = requests.Session()
        self.session.mount("https://", self.adapter)
        self.session.mount("http://", self.adapter)

    def solve_captcha(self, site_key: str, url: str) -> Optional[str]:
        """Solve CAPTCHA using 2captcha service"""
        try:
            result = self.solver.recaptcha(
                sitekey=site_key,
                url=url,
                version='v2',
                enterprise=0
            )
            return result['code']
        except Exception as e:
            logging.error(f"CAPTCHA solving failed: {e}")
            return None

    def handle_request(self, url: str, params: Dict = None, headers: Dict = None) -> requests.Response:
        """Make a request with proxy rotation and CAPTCHA handling"""
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                # Apply rate limiting
                self.rate_limiter.wait_if_needed()
                
                # Get proxy and make request
                proxies = self.proxy_rotator.get_proxy()
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    proxies=proxies,
                    timeout=30
                )
                
                # Handle different types of blocking
                if response.status_code == 403:
                    if 'captcha' in response.text.lower():
                        logging.info("CAPTCHA detected, attempting to solve...")
                        site_key = self._extract_captcha_key(response.text)
                        captcha_token = self.solve_captcha(site_key, url)
                        
                        if captcha_token:
                            if params is None:
                                params = {}
                            params['g-recaptcha-response'] = captcha_token
                            continue
                    else:
                        logging.warning("IP possibly blocked, rotating proxy...")
                        self.proxy_rotator.mark_proxy_failure(proxies)
                        continue
                
                # Success case
                if response.status_code == 200:
                    return response
                
                # Other error cases
                logging.error(f"Request failed with status code: {response.status_code}")
                current_retry += 1
                
            except requests.exceptions.RequestException as e:
                logging.error(f"Request failed: {e}")
                self.proxy_rotator.mark_proxy_failure(proxies)
                current_retry += 1
                time.sleep(random.uniform(2, 5))
        
        raise Exception("Max retries exceeded")

    def _extract_captcha_key(self, html_content: str) -> str:
        """Extract reCAPTCHA site key from HTML"""
        # This is a simplified example - adjust based on actual HTML structure
        import re
        match = re.search(r'data-sitekey="([^"]+)"', html_content)
        return match.group(1) if match else "SITE_KEY_HERE" 