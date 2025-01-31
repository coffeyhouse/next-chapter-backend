# backend/db/operations/base.py
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BaseDBOperations:
    def __init__(self, db_path: str):
        """Initialize database operations with path to SQLite database"""
        self.db_path = db_path
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with foreign keys enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
        
    def upsert(self, table: str, data: Dict[str, Any], key_field: str) -> bool:
        """Insert or update a record"""
        try:
            clean_data = {k: v for k, v in data.items() if v is not None}
            
            fields = list(clean_data.keys())
            placeholders = ','.join(['?'] * len(fields))
            update_set = ','.join([
                f"{f}=excluded.{f}" 
                for f in fields 
                if f != key_field
            ])
            
            sql = f"""
                INSERT INTO {table} ({','.join(fields)})
                VALUES ({placeholders})
                ON CONFLICT({key_field}) 
                DO UPDATE SET {update_set}
                WHERE {table}.{key_field} = excluded.{key_field}
            """
            
            with self._get_connection() as conn:
                conn.execute(sql, list(clean_data.values()))
                return True
                
        except Exception as e:
            logger.error(f"Error upserting to {table}: {str(e)}")
            return False
            
    def batch_upsert(self, table: str, records: List[Dict[str, Any]], key_field: str) -> bool:
        """Batch upsert multiple records"""
        if not records:
            return True
            
        try:
            fields = set()
            clean_records = []
            
            for record in records:
                clean_record = {k: v for k, v in record.items() if v is not None}
                fields.update(clean_record.keys())
                clean_records.append(clean_record)
                
            fields = list(fields)
            placeholders = ','.join(['?'] * len(fields))
            update_set = ','.join([
                f"{f}=excluded.{f}" 
                for f in fields 
                if f != key_field
            ])
            
            sql = f"""
                INSERT INTO {table} ({','.join(fields)})
                VALUES ({placeholders})
                ON CONFLICT({key_field}) 
                DO UPDATE SET {update_set}
                WHERE {table}.{key_field} = excluded.{key_field}
            """
            
            with self._get_connection() as conn:
                for record in clean_records:
                    values = [record.get(field) for field in fields]
                    conn.execute(sql, values)
                return True
                
        except Exception as e:
            logger.error(f"Error batch upserting to {table}: {str(e)}")
            return False

    def get_by_id(self, table: str, item_id: str, id_field: str = 'id') -> Optional[Dict[str, Any]]:
        """Get a single record by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    f"SELECT * FROM {table} WHERE {id_field} = ?",
                    (item_id,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(zip([col[0] for col in cursor.description], row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting {table} by ID: {str(e)}")
            return None

    def get_all(
        self, 
        table: str, 
        conditions: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get multiple records with optional conditions"""
        try:
            sql = f"SELECT * FROM {table}"
            params = []
            
            if conditions:
                where_clauses = []
                for field, value in conditions.items():
                    if value is None:
                        where_clauses.append(f"{field} IS NULL")
                    else:
                        where_clauses.append(f"{field} = ?")
                        params.append(value)
                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)
                
            if order_by:
                sql += f" ORDER BY {order_by}"
                
            if limit:
                sql += f" LIMIT {limit}"
                
            with self._get_connection() as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                return [
                    dict(zip([col[0] for col in cursor.description], row))
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting records from {table}: {str(e)}")
            return []
    
    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a custom query and return results as dictionaries"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                return [
                    dict(zip([col[0] for col in cursor.description], row))
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return []