#!/usr/bin/env python3
"""
Apply SQL migration to the database.
Usage: python scripts/apply_migration.py database/migrations/001_add_job_status.sql
"""
import sys
import sqlite3
from pathlib import Path

def apply_migration(db_path: str, migration_path: str):
    """Apply a SQL migration file to the database."""
    migration_file = Path(migration_path)
    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_path}")
        sys.exit(1)
    
    sql = migration_file.read_text()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Execute each statement
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        conn.commit()
        print(f"✓ Migration applied successfully: {migration_file.name}")
    except sqlite3.OperationalError as e:
        # If error is about column already exists, that's okay
        if "duplicate column name" in str(e).lower():
            print(f"✓ Migration already applied: {migration_file.name}")
        else:
            print(f"✗ Error applying migration: {e}")
            conn.rollback()
            sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python apply_migration.py <migration_file>")
        sys.exit(1)
    
    db_path = "database/life.db"
    migration_path = sys.argv[1]
    apply_migration(db_path, migration_path)
