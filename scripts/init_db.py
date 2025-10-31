"""Initialize database with schema."""

from database.connection import get_db_engine, init_db

if __name__ == '__main__':
    print("Initializing database...")
    
    try:
        init_db()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise

