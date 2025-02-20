# core/scrapers/author_books_scraper.py
from bs4 import BeautifulSoup
from pathlib import Path
import re
from urllib.parse import urlencode
from ..utils.http import GoodreadsDownloader

class AuthorBooksScraper:
   """Scrapes list of books by an author"""
   
   def __init__(self, scrape: bool = False, max_pages: int = None):
       self.downloader = GoodreadsDownloader(scrape)
       self.max_pages = max_pages
   
   def scrape_author_books(self, author_id: str) -> dict:
       """
       Get list of all books by author
       Expected output:
       {
           'author_id': str,
           'author_name': str,
           'books': [
               {
                   'goodreads_id': str,
                   'title': str,
                   'published_date': str
               }
           ]
       }
       """
       print(f"Scraping books for author: {author_id}")
       books = []
       author_name = None
       current_page = 1
       
       # Get first page to check total pages
       url = self._get_page_url(author_id, current_page)
       if not self.downloader.download_url(url):
           return None
           
       html = self._read_html(author_id, current_page)
       if not html:
           return None
           
       try:
           soup = BeautifulSoup(html, 'html.parser')
           pagination = self._extract_pagination(soup)
           total_pages = pagination['total_pages']
           
           # Check if total pages exceeds max_pages limit
           if self.max_pages and total_pages > self.max_pages:
               print(f"Skipping author {author_id} - has {total_pages} pages (max: {self.max_pages})")
               return None
               
           # Get author name and first page of books
           author_name = self._extract_author_name(soup)
           page_books = self._extract_books(soup)
           books.extend(page_books)
           
           # Continue with remaining pages
           while current_page < total_pages:
               current_page += 1
               url = self._get_page_url(author_id, current_page)
               if not self.downloader.download_url(url):
                   break
                   
               html = self._read_html(author_id, current_page)
               if not html:
                   break
                   
               try:
                   soup = BeautifulSoup(html, 'html.parser')
                   page_books = self._extract_books(soup)
                   books.extend(page_books)
                   print(f"Processing page {current_page} of {total_pages}")
               except Exception as e:
                   print(f"Error processing page {current_page}: {e}")
                   break
                   
       except Exception as e:
           print(f"Error processing first page: {e}")
           return None
       
       # Filter to only include books with dates
       dated_books = [b for b in books if b.get('published_date')]
       
       return {
           'author_id': author_id,
           'author_name': author_name,
           'books': dated_books
       }
   
   def _get_page_url(self, author_id: str, page: int) -> str:
       """Get URL for author's books page"""
       base = f"https://www.goodreads.com/author/list/{author_id}"
       params = {
           'page': page,
           'per_page': 100,
           'utf8': '✓',
           'sort': 'original_publication_year'
       }
       return f"{base}?{urlencode(params)}"
   
   def _read_html(self, author_id: str, page: int) -> str:
       """Read downloaded HTML file"""
       query = f"page={page}&per_page=100&utf8=%E2%9C%93&sort=original_publication_year"
       path = Path('data/cache/author/list') / f"{author_id}{query}.html"
       try:
           with open(path, 'r', encoding='utf-8') as f:
               return f.read()
       except Exception as e:
           print(f"Error reading HTML file: {e}")
           return None
   
   def _extract_author_name(self, soup) -> str:
       """Extract author name"""
       name_link = soup.find('a', class_='authorName')
       if name_link:
           return name_link.text.strip()
       return None
   
   def _extract_books(self, soup) -> list:
       """Extract books from page"""
       books = []
       book_rows = soup.find_all('tr', itemtype='http://schema.org/Book')
       
       for row in book_rows:
           book_link = row.find('a', class_='bookTitle')
           if not book_link:
               continue
               
           # Get title and ID
           book = {
               'title': book_link.find('span', itemprop='name').text.strip(),
               'goodreads_id': None,
               'published_date': None
           }
           
           # Get book ID from URL
           url_match = re.search(r'/show/(\d+)', book_link['href'])
           if url_match:
               book['goodreads_id'] = url_match.group(1)
               
           # Get publication date
           grey_text = row.find('span', class_='greyText smallText uitext')
           if grey_text:
               text = grey_text.get_text(strip=True)
               for prefix in ['expected publication', 'published']:
                   if prefix in text.lower():
                       year_match = re.search(rf'{prefix}\s*(\d{{4}})', text, re.I)
                       if year_match:
                           book['published_date'] = year_match.group(1)
                           break
           
           if book['goodreads_id'] and book['title']:
               books.append(book)
               
       return books
   
   def _extract_pagination(self, soup) -> dict:
       """Extract pagination information"""
       pagination = {'current_page': 1, 'total_pages': 1}
       
       # Find pagination div
       div = soup.find('div', style='float: right')
       if div:
           # Get current page
           current = div.find('em', class_='current')
           if current:
               try:
                   pagination['current_page'] = int(current.text.strip())
               except ValueError:
                   pass
           
           # Get max page number
           max_page = 1
           for link in div.find_all('a'):
               try:
                   page_num = int(link.text.strip())
                   max_page = max(max_page, page_num)
               except ValueError:
                   continue
                   
           pagination['total_pages'] = max_page
           
       return pagination