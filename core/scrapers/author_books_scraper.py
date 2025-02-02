# core/scrapers/author_books_scraper.py
from bs4 import BeautifulSoup
from pathlib import Path
import re
from urllib.parse import urlencode
from ..utils.http import GoodreadsDownloader

class AuthorBooksScraper:
   """Scrapes list of books by an author"""
   
   def __init__(self, scrape: bool = False):
       self.downloader = GoodreadsDownloader(scrape)
   
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
       
       while True:
           # Get page content
           url = self._get_page_url(author_id, current_page)
           if not self.downloader.download_url(url):
               if books:  # Return what we have if not first page
                   break
               return None
           
           # Read the downloaded page
           html = self._read_html(author_id, current_page)
           if not html:
               if books:
                   break
               return None
               
           try:
               # Parse page content
               soup = BeautifulSoup(html, 'html.parser')
               
               # Get author name on first page
               if not author_name:
                   author_name = self._extract_author_name(soup)
               
               # Get books from this page
               page_books = self._extract_books(soup)
               books.extend(page_books)
               
               # Check pagination
               pagination = self._extract_pagination(soup)
               print(f"Processing page {pagination['current_page']} of {pagination['total_pages']}")
               
               if current_page >= pagination['total_pages']:
                   break
                   
               current_page += 1
               
           except Exception as e:
               print(f"Error processing page {current_page}: {e}")
               if books:
                   break
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