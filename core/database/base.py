# core/database/base.py
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BaseDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with foreign keys enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
        
    def upsert(self, table: str, data: Dict[str, Any], key_field: str) -> tuple[bool, bool]:
        """
        Insert or update record
        
        Args:
            table: Table name
            data: Dictionary of field names and values
            key_field: Primary key field name
            
        Returns:
            tuple[bool, bool]: (success, was_updated)
        """
        try:
            now = datetime.now().isoformat()
            
            # Clean data (handle empty values)
            clean_data = {}
            for k, v in data.items():
                if v == "":  # Empty string
                    clean_data[k] = None
                elif isinstance(v, (list, dict)) and not v:  # Empty list/dict
                    clean_data[k] = None
                else:
                    clean_data[k] = v
            
            # Check if record exists
            with self._get_connection() as conn:
                cursor = conn.execute(
                    f"SELECT * FROM {table} WHERE {key_field} = ?",
                    (clean_data[key_field],)
                )
                existing = cursor.fetchone()
            
            if existing:
                # Preserve created_at for existing record
                cursor = conn.execute(
                    f"SELECT created_at FROM {table} WHERE {key_field} = ?",
                    (clean_data[key_field],)
                )
                result = cursor.fetchone()
                if result:
                    clean_data['created_at'] = result[0]
            else:
                # Set created_at for new record
                if 'created_at' not in clean_data:
                    clean_data['created_at'] = now
                    
            # Always update updated_at
            clean_data['updated_at'] = now
            
            # Prepare SQL
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
            
            # Execute upsert
            with self._get_connection() as conn:
                conn.execute(sql, list(clean_data.values()))
                return True, existing is not None
                
        except Exception as e:
            logger.error(f"Error upserting to {table}: {str(e)}")
            return False, False
            
    def get_by_id(self, table: str, id_value: Any, id_field: str = 'id') -> Optional[Dict[str, Any]]:
        """Get single record by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    f"SELECT * FROM {table} WHERE {id_field} = ?",
                    (id_value,)
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
        """Get multiple records with optional filtering"""
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
                return [
                    dict(zip([col[0] for col in cursor.description], row))
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Error getting records from {table}: {str(e)}")
            return []
            
    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute custom query"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(sql, params)
                return [
                    dict(zip([col[0] for col in cursor.description], row))
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return []