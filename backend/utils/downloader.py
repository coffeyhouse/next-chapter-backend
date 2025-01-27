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
               print(f"\nUsing last successful proxy: {self.last_successful_proxy['http']}")
               response = requests.get(
                   url, 
                   headers=self.last_successful_headers,
                   proxies=self.last_successful_proxy,
                   timeout=10
               )
               response.raise_for_status()
               
               # If successful, write the content and return
               local_path.write_text(response.text, encoding='utf-8')
               print(f"Successfully downloaded: {url} to {local_path}")
               return True
               
           except requests.RequestException as e:
               if '502 Bad Gateway' in str(e):
                   # If we get a 502, the proxy might be temporarily overloaded
                   # Reset it and try new ones
                   print(f"Last successful proxy returned 502, trying new proxies...")
                   self.last_successful_proxy = None
                   self.last_successful_headers = None
               else:
                   # For other errors, retry with the same proxy a few times
                   for _ in range(2):  # Try 2 more times
                       try:
                           response = requests.get(
                               url, 
                               headers=self.last_successful_headers,
                               proxies=self.last_successful_proxy,
                               timeout=10
                           )
                           response.raise_for_status()
                           local_path.write_text(response.text, encoding='utf-8')
                           print(f"Successfully downloaded on retry: {url} to {local_path}")
                           return True
                       except requests.RequestException:
                           continue
                   
                   print(f"Last successful proxy failed after retries, trying new proxies...")
                   self.last_successful_proxy = None
                   self.last_successful_headers = None
       
       # If we get here, either there was no last successful proxy or it failed
       return self._try_new_proxies(url, local_path)

   def _get_local_path(self, parsed_url, path_parts):
        path = Path('data/exported_html')
        full_path = '/'.join(path_parts).rstrip('/')
        query = parsed_url.query if parsed_url.query else ''
        return path / (full_path + query + '.html')

   def _try_new_proxies(self, url, local_path):
       """Try new proxies until one works"""
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