import logging
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.stock import Stock
from app.services.data_fetcher import DataFetcher
from app.services.metrics_calculator import MetricsCalculator
from app.services.valuation_engine import ValuationEngine

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def refresh_stock_list(self):
    """Refresh the list of stocks with market cap > $1B."""
    logger.info("Starting stock list refresh")

    db = SessionLocal()
    try:
        fetcher = DataFetcher(db)
        count = fetcher.refresh_all_stocks()
        logger.info(f"Refreshed {count} stocks")
        return {"status": "success", "stocks_refreshed": count}
    except Exception as e:
        logger.error(f"Error refreshing stock list: {e}")
        self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def refresh_single_stock(self, ticker: str):
    """Refresh data for a single stock."""
    logger.info(f"Refreshing data for {ticker}")

    db = SessionLocal()
    try:
        fetcher = DataFetcher(db)
        stock = fetcher.refresh_stock_data(ticker)

        if stock:
            # Calculate metrics
            calculator = MetricsCalculator(db)
            calculator.calculate_all_metrics(stock.id)

            # Update valuation
            engine = ValuationEngine(db)
            engine.calculate_dcf(ticker)

            return {"status": "success", "ticker": ticker}
        else:
            return {"status": "failed", "ticker": ticker, "reason": "Could not fetch data"}
    except Exception as e:
        logger.error(f"Error refreshing {ticker}: {e}")
        self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True)
def update_all_prices(self):
    """Update prices for all active stocks."""
    logger.info("Starting price update for all stocks")

    db = SessionLocal()
    try:
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        fetcher = DataFetcher(db)

        updated = 0
        failed = 0

        for stock in stocks:
            try:
                history = fetcher.fetch_price_history(stock.ticker, period="5d")
                if not history.empty:
                    fetcher.save_daily_prices(stock.id, history)
                    updated += 1
            except Exception as e:
                logger.warning(f"Failed to update prices for {stock.ticker}: {e}")
                failed += 1

        logger.info(f"Updated prices for {updated} stocks, {failed} failed")
        return {"status": "success", "updated": updated, "failed": failed}
    finally:
        db.close()


@celery_app.task(bind=True)
def update_all_financials(self):
    """Update financial statements for all active stocks."""
    logger.info("Starting financial statements update")

    db = SessionLocal()
    try:
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        fetcher = DataFetcher(db)

        updated = 0
        failed = 0

        for stock in stocks:
            try:
                statements = fetcher.fetch_financial_statements(stock.ticker)
                if statements:
                    parsed = fetcher.parse_financial_statements(stock.ticker, statements)
                    for data in parsed:
                        period_type = data.pop('period_type')
                        fetcher.save_financial_statement(stock.id, period_type, data)
                    updated += 1
            except Exception as e:
                logger.warning(f"Failed to update financials for {stock.ticker}: {e}")
                failed += 1

        logger.info(f"Updated financials for {updated} stocks, {failed} failed")
        return {"status": "success", "updated": updated, "failed": failed}
    finally:
        db.close()


@celery_app.task(bind=True)
def recalculate_all_metrics(self):
    """Recalculate metrics for all stocks."""
    logger.info("Starting metrics recalculation")

    db = SessionLocal()
    try:
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        calculator = MetricsCalculator(db)

        calculated = 0
        failed = 0

        for stock in stocks:
            try:
                calculator.calculate_all_metrics(stock.id)
                calculated += 1
            except Exception as e:
                logger.warning(f"Failed to calculate metrics for {stock.ticker}: {e}")
                failed += 1

        logger.info(f"Calculated metrics for {calculated} stocks, {failed} failed")
        return {"status": "success", "calculated": calculated, "failed": failed}
    finally:
        db.close()


@celery_app.task(bind=True)
def update_all_valuations(self):
    """Update DCF valuations for all stocks."""
    logger.info("Starting valuation updates")

    db = SessionLocal()
    try:
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        engine = ValuationEngine(db)

        updated = 0
        skipped = 0

        for stock in stocks:
            try:
                result = engine.calculate_dcf(stock.ticker)
                if result:
                    updated += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.warning(f"Failed to calculate valuation for {stock.ticker}: {e}")
                skipped += 1

        logger.info(f"Updated valuations for {updated} stocks, {skipped} skipped")
        return {"status": "success", "updated": updated, "skipped": skipped}
    finally:
        db.close()


@celery_app.task
def health_check():
    """Simple health check task."""
    return {"status": "healthy"}
