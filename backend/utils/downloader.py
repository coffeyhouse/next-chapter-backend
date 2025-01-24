# downloader.py
import requests
from pathlib import Path
from urllib.parse import urlparse
from backend.utils.proxy.proxy_manager import ProxyManager

class GoodreadsDownloader:
   def __init__(self):
       self.proxy_manager = ProxyManager()
       self.last_successful_proxy = None
       self.last_successful_headers = None
       
   def download_url(self, url):
       parsed_url = urlparse(url)
       path_parts = parsed_url.path.strip('/').split('/')
       
       local_path = self._get_local_path(parsed_url, path_parts)
       
       if local_path.exists():
           print(f"Skipping {url} - already downloaded")
           return True
           
       local_path.parent.mkdir(parents=True, exist_ok=True)
       
       # Try last successful proxy first if available
       if self.last_successful_proxy and self.last_successful_headers:
           try:
               print(f"\nRetrying last successful proxy: {self.last_successful_proxy['http']}")
               response = requests.get(
                   url, 
                   headers=self.last_successful_headers,
                   proxies=self.last_successful_proxy,
                   timeout=10
               )
               response.raise_for_status()
               
               local_path.write_text(response.text, encoding='utf-8')
               print(f"Successfully downloaded: {url} to {local_path}")
               return True
           except requests.RequestException:
               print("Last successful proxy failed, trying new proxies...")
               self.last_successful_proxy = None
               self.last_successful_headers = None
       
       # Try new proxies if needed
       while True:
           try:
               current_proxy = self.proxy_manager.get_proxy()
               current_headers = self.proxy_manager.get_headers()
                
               print(f"\nTrying proxy: {current_proxy['http']}")
               print(f"Using User-Agent: {current_headers['User-Agent'][:60]}...")
               
               response = requests.get(
                   url, 
                   headers=current_headers,
                   proxies=current_proxy,
                   timeout=10
               )
               response.raise_for_status()
               
               local_path.write_text(response.text, encoding='utf-8')
               print(f"Successfully downloaded: {url} to {local_path}")
               
               # Store successful proxy and headers
               self.last_successful_proxy = current_proxy
               self.last_successful_headers = current_headers
               
               return True
               
           except requests.RequestException as e:
               print(f"Download error with proxy {current_proxy['http']}: {str(e)}")
               self.proxy_manager.mark_failed()
               continue

   def _get_local_path(self, parsed_url, path_parts):
        path = Path('data/exported_html')
        full_path = '/'.join(path_parts).rstrip('/')
        query = parsed_url.query if parsed_url.query else ''
        return path / (full_path + query + '.html')

def main():
   downloader = GoodreadsDownloader()
   
   try:
       with open('urls.txt', 'r') as f:
           urls = [line.strip() for line in f if line.strip()]
   except FileNotFoundError:
       print("urls.txt not found")
       return
       
   print(f"Found {len(urls)} URLs to process")
   
   for url in urls:
       downloader.download_url(url)

if __name__ == "__main__":
   main()