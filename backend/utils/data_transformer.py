from datetime import datetime
from typing import Dict, List, Any

def transform_book_data(book_info: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Transform scraped book data into database table format"""
    now = datetime.now().isoformat()
    
    tables = {
        'book': [{
            'goodreads_id': book_info['id'],
            'title': book_info['title']['title'],
            'published_date': book_info['publication']['date'],
            'published_state': book_info['publication']['status'],
            'language': book_info['details']['language'],
            'calibre_id': None,  # To be filled later
            'pages': book_info['details']['pages'],
            'isbn': book_info['details']['isbn'],
            'goodreads_rating': book_info['details']['rating'],
            'goodreads_votes': book_info['details']['rating_count'],
            'description': book_info['description'],
            'image_url': None,  # Not currently scraped
            'similar_books_id': book_info.get('similar_books_id'),
            'hidden': False,
            'created_at': now,
            'updated_at': now,
            'last_synced_at': now
        }],
        
        'series': [],
        'book_series': [],
        'author': [],
        'author_book': [],
        'genre': [],
        'book_genre': [],
        'award': [],
        'book_award': [],
        'similar_book': [],
        'book_editions': []
    }
    
    # Process series data
    if book_info['title']['series'].get('name'):
        main_series = {
            'goodreads_id': book_info['title']['series']['id'],
            'title': book_info['title']['series']['name'],
            'created_at': now,
            'updated_at': now,
            'last_synced_at': None
        }
        tables['series'].append(main_series)
        
        # Add book_series relationship
        tables['book_series'].append({
            'book_id': book_info['id'],
            'series_id': book_info['title']['series']['id'],
            'series_order': book_info['title']['series'].get('number'),
            'created_at': now,
            'updated_at': now
        })
    
    # Process additional series
    for series in book_info.get('additional_series', []):
        tables['series'].append({
            'goodreads_id': series['id'],
            'title': series['name'],
            'created_at': now,
            'updated_at': now,
            'last_synced_at': None
        })
        tables['book_series'].append({
            'book_id': book_info['id'],
            'series_id': series['id'],
            'series_order': None,  # Additional series don't typically have order
            'created_at': now,
            'updated_at': now
        })
    
    # Process authors
    for author in book_info['authors']:
        tables['author'].append({
            'goodreads_id': author['id'],
            'name': author['name'],
            'bio': None,  # Would need separate author scrape
            'image_url': None,  # Would need separate author scrape
            'created_at': now,
            'updated_at': now,
            'last_synced_at': None
        })
        tables['author_book'].append({
            'book_id': book_info['id'],
            'author_id': author['id'],
            'role': author['role'],
            'created_at': now,
            'updated_at': now
        })
    
    # Process genres
    for i, genre in enumerate(book_info['genres'], 1):
        tables['genre'].append({
            'id': i,  # Temporary ID for display
            'name': genre['name'],
            'created_at': now,
            'updated_at': now
        })
        tables['book_genre'].append({
            'genre_id': i,
            'book_id': book_info['id'],
            'created_at': now,
            'updated_at': now
        })
    
    # Process awards
    for award in book_info['details']['awards']:
        tables['award'].append({
            'goodreads_id': award['id'],
            'name': award['name'],
            'created_at': now,
            'updated_at': now
        })
        tables['book_award'].append({
            'book_id': book_info['id'],
            'award_id': award['id'],
            'category': award['category'],
            'year': award['year'],
            'designation': award['designation'],
            'created_at': now,
            'updated_at': now
        })
    
    return tables

def format_tables(tables: Dict[str, List[Dict]]) -> str:
    """Format the tables data for display"""
    output = []
    
    for table_name, records in tables.items():
        if records:  # Only show tables with data
            output.append(f"\n=== {table_name} ===")
            for record in records:
                output.append("-" * 40)
                for field, value in record.items():
                    output.append(f"{field:<20} {value}")
    
    return "\n".join(output)