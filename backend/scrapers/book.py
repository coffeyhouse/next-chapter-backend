import os
from bs4 import BeautifulSoup
from pathlib import Path
import re
import json
import time
from backend.utils.downloader import GoodreadsDownloader
from backend.utils.image_downloader import download_book_cover

def extract_series(soup):
    series_info = {"name": "", "number": None, "id": None}
    
    # Try to find series info in HTML
    series_element = soup.find('h3', class_='Text__title3', attrs={'aria-label': lambda x: x and 'Book' in x and 'series' in x})
    if series_element:
        series_link = series_element.find('a')
        if series_link:
            # Extract series ID from URL
            series_match = re.search(r'/series/(\d+)', series_link['href'])
            if series_match:
                series_info["id"] = series_match.group(1)
            
            # Extract series name and number (if present)
            text = series_link.text.strip()
            if '#' in text:
                name, number = text.split('#')
                series_info["name"] = name.strip()
                try:
                    series_info["number"] = float(number.strip())
                except ValueError:
                    pass
            else:
                # Handle series without numbers
                series_info["name"] = text.strip()
    
    return series_info

def extract_title(soup):
    title_info = {'title': "", 'series': extract_series(soup)}
    
    # Find title in HTML
    title_element = soup.find('h1', attrs={'data-testid': 'bookTitle', 'aria-label': lambda x: x and 'Book title:' in x})
    if title_element:
        # Extract title from aria-label
        aria_label = title_element['aria-label']
        title = aria_label.replace('Book title:', '').strip()
        title_info['title'] = title
    
    return title_info

def extract_authors(soup):
    authors = []
    seen_authors = set()  # Track unique author IDs
    contributor_links = soup.find_all('a', class_='ContributorLink')
    
    for link in contributor_links:
        author_name = link.find('span', class_='ContributorLink__name')
        if author_name:
            author_id = None
            if 'href' in link.attrs:
                author_match = re.search(r'/author/show/(\d+)', link['href'])
                if author_match:
                    author_id = author_match.group(1)
            
            # Skip if we've seen this author ID before
            if author_id and author_id in seen_authors:
                continue
                
            # Clean up name - remove multiple spaces
            clean_name = ' '.join(author_name.text.split())
            
            # Extract role if present, default to "Author"
            role_span = link.find('span', class_='ContributorLink__role')
            role = "Author"
            if role_span:
                role_text = role_span.text.strip()
                # Remove parentheses and any whitespace
                role = role_text.replace('(', '').replace(')', '').strip()
            
            authors.append({
                'name': clean_name,
                'id': author_id,
                'role': role
            })
            
            if author_id:
                seen_authors.add(author_id)
                
    return authors

def extract_book_id(soup):
    canonical_link = soup.find('link', rel='canonical')
    if canonical_link and 'href' in canonical_link.attrs:
        id_match = re.search(r'/show/(\d+)', canonical_link['href'])
        if id_match:
            return id_match.group(1)
    return None

def extract_genres(soup):
    genres = []
    
    next_data = soup.find('script', id='__NEXT_DATA__')
    if next_data:
        try:
            data = json.loads(next_data.string)
            book_data = data.get('props', {}).get('pageProps', {}).get('apolloState', {})
            
            # Look for Book object that contains bookGenres
            for value in book_data.values():
                if isinstance(value, dict) and 'bookGenres' in value:
                    for genre_data in value['bookGenres']:
                        if isinstance(genre_data, dict) and 'genre' in genre_data:
                            genre = genre_data['genre']
                            if isinstance(genre, dict):
                                genres.append({
                                    'name': genre.get('name', ''),
                                    'url': genre.get('webUrl', '')
                                })
                    break  # Found our genres, no need to continue
        except json.JSONDecodeError:
            pass
    
    return genres

def extract_publication_info(soup):
    pub_info = {"date": None, "status": None}
    
    pub_element = soup.find('p', attrs={'data-testid': 'publicationInfo'})
    if pub_element:
        text = pub_element.text.strip()
        
        # Check if it's an expected publication
        if text.startswith('Expected publication'):
            pub_info['status'] = 'upcoming'
            pub_info['date'] = text.replace('Expected publication', '').strip()        
        elif text.startswith('First published'):
            pub_info['status'] = 'published'
            pub_info['date'] = text.replace('First published', '').strip()
        elif text.startswith('Published'):
            pub_info['status'] = 'published'
            pub_info['date'] = text.replace('Published', '').strip()
    
    return pub_info

def extract_language(data):
    return data.get('inLanguage')

def extract_pages(data):
    return data.get('numberOfPages')

def extract_isbn(data):
    return data.get('isbn')

def extract_awards(soup):
    awards = []
    next_data = soup.find('script', id='__NEXT_DATA__')
    if next_data:
        try:
            data = json.loads(next_data.string)
            apollo_state = data['props']['pageProps']['apolloState']
            
            # Find the Work object which contains awards
            for key, value in apollo_state.items():
                if key.startswith('Work:') and 'awardsWon' in value.get('details', {}):
                    awards_data = value['details']['awardsWon']
                    for award in awards_data:
                        award_info = {
                            'name': award['name'],
                            'id': None,  # Extract ID from webUrl if available
                            'category': award.get('category'),
                            'year': time.gmtime(award['awardedAt']/1000).tm_year if award.get('awardedAt') else None,
                            'designation': award.get('designation')
                        }
                        
                        # Extract ID from webUrl if present
                        if award.get('webUrl'):
                            id_match = re.search(r'/award/show/(\d+)', award['webUrl'])
                            if id_match:
                                award_info['id'] = id_match.group(1)
                        
                        awards.append(award_info)
                    break
                    
        except (json.JSONDecodeError, AttributeError):
            pass
            
    return awards

