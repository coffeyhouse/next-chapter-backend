import requests
from urllib.parse import urlparse
from core.utils.proxy.proxy_manager import ProxyManager
from core.utils.rate_limit import RateLimiter

class GoodreadsDownloader:
    def __init__(self, scrape=False):
        self.scrape = scrape
        if self.scrape:
            self.proxy_manager = ProxyManager()
            self.rate_limiter = RateLimiter()
        else:
            self.proxy_manager = None
            self.rate_limiter = None
        self.last_successful_proxy = None
        self.last_successful_headers = None
        
    def download_url(self, url) -> tuple[bool, str]:
        """
        Download a URL with rate limiting and proxy support.
        
        Args:
            url: The URL to download
            
        Returns:
            Tuple of (success: bool, content: str)
            If success is False, content will be empty string
        """
        # Apply rate limiting before download if scraping
        if self.scrape and self.rate_limiter:
            self.rate_limiter.delay()
            
        # If scraping is disabled, return failure
        if not self.scrape:
            print(f"Skipping {url} - scraping disabled")
            return False, ""
            
        print(f"Scraping enabled, attempting to download {url}")
        return self._try_new_proxies(url)

    def _try_new_proxies(self, url) -> tuple[bool, str]:
        """Try new proxies until one works"""
        if not self.scrape:
            return False, ""
            
        for proxy in self.proxy_manager.get_proxies():
            headers = self.proxy_manager.get_headers()
            proxy_dict = {'http': f'http://{proxy.ip}:{proxy.port}'}
            
            try:
                print(f"\nTrying proxy: {proxy_dict['http']}")
                response = requests.get(
                    url,
                    headers=headers,
                    proxies=proxy_dict,
                    timeout=10
                )
                response.raise_for_status()
                
                # Save successful proxy and headers for future use
                self.last_successful_proxy = proxy_dict
                self.last_successful_headers = headers
                
                print(f"Successfully downloaded: {url}")
                return True, response.text
                
            except requests.RequestException as e:
                print(f"Proxy failed: {str(e)}")
                continue
                
        print("All proxies failed")
        return False, ""