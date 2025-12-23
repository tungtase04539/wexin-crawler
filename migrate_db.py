"""
Simple migration script to add new columns to SQLite
"""
import sqlite3
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    db_path = settings.data_dir / "articles.db"
    
    if not db_path.exists():
        logger.info("Database file not found, nothing to migrate (will be created fresh).")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # List of new columns to add to 'articles' table
    # format: (column_name, column_type)
    new_columns = [
        ("read_count", "INTEGER DEFAULT 0"),
        ("like_count", "INTEGER DEFAULT 0"),
        ("comment_count", "INTEGER DEFAULT 0"),
        ("share_count", "INTEGER DEFAULT 0"),
        ("engagement_rate", "FLOAT"),
        ("metrics_updated_at", "DATETIME"),
        ("videos", "JSON"),
        ("wow_count", "INTEGER DEFAULT 0"),
        ("favorite_count", "INTEGER DEFAULT 0"),
        ("virality_index", "FLOAT DEFAULT 0.0"),
        ("content_value_index", "FLOAT DEFAULT 0.0"),
        ("heat_score", "FLOAT DEFAULT 0.0"),
        ("is_simulated", "BOOLEAN DEFAULT 0"),
        ("ai_summary", "TEXT")
    ]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
            logger.info(f"Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info(f"Column already exists: {col_name}")
            else:
                logger.error(f"Failed to add column {col_name}: {e}")
                
    conn.commit()
    conn.close()
    logger.info("Migration check completed.")

if __name__ == "__main__":
    migrate()
