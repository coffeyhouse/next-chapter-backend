import requests
from pathlib import Path
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
        
    def download_url(self, url):
        # Apply rate limiting before download if scraping
        if self.scrape and self.rate_limiter:
            self.rate_limiter.delay()
            
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        local_path = self._get_local_path(parsed_url, path_parts)
        
        # Check if file exists locally
        if local_path.exists():
            print(f"Using cached file: {local_path}")
            return True
            
        # If file doesn't exist and scraping is disabled, skip
        if not self.scrape:
            print(f"Skipping {url} - scraping disabled and no local file found")
            return False
            
        print(f"Scraping enabled, attempting to download {url}")
        return self._try_new_proxies(url, local_path)

    def _get_local_path(self, parsed_url, path_parts):
        path = Path('data/cache')
        full_path = '/'.join(path_parts).rstrip('/')
        query = parsed_url.query if parsed_url.query else ''
        return path / (full_path + query + '.html')

    def _try_new_proxies(self, url, local_path):
        """Try new proxies until one works"""
        if not self.scrape:
            return False
            
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
                
                local_path.write_text(response.text, encoding='utf-8')
                print(f"Successfully downloaded: {url} to {local_path}")
                return True
                
            except requests.RequestException as e:
                print(f"Proxy failed: {str(e)}")
                continue
                
        print("All proxies failed")
        return False