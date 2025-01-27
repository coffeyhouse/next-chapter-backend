from datetime import datetime
from typing import Dict, List, Any, Optional
from dateutil import parser as date_parser

def format_pub_date(date_str: Optional[str]) -> Optional[str]:
    """Convert publication date to ISO format"""
    if not date_str:
        return None
        
    try:
        # Parse the date string
        dt = date_parser.parse(date_str)
        # Add time component if only date is present
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
        # Return ISO format
        return dt.isoformat()
    except (ValueError, TypeError):
        return None

# Define default table schemas
DEFAULT_BOOK = {
    'goodreads_id': None,  # This will be the raw ID from Calibre
    'title': None,
    'published_date': None,
    'published_state': None,
    'language': None,
    'calibre_id': None,
    'pages': None,
    'isbn': None,
    'goodreads_rating': None,
    'goodreads_votes': None,
    'description': None,
    'image_url': None,
    'similar_books_id': None,
    'source': None,
    'hidden': False,
    'created_at': None,
    'updated_at': None,
    'last_synced_at': None
}

DEFAULT_LIBRARY = {
    'title': None,
    'calibre_id': None,
    'goodreads_id': None,
    'isbn': None,
    'created_at': None,
    'updated_at': None,
    'last_synced_at': None
}

DEFAULT_SERIES = {
    'goodreads_id': None,
    'title': None,
    'created_at': None,
    'updated_at': None,
    'last_synced_at': None
}

DEFAULT_BOOK_SERIES = {
    'book_id': None,
    'series_id': None,
    'series_order': None,
    'created_at': None,
    'updated_at': None
}

DEFAULT_AUTHOR = {
    'goodreads_id': None,
    'name': None,
    'bio': None,
    'image_url': None,
    'created_at': None,
    'updated_at': None,
    'last_synced_at': None
}

DEFAULT_AUTHOR_BOOK = {
    'book_id': None,
    'author_id': None,
    'role': None,
    'created_at': None,
    'updated_at': None
}

DEFAULT_GENRE = {
    'id': None,
    'name': None,
    'created_at': None,
    'updated_at': None
}

DEFAULT_BOOK_GENRE = {
    'genre_id': None,
    'book_id': None,
    'created_at': None,
    'updated_at': None
}

DEFAULT_AWARD = {
    'goodreads_id': None,
    'name': None,
    'created_at': None,
    'updated_at': None
}

DEFAULT_BOOK_AWARD = {
    'book_id': None,
    'award_id': None,
    'category': None,
    'year': None,
    'designation': None,
    'created_at': None,
    'updated_at': None
}

DEFAULT_BOOK_EDITIONS = {
    'book_id': None,
    'edition_id': None,
    'created_at': None,
    'updated_at': None
}

DEFAULT_SIMILAR_BOOK = {
    'book_id': None,
    'similar_book_id': None,
    'created_at': None,
    'updated_at': None
}

DEFAULT_USER = {
    'id': None,
    'name': None,
    'created_at': None,
    'updated_at': None
}

DEFAULT_BOOK_USER = {
    'book_id': None,
    'user_id': None,
    'status': None,
    'source': None,
    'started_at': None,
    'finished_at': None,
    'created_at': None,
    'updated_at': None
}

def create_record(default_schema: Dict[str, Any], data: Dict[str, Any], now: str) -> Dict[str, Any]:
    """Create a record by merging default schema with provided data"""
    record = default_schema.copy()
    record.update(data)
    
    # Update timestamps if not set
    for field in ['created_at', 'updated_at']:
        if record[field] is None:
            record[field] = now
            
    return record

