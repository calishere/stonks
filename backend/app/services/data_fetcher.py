import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging

from app.models.stock import Stock
from app.models.financial import FinancialStatement, DailyPrice
from app.core.config import settings

logger = logging.getLogger(__name__)


class DataFetcher:
    """Service for fetching financial data from external sources."""

    def __init__(self, db: Session):
        self.db = db
        self.min_market_cap = settings.min_market_cap

    def get_sp500_tickers(self) -> List[str]:
        """Fetch S&P 500 ticker list from Wikipedia."""
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url)
            sp500_table = tables[0]
            return sp500_table['Symbol'].str.replace('.', '-', regex=False).tolist()
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500 list: {e}")
            return []

    def get_nasdaq100_tickers(self) -> List[str]:
        """Fetch NASDAQ 100 ticker list."""
        try:
            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            tables = pd.read_html(url)
            # Find the table with ticker symbols
            for table in tables:
                if 'Ticker' in table.columns:
                    return table['Ticker'].tolist()
                elif 'Symbol' in table.columns:
                    return table['Symbol'].tolist()
            return []
        except Exception as e:
            logger.error(f"Failed to fetch NASDAQ 100 list: {e}")
            return []

    def get_large_cap_stocks(self) -> List[Dict[str, Any]]:
        """Get all stocks with market cap > $1B from major exchanges."""
        tickers = set()

        # Get S&P 500 and NASDAQ 100 as starting points
        sp500 = self.get_sp500_tickers()
        nasdaq100 = self.get_nasdaq100_tickers()

        tickers.update(sp500)
        tickers.update(nasdaq100)

        logger.info(f"Found {len(tickers)} tickers to check")

        stocks = []
        for ticker in tickers:
            try:
                stock_info = self.fetch_stock_info(ticker)
                if stock_info and stock_info.get('market_cap', 0) >= self.min_market_cap:
                    stocks.append(stock_info)
            except Exception as e:
                logger.warning(f"Failed to fetch {ticker}: {e}")
                continue

        logger.info(f"Found {len(stocks)} stocks with market cap >= ${self.min_market_cap:,.0f}")
        return stocks

    def fetch_stock_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch basic stock information."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or 'marketCap' not in info:
                return None

            return {
                'ticker': ticker.upper(),
                'name': info.get('longName') or info.get('shortName', ticker),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'exchange': info.get('exchange'),
                'market_cap': info.get('marketCap'),
                'currency': info.get('currency', 'USD'),
            }
        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            return None

    def fetch_financial_statements(self, ticker: str) -> Dict[str, pd.DataFrame]:
        """Fetch quarterly and annual financial statements."""
        try:
            stock = yf.Ticker(ticker)

            return {
                'income_quarterly': stock.quarterly_income_stmt,
                'income_annual': stock.income_stmt,
                'balance_quarterly': stock.quarterly_balance_sheet,
                'balance_annual': stock.balance_sheet,
                'cashflow_quarterly': stock.quarterly_cashflow,
                'cashflow_annual': stock.cashflow,
            }
        except Exception as e:
            logger.error(f"Error fetching financials for {ticker}: {e}")
            return {}

    def fetch_price_history(
        self,
        ticker: str,
        period: str = "5y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch historical price data."""
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period=period, interval=interval)
            return history
        except Exception as e:
            logger.error(f"Error fetching price history for {ticker}: {e}")
            return pd.DataFrame()

    def save_stock(self, stock_info: Dict[str, Any]) -> Stock:
        """Save or update stock in database."""
        stock = self.db.query(Stock).filter(
            Stock.ticker == stock_info['ticker']
        ).first()

        if stock:
            # Update existing
            for key, value in stock_info.items():
                setattr(stock, key, value)
            stock.last_updated = datetime.utcnow()
        else:
            # Create new
            stock = Stock(**stock_info)
            self.db.add(stock)

        self.db.commit()
        self.db.refresh(stock)
        return stock

    def save_financial_statement(
        self,
        stock_id: int,
        period_type: str,
        data: Dict[str, Any]
    ) -> FinancialStatement:
        """Save financial statement to database."""
        # Check if exists
        existing = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == period_type,
            FinancialStatement.period_end_date == data['period_end_date']
        ).first()

        if existing:
            # Update
            for key, value in data.items():
                setattr(existing, key, value)
            self.db.commit()
            return existing
        else:
            # Create new
            statement = FinancialStatement(stock_id=stock_id, period_type=period_type, **data)
            self.db.add(statement)
            self.db.commit()
            self.db.refresh(statement)
            return statement

    def save_daily_prices(self, stock_id: int, history: pd.DataFrame) -> int:
        """Save daily price data to database."""
        count = 0
        for idx, row in history.iterrows():
            price_date = idx.date() if hasattr(idx, 'date') else idx

            existing = self.db.query(DailyPrice).filter(
                DailyPrice.stock_id == stock_id,
                DailyPrice.date == price_date
            ).first()

            if not existing:
                price = DailyPrice(
                    stock_id=stock_id,
                    date=price_date,
                    open=row.get('Open'),
                    high=row.get('High'),
                    low=row.get('Low'),
                    close=row['Close'],
                    adjusted_close=row.get('Adj Close'),
                    volume=row.get('Volume'),
                )
                self.db.add(price)
                count += 1

        self.db.commit()
        return count

    def parse_financial_statements(
        self,
        ticker: str,
        statements: Dict[str, pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """Parse yfinance financial statements into structured data."""
        parsed = []

        # Process quarterly income statements
        if 'income_quarterly' in statements and not statements['income_quarterly'].empty:
            df = statements['income_quarterly']
            for col in df.columns:
                period_date = col.date() if hasattr(col, 'date') else col
                data = self._extract_income_data(df[col], period_date, 'quarterly')
                if data:
                    parsed.append(data)

        # Process annual income statements
        if 'income_annual' in statements and not statements['income_annual'].empty:
            df = statements['income_annual']
            for col in df.columns:
                period_date = col.date() if hasattr(col, 'date') else col
                data = self._extract_income_data(df[col], period_date, 'annual')
                if data:
                    parsed.append(data)

        # Merge with balance sheet and cash flow data
        self._merge_balance_sheet_data(parsed, statements)
        self._merge_cashflow_data(parsed, statements)

        return parsed

    def _extract_income_data(
        self,
        series: pd.Series,
        period_date: date,
        period_type: str
    ) -> Optional[Dict[str, Any]]:
        """Extract income statement data."""
        try:
            fiscal_year = period_date.year
            fiscal_quarter = (period_date.month - 1) // 3 + 1 if period_type == 'quarterly' else None

            return {
                'period_end_date': period_date,
                'period_type': period_type,
                'fiscal_year': fiscal_year,
                'fiscal_quarter': fiscal_quarter,
                'revenue': self._safe_get(series, ['Total Revenue', 'Revenue']),
                'cost_of_revenue': self._safe_get(series, ['Cost Of Revenue']),
                'gross_profit': self._safe_get(series, ['Gross Profit']),
                'operating_income': self._safe_get(series, ['Operating Income', 'EBIT']),
                'net_income': self._safe_get(series, ['Net Income', 'Net Income Common Stockholders']),
                'ebitda': self._safe_get(series, ['EBITDA', 'Normalized EBITDA']),
                'ebit': self._safe_get(series, ['EBIT', 'Operating Income']),
                'earnings_per_share': self._safe_get(series, ['Basic EPS', 'Diluted EPS']),
            }
        except Exception as e:
            logger.warning(f"Error extracting income data: {e}")
            return None

    def _merge_balance_sheet_data(
        self,
        parsed: List[Dict[str, Any]],
        statements: Dict[str, pd.DataFrame]
    ):
        """Merge balance sheet data into parsed statements."""
        for period_type in ['quarterly', 'annual']:
            key = f'balance_{period_type}'
            if key not in statements or statements[key].empty:
                continue

            df = statements[key]
            for item in parsed:
                if item['period_type'] != period_type:
                    continue

                # Find matching date column
                for col in df.columns:
                    col_date = col.date() if hasattr(col, 'date') else col
                    if col_date == item['period_end_date']:
                        series = df[col]
                        item.update({
                            'total_assets': self._safe_get(series, ['Total Assets']),
                            'total_liabilities': self._safe_get(series, ['Total Liabilities Net Minority Interest', 'Total Liabilities']),
                            'total_equity': self._safe_get(series, ['Total Equity Gross Minority Interest', 'Stockholders Equity']),
                            'current_assets': self._safe_get(series, ['Current Assets']),
                            'current_liabilities': self._safe_get(series, ['Current Liabilities']),
                            'total_debt': self._safe_get(series, ['Total Debt', 'Long Term Debt']),
                            'cash_and_equivalents': self._safe_get(series, ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments']),
                            'shares_outstanding': self._safe_get(series, ['Share Issued', 'Ordinary Shares Number']),
                        })
                        break

    def _merge_cashflow_data(
        self,
        parsed: List[Dict[str, Any]],
        statements: Dict[str, pd.DataFrame]
    ):
        """Merge cash flow data into parsed statements."""
        for period_type in ['quarterly', 'annual']:
            key = f'cashflow_{period_type}'
            if key not in statements or statements[key].empty:
                continue

            df = statements[key]
            for item in parsed:
                if item['period_type'] != period_type:
                    continue

                for col in df.columns:
                    col_date = col.date() if hasattr(col, 'date') else col
                    if col_date == item['period_end_date']:
                        series = df[col]
                        operating_cf = self._safe_get(series, ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities'])
                        capex = self._safe_get(series, ['Capital Expenditure', 'Purchase Of PPE'])

                        # CapEx is usually negative in statements
                        if capex and capex > 0:
                            capex = -capex

                        fcf = None
                        if operating_cf is not None and capex is not None:
                            fcf = operating_cf + capex  # capex is negative

                        item.update({
                            'operating_cash_flow': operating_cf,
                            'capital_expenditure': capex,
                            'free_cash_flow': fcf,
                            'dividends_paid': self._safe_get(series, ['Cash Dividends Paid', 'Common Stock Dividend Paid']),
                        })
                        break

    def _safe_get(self, series: pd.Series, keys: List[str]) -> Optional[float]:
        """Safely get value from series, trying multiple keys."""
        for key in keys:
            if key in series.index:
                val = series[key]
                if pd.notna(val):
                    return float(val)
        return None

    def refresh_stock_data(self, ticker: str) -> Optional[Stock]:
        """Refresh all data for a single stock."""
        logger.info(f"Refreshing data for {ticker}")

        # Fetch and save stock info
        stock_info = self.fetch_stock_info(ticker)
        if not stock_info:
            logger.warning(f"Could not fetch info for {ticker}")
            return None

        if stock_info.get('market_cap', 0) < self.min_market_cap:
            logger.info(f"Skipping {ticker} - market cap below threshold")
            return None

        stock = self.save_stock(stock_info)

        # Fetch and save financial statements
        statements = self.fetch_financial_statements(ticker)
        if statements:
            parsed = self.parse_financial_statements(ticker, statements)
            for data in parsed:
                period_type = data.pop('period_type')
                self.save_financial_statement(stock.id, period_type, data)

        # Fetch and save price history
        history = self.fetch_price_history(ticker)
        if not history.empty:
            self.save_daily_prices(stock.id, history)

        logger.info(f"Successfully refreshed data for {ticker}")
        return stock

    def refresh_all_stocks(self) -> int:
        """Refresh data for all large-cap stocks."""
        stocks = self.get_large_cap_stocks()
        count = 0

        for stock_info in stocks:
            try:
                result = self.refresh_stock_data(stock_info['ticker'])
                if result:
                    count += 1
            except Exception as e:
                logger.error(f"Error refreshing {stock_info['ticker']}: {e}")
                continue

        logger.info(f"Refreshed {count} stocks")
        return count

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current price for a stock."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info.get('currentPrice') or info.get('regularMarketPrice')
        except Exception as e:
            logger.error(f"Error getting price for {ticker}: {e}")
            return None
