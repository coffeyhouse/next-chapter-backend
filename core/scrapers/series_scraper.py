# core/scrapers/series_scraper.py
from bs4 import BeautifulSoup
from pathlib import Path
import re
from ..utils.http import GoodreadsDownloader

class SeriesScraper:
   """Scrapes series information and books"""
   
   def __init__(self, scrape: bool = False):
       self.downloader = GoodreadsDownloader(scrape)
   
   def scrape_series(self, series_id: str) -> dict:
       """
       Get series info and books
       Expected output:
       {
           'goodreads_id': str,
           'name': str, 
           'books': [
               {
                   'goodreads_id': str,
                   'title': str,
                   'order': float
               }
           ]
       }
       """
       print(f"Scraping series: {series_id}")
       
       # Get series page
       url = self._get_series_url(series_id)
       if not self.downloader.download_url(url):
           print(f"Failed to download series page for ID: {series_id}")
           return None
           
       # Read HTML
       html = self._read_html(series_id)
       if not html:
           return None
           
       try:
           soup = BeautifulSoup(html, 'html.parser')
           
           series_data = {
               'goodreads_id': series_id,
               'name': self._extract_name(soup),
               'books': self._extract_books(soup)
           }
           
           return series_data
           
       except Exception as e:
           print(f"Error parsing series data: {e}")
           return None
   
   def _get_series_url(self, series_id: str) -> str:
       """Get Goodreads URL for series"""
       return f"https://www.goodreads.com/series/show/{series_id}"
   
   def _read_html(self, series_id: str) -> str:
       """Read downloaded HTML file"""
       path = Path('data/cache/series/show') / f"{series_id}.html"
       try:
           with open(path, 'r', encoding='utf-8') as f:
               return f.read()
       except Exception as e:
           print(f"Error reading HTML file: {e}")
           return None
   
   def _extract_name(self, soup) -> str:
       """Extract series name"""
       title_element = soup.find('h1', class_='gr-h1--serif')
       if title_element:
           name = title_element.text.strip()
           # Remove " Series" from the end if present
           if name.endswith(' Series'):
               name = name[:-7]
           return name
       return None
   
   def _extract_books(self, soup) -> list:
       """Extract books in series with order"""
       books = []
       book_divs = soup.find_all('div', class_='listWithDividers__item')
       
       for book_div in book_divs:
           # Get order number
           order = None
           number_heading = book_div.find('h3', class_='gr-h3--noBottomMargin')
           if number_heading:
               number_text = number_heading.text.strip()
               try:
                   if number_text.startswith('Book '):
                       number_text = number_text[5:]
                   if '-' not in number_text:  # Skip ranges like "1-3"
                       order = float(number_text)
               except ValueError:
                   pass
           
           # Get title and ID
           title_link = book_div.find('a', class_='gr-h3--serif')
           if title_link:
               title = title_link.find('span', itemprop='name')
               if title:
                   # Extract ID from URL
                   url_match = re.search(r'/show/(\d+)', title_link['href'])
                   if url_match:
                       books.append({
                           'goodreads_id': url_match.group(1),
                           'title': title.text.strip(),
                           'order': order
                       })
       
       return books