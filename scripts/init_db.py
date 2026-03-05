#!/usr/bin/env python3
"""
Initialize the database with the base schema.
"""
import sqlite3
from pathlib import Path

def init_db():
    """Initialize database with base schema."""
    db_path = "database/life.db"
    schema_path = "database/schema.sql"
    
    schema_file = Path(schema_path)
    if not schema_file.exists():
        print(f"Error: Schema file not found: {schema_path}")
        return
    
    sql = schema_file.read_text()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.executescript(sql)
        conn.commit()
        print(f"✓ Database initialized: {db_path}")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
