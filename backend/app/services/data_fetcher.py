import finnhub
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging
import io
import time

from app.models.stock import Stock
from app.models.financial import FinancialStatement, DailyPrice
from app.core.config import settings

logger = logging.getLogger(__name__)

# Headers to avoid being blocked
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Rate limiting settings for Finnhub (60 calls/min = 1 call/second to be safe)
REQUEST_DELAY = 1.0  # seconds between requests

# Alpha Vantage rate limit (5 calls/min for free tier, 12 second delay to be safe)
ALPHA_VANTAGE_DELAY = 12.0

# Ticker mappings for companies with restructured/rebranded tickers
# Maps the ticker we store -> ticker(s) to try for financial data
FINANCIAL_DATA_TICKER_MAP = {
    'GOOG': ['GOOGL'],      # Google -> Alphabet (GOOGL has newer filings)
    'FB': ['META'],          # Facebook -> Meta
    'TWTR': ['X'],           # Twitter -> X (if applicable)
}


class DataFetcher:
    """Service for fetching financial data from Finnhub and Alpha Vantage."""

    def __init__(self, db: Session):
        self.db = db
        self.min_market_cap = settings.min_market_cap
        self.finnhub_client = finnhub.Client(api_key=settings.finnhub_api_key)
        self.alpha_vantage_key = settings.alpha_vantage_api_key

    def get_sp500_tickers(self) -> List[str]:
        """Fetch S&P 500 ticker list from Wikipedia."""
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            tables = pd.read_html(io.StringIO(response.text))
            sp500_table = tables[0]
            tickers = sp500_table['Symbol'].str.replace('.', '-', regex=False).tolist()
            logger.info(f"Fetched {len(tickers)} S&P 500 tickers")
            return tickers
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500 list: {e}")
            return self._get_fallback_tickers()

    def get_nasdaq100_tickers(self) -> List[str]:
        """Fetch NASDAQ 100 ticker list."""
        try:
            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            tables = pd.read_html(io.StringIO(response.text))
            for table in tables:
                if 'Ticker' in table.columns:
                    tickers = table['Ticker'].tolist()
                    logger.info(f"Fetched {len(tickers)} NASDAQ 100 tickers")
                    return tickers
                elif 'Symbol' in table.columns:
                    tickers = table['Symbol'].tolist()
                    logger.info(f"Fetched {len(tickers)} NASDAQ 100 tickers")
                    return tickers
            return []
        except Exception as e:
            logger.error(f"Failed to fetch NASDAQ 100 list: {e}")
            return []

    def _get_fallback_tickers(self) -> List[str]:
        """Fallback list of major US stocks if Wikipedia fetch fails."""
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH',
            'JPM', 'JNJ', 'V', 'XOM', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
            'LLY', 'PEP', 'COST', 'KO', 'AVGO', 'WMT', 'MCD', 'CSCO', 'TMO', 'ACN',
            'ABT', 'DHR', 'NEE', 'LIN', 'ADBE', 'NKE', 'TXN', 'PM', 'UNP', 'RTX',
            'ORCL', 'CRM', 'AMD', 'INTC', 'QCOM', 'IBM', 'AMGN', 'HON', 'LOW', 'SPGI',
        ]

    def fetch_stock_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch basic stock information from Finnhub."""
        try:
            # Get company profile
            profile = self.finnhub_client.company_profile2(symbol=ticker)

            if not profile or 'marketCapitalization' not in profile:
                logger.warning(f"No profile data for {ticker}")
                return None

            # Finnhub returns market cap in millions
            market_cap = profile.get('marketCapitalization', 0) * 1_000_000

            return {
                'ticker': ticker.upper(),
                'name': profile.get('name', ticker),
                'sector': profile.get('finnhubIndustry'),
                'industry': profile.get('finnhubIndustry'),
                'exchange': profile.get('exchange'),
                'market_cap': market_cap,
                'currency': profile.get('currency', 'USD'),
            }
        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            return None

    def fetch_financial_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch financial metrics from Finnhub."""
        try:
            # Get basic financials (includes many key metrics)
            financials = self.finnhub_client.company_basic_financials(ticker, 'all')
            return financials if financials else {}
        except Exception as e:
            logger.error(f"Error fetching financials for {ticker}: {e}")
            return {}

    def fetch_financial_statements(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Fetch reported financial statements from Finnhub.

        Tries alternate tickers if the primary ticker has outdated or missing data.
        This handles cases like GOOG->GOOGL where company restructured.
        """
        def get_latest_year(statements):
            """Get the most recent filing year from statements."""
            if not statements:
                return 0
            years = [s.get('year', 0) for s in statements if s.get('year')]
            return max(years) if years else 0

        # Try primary ticker first
        try:
            reported = self.finnhub_client.financials_reported(symbol=ticker)
            statements = reported.get('data', []) if reported else []
            latest_year = get_latest_year(statements)

            # If data is recent enough (within 2 years), use it
            current_year = date.today().year
            if latest_year >= current_year - 2:
                return statements

            # Try alternate tickers if available
            alt_tickers = FINANCIAL_DATA_TICKER_MAP.get(ticker, [])
            for alt_ticker in alt_tickers:
                try:
                    time.sleep(REQUEST_DELAY)
                    alt_reported = self.finnhub_client.financials_reported(symbol=alt_ticker)
                    alt_statements = alt_reported.get('data', []) if alt_reported else []
                    alt_latest_year = get_latest_year(alt_statements)

                    # Use alternate if it has more recent data
                    if alt_latest_year > latest_year:
                        logger.info(f"Using {alt_ticker} financial data for {ticker} (more recent: {alt_latest_year} vs {latest_year})")
                        return alt_statements
                except Exception as e:
                    logger.warning(f"Error fetching alt ticker {alt_ticker}: {e}")

            # Return whatever we have
            return statements

        except Exception as e:
            logger.error(f"Error fetching financial statements for {ticker}: {e}")
            return []

    def fetch_price_history(
        self,
        ticker: str,
        period: str = "1y"
    ) -> pd.DataFrame:
        """Fetch historical price data using yfinance (Finnhub free tier doesn't include this)."""
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period=period, interval="1d")
            if not history.empty:
                logger.info(f"Fetched {len(history)} price records for {ticker}")
            else:
                logger.warning(f"No price history returned for {ticker}")
            return history
        except Exception as e:
            logger.warning(f"yfinance price fetch failed for {ticker}: {e}")
            return pd.DataFrame()

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current price for a stock."""
        try:
            # Try Finnhub first
            quote = self.finnhub_client.quote(ticker)
            price = quote.get('c')
            if price and price > 0:
                return price
        except Exception as e:
            logger.warning(f"Finnhub price fetch failed for {ticker}: {e}")

        # Fallback to yfinance
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info.get('currentPrice') or info.get('regularMarketPrice')
        except Exception as e:
            logger.error(f"Error getting price for {ticker}: {e}")
            return None

    def fetch_alpha_vantage_cash_flow(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Fetch cash flow data from Alpha Vantage.

        Used as fallback when Finnhub doesn't have FCF data.
        Free tier: 5 calls/minute, 500 calls/day.
        """
        if not self.alpha_vantage_key:
            return []

        try:
            url = f"https://www.alphavantage.co/query?function=CASH_FLOW&symbol={ticker}&apikey={self.alpha_vantage_key}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if 'Error Message' in data or 'Note' in data:
                logger.warning(f"Alpha Vantage error for {ticker}: {data.get('Error Message') or data.get('Note')}")
                return []

            annual_reports = data.get('annualReports', [])
            if not annual_reports:
                logger.warning(f"No Alpha Vantage cash flow data for {ticker}")
                return []

            logger.info(f"Fetched {len(annual_reports)} annual cash flow reports from Alpha Vantage for {ticker}")
            return annual_reports

        except Exception as e:
            logger.error(f"Alpha Vantage cash flow fetch failed for {ticker}: {e}")
            return []

    def fetch_alpha_vantage_income(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch income statement data from Alpha Vantage."""
        if not self.alpha_vantage_key:
            return []

        try:
            url = f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ticker}&apikey={self.alpha_vantage_key}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'Error Message' in data or 'Note' in data:
                return []

            return data.get('annualReports', [])

        except Exception as e:
            logger.error(f"Alpha Vantage income fetch failed for {ticker}: {e}")
            return []

    def fetch_alpha_vantage_balance(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch balance sheet data from Alpha Vantage."""
        if not self.alpha_vantage_key:
            return []

        try:
            url = f"https://www.alphavantage.co/query?function=BALANCE_SHEET&symbol={ticker}&apikey={self.alpha_vantage_key}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'Error Message' in data or 'Note' in data:
                return []

            return data.get('annualReports', [])

        except Exception as e:
            logger.error(f"Alpha Vantage balance fetch failed for {ticker}: {e}")
            return []

    def parse_alpha_vantage_financials(
        self,
        ticker: str,
        cash_flow: List[Dict],
        income: List[Dict],
        balance: List[Dict]
    ) -> List[tuple]:
        """Parse Alpha Vantage data into financial statement format."""
        parsed = []

        # Create lookup dicts by fiscal date
        income_by_date = {i.get('fiscalDateEnding'): i for i in income}
        balance_by_date = {b.get('fiscalDateEnding'): b for b in balance}

        for cf in cash_flow:
            try:
                fiscal_date = cf.get('fiscalDateEnding')
                if not fiscal_date:
                    continue

                end_date = datetime.strptime(fiscal_date, '%Y-%m-%d').date()
                inc = income_by_date.get(fiscal_date, {})
                bal = balance_by_date.get(fiscal_date, {})

                # Parse cash flow values
                operating_cf = self._safe_float(cf.get('operatingCashflow'))
                capex = self._safe_float(cf.get('capitalExpenditures'))
                net_income = self._safe_float(cf.get('netIncome')) or self._safe_float(inc.get('netIncome'))

                # Calculate FCF
                free_cash_flow = None
                if operating_cf is not None and capex is not None:
                    free_cash_flow = operating_cf - abs(capex)

                # Parse income statement
                revenue = self._safe_float(inc.get('totalRevenue'))
                gross_profit = self._safe_float(inc.get('grossProfit'))
                operating_income = self._safe_float(inc.get('operatingIncome'))
                eps = self._safe_float(inc.get('reportedEPS'))

                # Parse balance sheet
                total_assets = self._safe_float(bal.get('totalAssets'))
                total_liabilities = self._safe_float(bal.get('totalLiabilities'))
                total_equity = self._safe_float(bal.get('totalShareholderEquity'))
                cash = self._safe_float(bal.get('cashAndCashEquivalentsAtCarryingValue'))
                total_debt = self._safe_float(bal.get('longTermDebt'))

                data = {
                    'period_end_date': end_date,
                    'fiscal_year': end_date.year,
                    'revenue': revenue,
                    'gross_profit': gross_profit,
                    'operating_income': operating_income,
                    'net_income': net_income,
                    'earnings_per_share': eps,
                    'total_assets': total_assets,
                    'total_liabilities': total_liabilities,
                    'total_equity': total_equity,
                    'cash_and_equivalents': cash,
                    'total_debt': total_debt,
                    'operating_cash_flow': operating_cf,
                    'capital_expenditure': capex,
                    'free_cash_flow': free_cash_flow,
                }

                parsed.append(('annual', data))

            except Exception as e:
                logger.warning(f"Error parsing Alpha Vantage data for {ticker}: {e}")
                continue

        return parsed

    def save_stock(self, stock_info: Dict[str, Any]) -> Stock:
        """Save or update stock in database."""
        stock = self.db.query(Stock).filter(
            Stock.ticker == stock_info['ticker']
        ).first()

        if stock:
            for key, value in stock_info.items():
                setattr(stock, key, value)
            stock.last_updated = datetime.utcnow()
        else:
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
        existing = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == period_type,
            FinancialStatement.period_end_date == data['period_end_date']
        ).first()

        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            self.db.commit()
            return existing
        else:
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
                    volume=row.get('Volume'),
                )
                self.db.add(price)
                count += 1

        self.db.commit()
        return count

    def parse_finnhub_financials(
        self,
        ticker: str,
        financials: Dict[str, Any],
        statements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse Finnhub financial data into structured format."""
        parsed = []

        # Parse reported financial statements
        for statement in statements:
            try:
                report = statement.get('report', {})

                # Determine period type
                form = statement.get('form', '')
                period_type = 'quarterly' if '10-Q' in form else 'annual'

                # Parse date
                end_date_str = statement.get('endDate') or statement.get('filedDate')
                if not end_date_str:
                    continue

                end_date = datetime.strptime(end_date_str[:10], '%Y-%m-%d').date()

                # Extract income statement data
                income = report.get('ic', [])
                balance = report.get('bs', [])
                cashflow = report.get('cf', [])

                data = {
                    'period_end_date': end_date,
                    'fiscal_year': statement.get('year'),
                    'fiscal_quarter': statement.get('quarter'),
                    'revenue': self._find_concept(income, ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet']),
                    'cost_of_revenue': self._find_concept(income, ['CostOfRevenue', 'CostOfGoodsAndServicesSold']),
                    'gross_profit': self._find_concept(income, ['GrossProfit']),
                    'operating_income': self._find_concept(income, ['OperatingIncomeLoss', 'OperatingIncome']),
                    'net_income': self._find_concept(income, ['NetIncomeLoss', 'NetIncome']),
                    'earnings_per_share': self._find_concept(income, ['EarningsPerShareBasic', 'EarningsPerShareDiluted']),
                    'total_assets': self._find_concept(balance, ['Assets']),
                    'total_liabilities': self._find_concept(balance, ['Liabilities', 'LiabilitiesAndStockholdersEquity']),
                    'total_equity': self._find_concept(balance, ['StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']),
                    'cash_and_equivalents': self._find_concept(balance, ['CashAndCashEquivalentsAtCarryingValue', 'Cash']),
                    'total_debt': self._find_concept(balance, ['LongTermDebt', 'LongTermDebtNoncurrent']),
                    'operating_cash_flow': self._find_concept(cashflow, ['NetCashProvidedByUsedInOperatingActivities']),
                    'capital_expenditure': self._find_concept(cashflow, ['PaymentsToAcquirePropertyPlantAndEquipment']),
                }

                # Calculate free cash flow
                if data['operating_cash_flow'] and data['capital_expenditure']:
                    capex = abs(data['capital_expenditure'])
                    data['free_cash_flow'] = data['operating_cash_flow'] - capex

                parsed.append((period_type, data))

            except Exception as e:
                logger.warning(f"Error parsing statement for {ticker}: {e}")
                continue

        return parsed

    def _safe_float(self, val: Any) -> Optional[float]:
        """Safely convert a value to float, handling N/A and other non-numeric values."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            val = val.strip()
            if val.upper() in ('N/A', 'NA', 'NAN', 'NULL', '', '-'):
                return None
            try:
                return float(val)
            except ValueError:
                return None
        return None

    def _find_concept(self, items: List[Dict], concepts: List[str]) -> Optional[float]:
        """Find a value by concept name in Finnhub financial data."""
        for item in items:
            concept = item.get('concept', '')
            for target in concepts:
                if target.lower() in concept.lower():
                    val = item.get('value')
                    return self._safe_float(val)
        return None

    def refresh_stock_data(self, ticker: str) -> Optional[Stock]:
        """Refresh all data for a single stock."""
        logger.info(f"Refreshing data for {ticker}")

        # Fetch stock info
        stock_info = self.fetch_stock_info(ticker)
        time.sleep(REQUEST_DELAY)

        if not stock_info:
            logger.warning(f"Could not fetch info for {ticker}")
            return None

        if stock_info.get('market_cap', 0) < self.min_market_cap:
            logger.info(f"Skipping {ticker} - market cap below threshold")
            return None

        stock = self.save_stock(stock_info)

        # Fetch and save financial statements from Finnhub
        has_fcf_data = False
        try:
            statements = self.fetch_financial_statements(ticker)
            time.sleep(REQUEST_DELAY)

            financials = self.fetch_financial_data(ticker)
            time.sleep(REQUEST_DELAY)

            if statements:
                parsed = self.parse_finnhub_financials(ticker, financials, statements)
                for period_type, data in parsed:
                    self.save_financial_statement(stock.id, period_type, data)
                    if data.get('free_cash_flow'):
                        has_fcf_data = True
        except Exception as e:
            logger.warning(f"Could not fetch financials for {ticker}: {e}")

        # If no FCF data from Finnhub, try Alpha Vantage
        if not has_fcf_data and self.alpha_vantage_key:
            try:
                logger.info(f"Trying Alpha Vantage for {ticker} FCF data...")
                cash_flow = self.fetch_alpha_vantage_cash_flow(ticker)
                time.sleep(ALPHA_VANTAGE_DELAY)

                if cash_flow:
                    income = self.fetch_alpha_vantage_income(ticker)
                    time.sleep(ALPHA_VANTAGE_DELAY)

                    balance = self.fetch_alpha_vantage_balance(ticker)
                    time.sleep(ALPHA_VANTAGE_DELAY)

                    parsed = self.parse_alpha_vantage_financials(ticker, cash_flow, income, balance)
                    for period_type, data in parsed:
                        self.save_financial_statement(stock.id, period_type, data)
                    logger.info(f"Saved {len(parsed)} Alpha Vantage statements for {ticker}")
            except Exception as e:
                logger.warning(f"Alpha Vantage fallback failed for {ticker}: {e}")

        # Price history skipped - yfinance rate limited, Finnhub requires premium
        # TODO: Re-enable when rate limits clear or using paid API
        # try:
        #     history = self.fetch_price_history(ticker)
        #     time.sleep(REQUEST_DELAY)
        #     if not history.empty:
        #         self.save_daily_prices(stock.id, history)
        # except Exception as e:
        #     logger.warning(f"Could not fetch price history for {ticker}: {e}")

        logger.info(f"Successfully refreshed data for {ticker}")
        return stock

    def get_large_cap_stocks(self) -> List[Dict[str, Any]]:
        """Get all stocks with market cap > threshold from major exchanges."""
        tickers = set()

        sp500 = self.get_sp500_tickers()
        nasdaq100 = self.get_nasdaq100_tickers()

        tickers.update(sp500)
        tickers.update(nasdaq100)

        logger.info(f"Found {len(tickers)} tickers to check")

        stocks = []
        ticker_list = list(tickers)
        for i, ticker in enumerate(ticker_list):
            try:
                stock_info = self.fetch_stock_info(ticker)
                if stock_info and stock_info.get('market_cap', 0) >= self.min_market_cap:
                    stocks.append(stock_info)
                    logger.info(f"[{i+1}/{len(ticker_list)}] Added {ticker}")

                time.sleep(REQUEST_DELAY)

            except Exception as e:
                logger.warning(f"Failed to fetch {ticker}: {e}")
                continue

        logger.info(f"Found {len(stocks)} stocks with market cap >= ${self.min_market_cap:,.0f}")
        return stocks

    def refresh_all_stocks(self) -> int:
        """Refresh data for all large-cap stocks."""
        stocks = self.get_large_cap_stocks()
        count = 0
        total = len(stocks)

        for i, stock_info in enumerate(stocks):
            try:
                logger.info(f"[{i+1}/{total}] Processing {stock_info['ticker']}...")

                # Save the stock info we already have
                stock = self.save_stock(stock_info)

                # Fetch additional data
                statements = self.fetch_financial_statements(stock_info['ticker'])
                time.sleep(REQUEST_DELAY)

                financials = self.fetch_financial_data(stock_info['ticker'])
                time.sleep(REQUEST_DELAY)

                if statements:
                    parsed = self.parse_finnhub_financials(stock_info['ticker'], financials, statements)
                    for period_type, data in parsed:
                        self.save_financial_statement(stock.id, period_type, data)

                # Price history skipped - rate limited
                # history = self.fetch_price_history(stock_info['ticker'])
                # time.sleep(REQUEST_DELAY)
                # if not history.empty:
                #     self.save_daily_prices(stock.id, history)

                count += 1

            except Exception as e:
                logger.error(f"Error refreshing {stock_info['ticker']}: {e}")
                continue

        logger.info(f"Refreshed {count} stocks")
        return count
