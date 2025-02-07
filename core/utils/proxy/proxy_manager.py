# proxy_manager.py
import requests
import re
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Optional
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

@dataclass
class Proxy:
   ip: str
   port: str
   last_used: datetime = None
   fail_count: int = 0
   
class ProxyManager:
   def __init__(self, max_fails: int = 3, cooldown_minutes: int = 5):
       # Get the directory where proxy_manager.py is located
       self.proxy_dir = Path(__file__).parent
       
       self.proxies: List[Proxy] = []
       self.current_index = 0
       self.max_fails = max_fails
       self.cooldown = timedelta(minutes=cooldown_minutes)
        
       # Update file paths to be relative to proxy directory
       self.proxy_file = self.proxy_dir / "working_proxies.txt"
       self.metadata_file = self.proxy_dir / "proxy_metadata.json"
       self.sources_file = self.proxy_dir / "sources.json"
        
       self.load_proxies()
    

   @staticmethod
   def _load_sources(file_path: str) -> List[dict]:
       # Update to use Path object
       with open(file_path, 'r') as f:
           return json.load(f)

   def load_proxies(self) -> None:
       if self._should_refresh_proxies():
           print("Fetching fresh proxies...")
           sources = self._load_sources(self.sources_file)
           raw_proxies = self._fetch_all_proxies(sources)
           valid_proxies = self._validate_proxies(raw_proxies)
           self.proxies = [Proxy(ip=ip, port=port) for ip, port in valid_proxies]
           self._save_proxies_with_timestamp()
       else:
           print("Loading cached proxies...")
           self._load_saved_proxies()

   def _should_refresh_proxies(self) -> bool:
       try:
           with open(self.metadata_file, 'r') as f:
               metadata = json.load(f)
               last_update = datetime.fromisoformat(metadata['last_update'])
               return datetime.now() - last_update > timedelta(days=2)
       except (FileNotFoundError, json.JSONDecodeError, KeyError):
           return True

   def _load_saved_proxies(self) -> None:
       try:
           with open(self.proxy_file, 'r') as f:
               proxy_lines = f.read().splitlines()
               self.proxies = []
               for line in proxy_lines:
                   ip, port = line.split(':')
                   self.proxies.append(Proxy(ip=ip, port=port))
           print(f"Loaded {len(self.proxies)} cached proxies")
       except FileNotFoundError:
           print("No cached proxies found, fetching new ones...")
           self.load_proxies()

   def _save_proxies_with_timestamp(self) -> None:
       with open(self.proxy_file, 'w') as f:
           f.write("\n".join(f"{p.ip}:{p.port}" for p in self.proxies))
       
       with open(self.metadata_file, 'w') as f:
           json.dump({
               'last_update': datetime.now().isoformat(),
               'count': len(self.proxies)
           }, f)
       print(f"Saved {len(self.proxies)} proxies with timestamp")

   def get_proxy(self) -> dict:
       if not self.proxies:
           self.load_proxies()
           
       proxy = self._get_next_valid_proxy()
       proxy_str = f"http://{proxy.ip}:{proxy.port}"
       return {"http": proxy_str, "https": proxy_str}

   def mark_failed(self) -> None:
       if self.proxies:
           current = self.proxies[self.current_index]
           current.fail_count += 1
           if current.fail_count >= self.max_fails:
               self.proxies.pop(self.current_index)
               if self.current_index >= len(self.proxies):
                   self.current_index = 0

   def _get_next_valid_proxy(self) -> Proxy:
       start_index = self.current_index
       while True:
           current = self.proxies[self.current_index]
           
           if (not current.last_used or 
               datetime.now() - current.last_used > self.cooldown):
               current.last_used = datetime.now()
               return current
               
           self.current_index = (self.current_index + 1) % len(self.proxies)
           if self.current_index == start_index:
               time.sleep(self.cooldown.seconds)

   @staticmethod
   def _load_sources(file_path: str) -> List[dict]:
       with open(file_path, 'r') as f:
           return json.load(f)

   def _fetch_all_proxies(self, sources: List[dict]) -> List[Tuple[str, str]]:
       all_proxies = []
       with ThreadPoolExecutor(max_workers=10) as executor:
           futures = [
               executor.submit(
                   self._fetch_proxies,
                   source["source"],
                   source.get("pattern", ""),
                   source.get("is_json", False)
               )
               for source in sources
           ]
           for future in futures:
               all_proxies.extend(future.result())
       return all_proxies

   @staticmethod
   def _fetch_proxies(source: str, pattern: str, is_json: bool) -> List[Tuple[str, str]]:
       print(f"Attempting to fetch from {source}")
       try:
           response = requests.get(source, timeout=10)
           print(f"Response received from {source}: {response.status_code}")
           response.raise_for_status()

           if is_json:
               data = response.json().get('data', [])
               proxies = [(entry['ip'], str(entry['port'])) 
                       for entry in data 
                       if 'ip' in entry and 'port' in entry]
           else:
               proxies = re.findall(pattern, response.text)
           
           print(f"Found {len(proxies)} proxies from {source}")
           return proxies
       except Exception as e:
           print(f"Failed to fetch from {source}: {e}")
           return []

   def _validate_proxies(self, proxies: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
       print(f"Validating {len(proxies)} proxies...")
       valid_proxies = []
       with ThreadPoolExecutor(max_workers=20) as executor:
           futures = [
               executor.submit(self._validate_proxy, ip, port)
               for ip, port in proxies
           ]
           for future in futures:
               if result := future.result():
                   valid_proxies.append(result)
       print(f"Found {len(valid_proxies)} valid proxies")
       return valid_proxies

   @staticmethod
   def _validate_proxy(ip: str, port: str) -> Optional[Tuple[str, str]]:
       proxy = f"http://{ip}:{port}"
       try:
           response = requests.get(
               "https://httpbin.org/ip",
               proxies={"http": proxy, "https": proxy},
               timeout=5
           )
           return (ip, port) if response.status_code == 200 else None
       except:
           return None

   @staticmethod
   def get_headers() -> dict:
       # Choose a complete browser profile rather than just changing User-Agent
    browser_profiles = [
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
    ]
    
    # Choose and stick with one browser profile per session
    return random.choice(browser_profiles)

   def get_proxies(self):
       """Get list of proxies, refreshing if needed"""
       if self._should_refresh_proxies():
           self.load_proxies()
       return self.proxies