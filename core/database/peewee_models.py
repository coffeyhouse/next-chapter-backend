# core/database/peewee_models.py
from peewee import *
from datetime import datetime

db = SqliteDatabase('books.db')

class BaseModel(Model):
    # Add common fields that appear in all/most tables
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db

# Main Entities
class Book(BaseModel):
    goodreads_id = CharField(primary_key=True)
    work_id = CharField(unique=True)
    title = CharField()
    published_date = DateTimeField(null=True)
    published_state = CharField(null=True)
    language = CharField(null=True)
    calibre_id = IntegerField(null=True)
    pages = IntegerField(null=True)
    isbn = CharField(null=True)
    goodreads_rating = FloatField(null=True)
    goodreads_votes = IntegerField(null=True)
    description = TextField(null=True)
    image_url = CharField(null=True)
    source = CharField(null=True)
    hidden = BooleanField(default=False)
    last_synced_at = DateTimeField(null=True)

    class Meta:
        table_name = 'book'

class Author(BaseModel):
    goodreads_id = CharField(primary_key=True)
    name = CharField()
    bio = TextField(null=True)
    image_url = CharField(null=True)
    last_synced_at = DateTimeField(null=True)

    class Meta:
        table_name = 'author'

class Series(BaseModel):
    goodreads_id = CharField(primary_key=True)
    title = CharField()
    last_synced_at = DateTimeField(null=True)

    class Meta:
        table_name = 'series'

class Genre(BaseModel):
    id = AutoField()
    name = CharField(unique=True)

    class Meta:
        table_name = 'genre'

# Relationship Models
class BookAuthor(BaseModel):
    work_id = ForeignKeyField(Book, field='work_id')
    author_id = ForeignKeyField(Author, field='goodreads_id')
    role = CharField(null=True)

    class Meta:
        table_name = 'book_author'
        primary_key = CompositeKey('work_id', 'author_id')

class BookSeries(BaseModel):
    work_id = ForeignKeyField(Book, field='work_id')
    series_id = ForeignKeyField(Series, field='goodreads_id')
    series_order = FloatField(null=True)

    class Meta:
        table_name = 'book_series'
        primary_key = CompositeKey('work_id', 'series_id')

class BookGenre(BaseModel):
    work_id = ForeignKeyField(Book, field='work_id')
    genre_id = ForeignKeyField(Genre, field='id')

    class Meta:
        table_name = 'book_genre'
        primary_key = CompositeKey('work_id', 'genre_id')