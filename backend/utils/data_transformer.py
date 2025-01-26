from datetime import datetime
from typing import Dict, List, Any, Optional

# Define default table schemas
DEFAULT_BOOK = {
    'goodreads_id': None,
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
    
    # Initialize tables with empty lists
    tables = {
        'book': [],
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
        'library': [],
        'user': [],
        'book_user': []
    }
    
    # Handle simplified library source data
    if 'source' in book_info and book_info['source'] == 'library':
        tables['book'].append(create_record(
            DEFAULT_BOOK,
            {
                'goodreads_id': book_info['id'],
                'title': book_info['title'],
                'calibre_id': book_info['calibre_id'],
                'source': book_info['source'],
                'last_synced_at': None
            },
            now
        ))
        return tables
    
    # Process book data
    tables['book'].append(create_record(
        DEFAULT_BOOK,
        {
            'goodreads_id': book_info['id'],
            'title': book_info['title']['title'],
            'published_date': book_info['publication']['date'],
            'published_state': book_info['publication']['status'],
            'language': book_info['details']['language'],
            'pages': book_info['details']['pages'],
            'isbn': book_info['details']['isbn'],
            'goodreads_rating': book_info['details']['rating'],
            'goodreads_votes': book_info['details']['rating_count'],
            'description': book_info['description'],
            'image_url': book_info['image_url'],
            'similar_books_id': book_info.get('similar_books_id'),
            'hidden': book_info['details']['language'] is None or book_info['details']['language'].lower() != 'english',
            'last_synced_at': now
        },
        now
    ))
    
    # Add user records if they don't exist
    warren_user = create_record(
        DEFAULT_USER,
        {
            'id': 1,
            'name': 'Warren'
        },
        now
    )
    
    ruth_user = create_record(
        DEFAULT_USER,
        {
            'id': 2,
            'name': 'Ruth'
        },
        now
    )
    tables['user'].extend([warren_user, ruth_user])
    
    # Add book_user records if read dates exist
    if book_info.get('warren_last_read'):
        tables['book_user'].append(create_record(
            DEFAULT_BOOK_USER,
            {
                'book_id': book_info['id'],
                'user_id': 1,  # Warren's ID
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
                'user_id': 2,  # Ruth's ID
                'status': 'read',
                'source': 'calibre',
                'finished_at': book_info['ruth_last_read']
            },
            now
        ))

    
    # Process main series
    if book_info['title']['series'].get('name'):
        tables['series'].append(create_record(
            DEFAULT_SERIES,
            {
                'goodreads_id': book_info['title']['series']['id'],
                'title': book_info['title']['series']['name']
            },
            now
        ))
        
        tables['book_series'].append(create_record(
            DEFAULT_BOOK_SERIES,
            {
                'book_id': book_info['id'],
                'series_id': book_info['title']['series']['id'],
                'series_order': book_info['title']['series'].get('number')
            },
            now
        ))
    
    # Process additional series
    for series in book_info.get('additional_series', []):
        tables['series'].append(create_record(
            DEFAULT_SERIES,
            {
                'goodreads_id': series['id'],
                'title': series['name']
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
    for author in book_info['authors']:
        tables['author'].append(create_record(
            DEFAULT_AUTHOR,
            {
                'goodreads_id': author['id'],
                'name': author['name']
            },
            now
        ))
        
        tables['author_book'].append(create_record(
            DEFAULT_AUTHOR_BOOK,
            {
                'book_id': book_info['id'],
                'author_id': author['id'],
                'role': author['role']
            },
            now
        ))
    
    # Process genres
    for i, genre in enumerate(book_info['genres'], 1):
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
    for award in book_info['details']['awards']:
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
                'category': award['category'],
                'year': award['year'],
                'designation': award['designation']
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