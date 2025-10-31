"""Seed initial stock list from Polygon.io."""

from database.connection import get_db_context
from data_fetch.stock_list import StockListManager

if __name__ == '__main__':
    print("Seeding stocks from Polygon.io...")
    print("This may take a while due to rate limiting (5 calls/min)...")
    
    with get_db_context() as db:
        stock_manager = StockListManager(db)
        count = stock_manager.fetch_all_stocks()
        
        print(f"\nSuccessfully seeded {count} stocks!")