def extract_rating_info(data):
    rating_info = {'rating': None, 'rating_count': None}
    if 'aggregateRating' in data:
        rating_data = data['aggregateRating']
        rating_info['rating'] = rating_data.get('ratingValue')
        rating_info['rating_count'] = rating_data.get('ratingCount')
    return rating_info

def extract_book_details(soup):
    details = {
        'language': None,
        'pages': None,
        'isbn': None,
        'awards': [],
        'rating': None,
        'rating_count': None
    }
    
    schema_script = soup.find('script', {'type': 'application/ld+json'})
    if schema_script:
        try:
            data = json.loads(schema_script.string)
            
            details['language'] = extract_language(data)
            details['pages'] = extract_pages(data)
            details['isbn'] = extract_isbn(data)
            details['awards'] = extract_awards(soup)
            
            rating_info = extract_rating_info(data)
            details['rating'] = rating_info['rating']
            details['rating_count'] = rating_info['rating_count']
                
        except json.JSONDecodeError:
            pass
    
    return details

def extract_additional_series(soup, main_series_id=None):
    additional_series = []
    
    next_data = soup.find('script', id='__NEXT_DATA__')
    if next_data:
        try:
            data = json.loads(next_data.string)
            book_data = data.get('props', {}).get('pageProps', {}).get('apolloState', {})
            
            # Get all series
            for key, value in book_data.items():
                if isinstance(value, dict) and value.get('__typename') == 'Series':
                    # Extract series ID from webUrl
                    url = value.get('webUrl', '')
                    series_match = re.search(r'/series/(\d+)', url)
                    series_id = series_match.group(1) if series_match else None
                    
                    # Skip if this is the main series
                    if main_series_id and str(main_series_id) == str(series_id):
                        continue
                        
                    additional_series.append({
                        'name': value.get('title', ''),
                        'id': series_id,
                        'url': url
                    })
                    
        except json.JSONDecodeError:
            pass
    
    return additional_series

def extract_work_id(soup):
    next_data = soup.find('script', id='__NEXT_DATA__')
    if next_data:        
        try:
            data = json.loads(next_data.string)
            for key, value in data['props']['pageProps']['apolloState'].items():
                if isinstance(value, dict) and 'editions' in value:
                    if value['editions'].get('webUrl'):
                        # Extract work ID from the editions URL
                        return value['editions']['webUrl'].split('/')[-1].split('-')[0]
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
    return None

def extract_description(soup):
    next_data = soup.find('script', id='__NEXT_DATA__')
    if next_data:
        try:
            data = json.loads(next_data.string)
            for key, value in data['props']['pageProps']['apolloState'].items():
                if key.startswith('Book:') and isinstance(value, dict):
                    if value.get('description'):
                        return value['description']
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
    return None

def extract_book_cover_url(soup):
    """Extract the book cover image URL from a book page"""
    # Try class ResponsiveImage first
    img = soup.find('img', {'class': 'ResponsiveImage'})
    if img and 'src' in img.attrs:
        return img['src']
        
    # Try schema.org metadata as fallback
    schema_script = soup.find('script', {'type': 'application/ld+json'})
    if schema_script:
        try:
            data = json.loads(schema_script.string)
            if 'image' in data:
                return data['image']
        except json.JSONDecodeError:
            pass
            
    return None

def get_book_url(book_id):
    return f"https://www.goodreads.com/book/show/{book_id}"

def scrape_book(book_id):
    # Initialize downloader
    downloader = GoodreadsDownloader()
    
    # Get book URL
    url = get_book_url(book_id)
    
    # Download the HTML content
    success = downloader.download_url(url)
    if not success:
        return None
        
    # Construct the path where the file was saved
    local_path = Path('data/exported_html') / 'book' / 'show' / f"{book_id}.html"
    
    try:
        # Read the downloaded HTML
        with open(local_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Parse and extract information
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract all info using existing functions
        book_info = {
            'id': book_id,
            'title': extract_title(soup),
            'authors': extract_authors(soup),
            'genres': extract_genres(soup),
            'publication': extract_publication_info(soup),
            'details': extract_book_details(soup),
            'description': extract_description(soup),
            'similar_books_id': extract_work_id(soup)
        }
        
        # Add series information
        main_series_id = book_info['title']['series'].get('id') if book_info['title']['series'] else None
        book_info['additional_series'] = extract_additional_series(soup, main_series_id)        
        
        cover_url = extract_book_cover_url(soup)
        if cover_url:
            local_path = download_book_cover(book_id, cover_url)
            if local_path:
                book_info['image_url'] = local_path
        
        return book_info
        
    except Exception as e:
        print(f"Error processing book ID {book_id}: {str(e)}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python -m backend.scrapers.book <book_id>")
        sys.exit(1)
        
    book_id = sys.argv[1]
    scrape_book(book_id)  # Just scrape, no printing