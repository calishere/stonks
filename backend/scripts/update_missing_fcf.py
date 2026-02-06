#!/usr/bin/env python3
"""
Script to update stocks missing FCF data using Alpha Vantage.
Alpha Vantage free tier: 5 calls/minute, 500 calls/day.
"""
import sys
import os
import time
import logging

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.data_fetcher import DataFetcher, ALPHA_VANTAGE_DELAY
from app.models.stock import Stock
from app.models.financial import FinancialStatement
from app.services.metrics_calculator import MetricsCalculator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_stocks_missing_fcf(session) -> list:
    """Find all stocks that don't have FCF data in their financial statements."""
    # Get all active stocks
    stocks = session.query(Stock).filter(Stock.is_active == True).all()

    missing_fcf = []
    for stock in stocks:
        # Check if stock has any financial statement with FCF
        has_fcf = session.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock.id,
            FinancialStatement.free_cash_flow.isnot(None),
            FinancialStatement.free_cash_flow != 0
        ).first()

        if not has_fcf:
            missing_fcf.append(stock)

    return missing_fcf


def update_stock_from_alpha_vantage(session, fetcher: DataFetcher, stock: Stock) -> bool:
    """Update a single stock with Alpha Vantage data."""
    ticker = stock.ticker
    logger.info(f"Fetching Alpha Vantage data for {ticker}...")

    try:
        # Fetch cash flow (required)
        cash_flow = fetcher.fetch_alpha_vantage_cash_flow(ticker)
        if not cash_flow:
            logger.warning(f"No cash flow data from Alpha Vantage for {ticker}")
            return False

        time.sleep(ALPHA_VANTAGE_DELAY)

        # Fetch income statement
        income = fetcher.fetch_alpha_vantage_income(ticker)
        time.sleep(ALPHA_VANTAGE_DELAY)

        # Fetch balance sheet
        balance = fetcher.fetch_alpha_vantage_balance(ticker)
        time.sleep(ALPHA_VANTAGE_DELAY)

        # Parse and save
        parsed = fetcher.parse_alpha_vantage_financials(ticker, cash_flow, income, balance)
        if not parsed:
            logger.warning(f"Could not parse Alpha Vantage data for {ticker}")
            return False

        # Delete old statements without FCF data for this stock
        session.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock.id,
            (FinancialStatement.free_cash_flow.is_(None)) | (FinancialStatement.free_cash_flow == 0)
        ).delete()
        session.commit()

        # Save new statements
        for period_type, data in parsed:
            fetcher.save_financial_statement(stock.id, period_type, data)

        logger.info(f"Saved {len(parsed)} statements for {ticker}")
        return True

    except Exception as e:
        logger.error(f"Error updating {ticker}: {e}")
        return False


def main():
    # Create database session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Find stocks missing FCF
        missing = get_stocks_missing_fcf(session)
        logger.info(f"Found {len(missing)} stocks missing FCF data")

        if not missing:
            logger.info("All stocks have FCF data!")
            return

        # Print list of stocks
        logger.info("Stocks missing FCF: " + ", ".join([s.ticker for s in missing]))

        # Create data fetcher
        fetcher = DataFetcher(session)

        # Update each stock
        updated = 0
        failed = []

        for i, stock in enumerate(missing):
            logger.info(f"\n[{i+1}/{len(missing)}] Processing {stock.ticker}...")

            if update_stock_from_alpha_vantage(session, fetcher, stock):
                updated += 1
            else:
                failed.append(stock.ticker)

            # Extra delay between stocks to be safe
            if i < len(missing) - 1:
                logger.info("Waiting before next stock...")
                time.sleep(5)

        logger.info(f"\n=== Summary ===")
        logger.info(f"Updated: {updated}/{len(missing)} stocks")
        if failed:
            logger.info(f"Failed: {', '.join(failed)}")

        # Recalculate metrics for updated stocks
        if updated > 0:
            logger.info("\nRecalculating metrics for updated stocks...")
            calculator = MetricsCalculator(session)

            for stock in missing:
                if stock.ticker not in failed:
                    try:
                        calculator.calculate_all_metrics(stock.id)
                        logger.info(f"Recalculated metrics for {stock.ticker}")
                    except Exception as e:
                        logger.error(f"Error calculating metrics for {stock.ticker}: {e}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
