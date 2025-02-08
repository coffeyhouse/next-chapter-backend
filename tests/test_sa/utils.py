# tests/test_sa/utils.py
from typing import List, Dict, Any, Optional
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

class DBInspector:
    def __init__(self, session: Session):
        self.session = session
        self.engine = session.get_bind()
        self.inspector = inspect(self.engine)

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific table"""
        columns = self.inspector.get_columns(table_name)
        pk = self.inspector.get_pk_constraint(table_name)
        fks = self.inspector.get_foreign_keys(table_name)
        indexes = self.inspector.get_indexes(table_name)

        return {
            'columns': columns,
            'primary_key': pk,
            'foreign_keys': fks,
            'indexes': indexes
        }

    def get_all_tables(self) -> List[str]:
        """Get list of all tables in database"""
        return self.inspector.get_table_names()

    def count_rows(self, table_name: str) -> int:
        """Get row count for a table"""
        result = self.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()

    def get_schema_sql(self, table_name: str) -> str:
        """Get CREATE TABLE SQL for a table"""
        result = self.session.execute(
            text(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"),
            {'name': table_name}
        )
        return result.scalar() or ''

    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample rows from a table"""
        result = self.session.execute(
            text(f"SELECT * FROM {table_name} LIMIT :limit"),
            {'limit': limit}
        )
        return [dict(row) for row in result]

    def describe_table(self, table_name: str) -> str:
        """Get a human-readable description of a table"""
        info = self.get_table_info(table_name)
        
        description = [f"\nTable: {table_name}"]
        description.append("\nColumns:")
        for col in info['columns']:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f"DEFAULT {col['default']}" if col['default'] is not None else ""
            description.append(f"  - {col['name']}: {col['type']} {nullable} {default}")

        if info['primary_key']['constrained_columns']:
            description.append("\nPrimary Key:")
            description.append(f"  {', '.join(info['primary_key']['constrained_columns'])}")

        if info['foreign_keys']:
            description.append("\nForeign Keys:")
            for fk in info['foreign_keys']:
                description.append(
                    f"  - {', '.join(fk['constrained_columns'])} -> "
                    f"{fk['referred_table']}({', '.join(fk['referred_columns'])})"
                )

        if info['indexes']:
            description.append("\nIndexes:")
            for idx in info['indexes']:
                unique = "UNIQUE " if idx['unique'] else ""
                description.append(
                    f"  - {unique}INDEX {idx['name']} ON ({', '.join(idx['column_names'])})"
                )

        row_count = self.count_rows(table_name)
        description.append(f"\nRow Count: {row_count}")

        return "\n".join(description)

def print_table_schema(session: Session, table_name: str):
    """Print detailed schema information for a table"""
    inspector = DBInspector(session)
    print(inspector.describe_table(table_name))
    
def print_sample_data(session: Session, table_name: str, limit: int = 5):
    """Print sample rows from a table"""
    inspector = DBInspector(session)
    samples = inspector.get_sample_data(table_name, limit)
    print(f"\nSample data from {table_name} (showing {len(samples)} rows):")
    for row in samples:
        print(row)

def compare_model_to_db(session: Session, model_class) -> List[str]:
    """Compare SQLAlchemy model to actual database table"""
    differences = []
    inspector = DBInspector(session)
    table_name = model_class.__tablename__
    db_info = inspector.get_table_info(table_name)
    
    # Get model columns
    mapper = inspect(model_class)
    model_columns = {c.key: c for c in mapper.columns}
    
    # Compare columns
    db_columns = {c['name']: c for c in db_info['columns']}
    
    # Check for columns in model but not in db
    for col_name in model_columns:
        if col_name not in db_columns:
            differences.append(f"Column '{col_name}' exists in model but not in database")
            
    # Check for columns in db but not in model
    for col_name in db_columns:
        if col_name not in model_columns:
            differences.append(f"Column '{col_name}' exists in database but not in model")
            
    return differences