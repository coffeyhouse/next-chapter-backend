# core/database/peewee_models.py
from peewee import *
from datetime import datetime

db = SqliteDatabase('books.db')  # Same database as your current system

class BaseModel(Model):
    class Meta:
        database = db

class Book(BaseModel):
    # Match your existing schema
    goodreads_id = CharField(primary_key=True)
    work_id = CharField(unique=True)
    title = CharField()
    published_date = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'book'  # Use your existing table name