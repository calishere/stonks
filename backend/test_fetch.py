import time
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.data_fetcher import DataFetcher

# Setup database connection
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

fetcher = DataFetcher(db)

# Test with just 1 stock first
print("Testing Finnhub API for AAPL...")
print(f"API Key configured: {'Yes' if settings.finnhub_api_key and settings.finnhub_api_key != 'your_api_key_here' else 'No - get free key at https://finnhub.io'}")

result = fetcher.refresh_stock_data('AAPL')
print(f"AAPL loaded: {result is not None}")

if result:
    print(f"  Name: {result.name}")
    print(f"  Market Cap: ${result.market_cap:,.0f}")
    print(f"  Sector: {result.sector}")

db.close()