def transform_book_data(book_info: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Transform book data into database table format"""
    now = datetime.now().isoformat()
    
    # Initialize tables
    tables = {
        'book': [],
        'library': [],
        'series': [],
        'book_series': [],
        'author': [],
        'author_book': [],
        'genre': [],
        'book_genre': [],
        'award': [],
        'book_award': [],
        'similar_book': [],
        'book_editions': [],
        'user': [],
        'book_user': []
    }
    
    # Extract title from title object if it's a dict
    title = book_info['title']['title'] if isinstance(book_info['title'], dict) else book_info['title']
    
    # Process book data
    book_record = {
        'goodreads_id': book_info.get('id'),
        'title': title,
        'calibre_id': book_info.get('calibre_id'),
        'source': book_info.get('source'),
        'last_synced_at': now if book_info['details'].get('rating') else None  # Set sync date only if we have scraped details
    }
    
    # Add additional fields if they exist
    if 'publication' in book_info:
        book_record.update({
            'published_date': format_pub_date(book_info['publication'].get('date')),
            'published_state': book_info['publication'].get('status')
        })
    
    if 'details' in book_info:
        book_record.update({
            'language': book_info['details'].get('language'),
            'pages': book_info['details'].get('pages'),
            'isbn': book_info['details'].get('isbn'),
            'goodreads_rating': book_info['details'].get('rating'),
            'goodreads_votes': book_info['details'].get('rating_count'),
            'hidden': book_info['details'].get('language') is None or 
                     book_info['details'].get('language', '').lower() != 'english'
        })
    
    if 'description' in book_info:
        book_record['description'] = book_info['description']
    
    if 'image_url' in book_info:
        book_record['image_url'] = book_info['image_url']
        
    if 'similar_books_id' in book_info:
        book_record['similar_books_id'] = book_info['similar_books_id']
    
    tables['book'].append(create_record(DEFAULT_BOOK, book_record, now))
    
    # Add library record if it's a library source
    if book_info.get('source') == 'library':
        tables['library'].append(create_record(
            DEFAULT_LIBRARY,
            {
                'title': title,
                'calibre_id': book_info.get('calibre_id'),
                'goodreads_id': book_info.get('id'),
                'isbn': book_info.get('isbn'),
                'last_synced_at': now
            },
            now
        ))
    
    # Process series information
    if isinstance(book_info['title'], dict) and book_info['title'].get('series'):
        series_info = book_info['title']['series']
        if series_info.get('id') and series_info.get('name'):
            tables['series'].append(create_record(
                DEFAULT_SERIES,
                {
                    'goodreads_id': series_info['id'],
                    'title': series_info['name'],
                    'last_synced_at': None
                },
                now
            ))
            
            tables['book_series'].append(create_record(
                DEFAULT_BOOK_SERIES,
                {
                    'book_id': book_info['id'],
                    'series_id': series_info['id'],
                    'series_order': series_info.get('number')
                },
                now
            ))
    
    # Process additional series
    for series in book_info.get('additional_series', []):
        if series.get('id') and series.get('name'):
            tables['series'].append(create_record(
                DEFAULT_SERIES,
                {
                    'goodreads_id': series['id'],
                    'title': series['name'],
                    'last_synced_at': None
                },
                now
            ))
            
            tables['book_series'].append(create_record(
                DEFAULT_BOOK_SERIES,
                {
                    'book_id': book_info['id'],
                    'series_id': series['id']
                },
                now
            ))
    
    # Process authors
    for author in book_info.get('authors', []):
        if author.get('id') and author.get('name'):
            tables['author'].append(create_record(
                DEFAULT_AUTHOR,
                {
                    'goodreads_id': author['id'],
                    'name': author['name'],
                    'last_synced_at': None
                },
                now
            ))
            
            tables['author_book'].append(create_record(
                DEFAULT_AUTHOR_BOOK,
                {
                    'book_id': book_info['id'],
                    'author_id': author['id'],
                    'role': author.get('role', 'Author')
                },
                now
            ))
    
    # Process genres
    if 'genres' in book_info:
        for i, genre in enumerate(book_info['genres'], 1):
            if genre.get('name'):
                tables['genre'].append(create_record(
                    DEFAULT_GENRE,
                    {
                        'id': i,
                        'name': genre['name']
                    },
                    now
                ))
                
                tables['book_genre'].append(create_record(
                    DEFAULT_BOOK_GENRE,
                    {
                        'genre_id': i,
                        'book_id': book_info['id']
                    },
                    now
                ))
    
    # Process awards
    if 'details' in book_info and 'awards' in book_info['details']:
        for award in book_info['details']['awards']:
            if award.get('id') and award.get('name'):
                tables['award'].append(create_record(
                    DEFAULT_AWARD,
                    {
                        'goodreads_id': award['id'],
                        'name': award['name']
                    },
                    now
                ))
                
                tables['book_award'].append(create_record(
                    DEFAULT_BOOK_AWARD,
                    {
                        'book_id': book_info['id'],
                        'award_id': award['id'],
                        'category': award.get('category'),
                        'year': award.get('year'),
                        'designation': award.get('designation')
                    },
                    now
                ))
    
    # Add default users if not present
    if not tables['user']:
        tables['user'].extend([
            create_record(DEFAULT_USER, {'id': 1, 'name': 'Warren'}, now),
            create_record(DEFAULT_USER, {'id': 2, 'name': 'Ruth'}, now)
        ])
    
    # Add reading records if they exist
    if book_info.get('warren_last_read'):
        tables['book_user'].append(create_record(
            DEFAULT_BOOK_USER,
            {
                'book_id': book_info['id'],
                'user_id': 1,
                'status': 'read',
                'source': 'calibre',
                'finished_at': book_info['warren_last_read']
            },
            now
        ))
    
    if book_info.get('ruth_last_read'):
        tables['book_user'].append(create_record(
            DEFAULT_BOOK_USER,
            {
                'book_id': book_info['id'],
                'user_id': 2,
                'status': 'read',
                'source': 'calibre',
                'finished_at': book_info['ruth_last_read']
            },
            now
        ))
    
    return tables

def transform_author_data(author_info: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Transform author data into database table format"""
    now = datetime.now().isoformat()
    
    # Initialize tables
    tables = {
        'author': [],
        'series': [],
        'author_series': []
    }
    
    # Process author data
    tables['author'].append(create_record(
        DEFAULT_AUTHOR,
        {
            'goodreads_id': author_info['id'],
            'name': author_info['name'],
            'bio': author_info['bio'],
            'image_url': author_info['image_url'],
            'last_synced_at': now
        },
        now
    ))
    
    # Process series if present
    for series in author_info.get('series', []):
        tables['series'].append(create_record(
            DEFAULT_SERIES,
            {
                'goodreads_id': series['id'],
                'title': series['name']
            },
            now
        ))
        
        # Add author_series relationship
        tables['author_series'].append({
            'author_id': author_info['id'],
            'series_id': series['id'],
            'created_at': now,
            'updated_at': now
        })
    
    return tables

def transform_author_books_data(author_books_info: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Transform author books data into database table format"""
    now = datetime.now().isoformat()
    
    # Initialize tables
    tables = {
        'author': [],
        'book': [],
        'author_book': []
    }
    
    # Process author data
    tables['author'].append(create_record(
        DEFAULT_AUTHOR,
        {
            'goodreads_id': author_books_info['author_id'],
            'name': author_books_info['author_name'],
            'last_synced_at': now
        },
        now
    ))
    
    # Process each book
    for book in author_books_info['books']:
        # Add book record
        tables['book'].append(create_record(
            DEFAULT_BOOK,
            {
                'goodreads_id': book['id'],
                'title': book['title'],
                'published_date': book.get('publication'),  # This might be in "Published: 2024" format
                'last_synced_at': now
            },
            now
        ))
        
        # Add author-book relationship
        tables['author_book'].append(create_record(
            DEFAULT_AUTHOR_BOOK,
            {
                'author_id': author_books_info['author_id'],
                'book_id': book['id'],
                'role': 'Author'  # Default role
            },
            now
        ))
    
    return tables

def transform_editions_data(editions_info):
    """Transform editions data into database table format"""
    now = datetime.now().isoformat()
    
    # Initialize tables
    tables = {
        'book': [],
        'book_editions': []
    }
    
    if editions_info:
        first_edition, all_editions = editions_info
        
        # Add the first edition as the main book if it exists
        if first_edition and first_edition.get('id'):
            tables['book'].append(create_record(
                DEFAULT_BOOK,
                {
                    'goodreads_id': first_edition['id'],
                    'title': first_edition['title'],
                    'source': 'editions'
                },
                now
            ))
        
            # Add all editions EXCEPT the first edition
            for edition in all_editions:
                # Skip if this is the main edition or if missing ID
                if edition['id'] and edition['id'] != first_edition['id']:
                    tables['book_editions'].append(create_record(
                        DEFAULT_BOOK_EDITIONS,
                        {
                            'book_id': first_edition['id'],
                            'edition_id': edition['id']
                        },
                        now
                    ))
    
    return tables

def transform_series_data(series_info):
    """Transform series data into database table format"""
    now = datetime.now().isoformat()
    
    # Initialize tables
    tables = {
        'series': [],
        'book': [],
        'book_series': []
    }
    
    if series_info:
        # Add series record
        tables['series'].append(create_record(
            DEFAULT_SERIES,
            {
                'goodreads_id': series_info['id'],
                'title': series_info['name'],
                'last_synced_at': now
            },
            now
        ))
        
        # Process books in the series
        for book in series_info.get('books', []):
            # Add book record
            tables['book'].append(create_record(
                DEFAULT_BOOK,
                {
                    'goodreads_id': book['id'],
                    'title': book['title'],
                    'source': 'series',
                    'last_synced_at': now
                },
                now
            ))
            
            # Add book-series relationship
            tables['book_series'].append(create_record(
                DEFAULT_BOOK_SERIES,
                {
                    'book_id': book['id'],
                    'series_id': series_info['id'],
                    'series_order': book.get('number')
                },
                now
            ))
    
    return tables

def transform_similar_data(similar_info):
    """Transform similar books data into database table format"""
    now = datetime.now().isoformat()
    
    # Initialize tables
    tables = {
        'book': [],
        'similar_book': []
    }
    
    if similar_info:
        main_book, similar_books = similar_info
        
        if main_book and main_book.get('id'):
            # Add main book
            tables['book'].append(create_record(
                DEFAULT_BOOK,
                {
                    'goodreads_id': main_book['id'],
                    'title': main_book['title'],
                    'source': 'similar',
                    'last_synced_at': now
                },
                now
            ))
            
            # Process similar books
            for book in similar_books:
                # Add similar book
                tables['book'].append(create_record(
                    DEFAULT_BOOK,
                    {
                        'goodreads_id': book['id'],
                        'title': book['title'],
                        'source': 'similar',
                        'last_synced_at': now
                    },
                    now
                ))
                
                # Add similar book relationship
                tables['similar_book'].append(create_record(
                    DEFAULT_SIMILAR_BOOK,
                    {
                        'book_id': main_book['id'],
                        'similar_book_id': book['id']
                    },
                    now
                ))
    
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
    
    # Add summary section
    output.append("\nSummary:")
    for table_name, records in tables.items():
        if records:
            output.append(f"{table_name}: {len(records)} records")
    
    return "\n".join(output)

def print_transformed_data(tables: Dict[str, List[Dict]]) -> None:
    """Print the transformed data with formatting"""
    print(format_tables(tables))