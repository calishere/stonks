from typing import Optional, List, Dict, Any
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
import finnhub

from app.models.stock import Stock
from app.models.financial import FinancialStatement, DailyPrice, CalculatedMetrics
from app.core.config import settings

logger = logging.getLogger(__name__)

# DCF Model Parameters (based on SimplyWallSt methodology)
RISK_FREE_RATE = 0.045  # ~4.5% (5-year avg of 10-year govt bond)
EQUITY_RISK_PREMIUM = 0.055  # ~5.5% market risk premium
DEFAULT_BETA = 1.0  # Market average
MIN_BETA = 0.8
MAX_BETA = 2.0
DEFAULT_TERMINAL_GROWTH = 0.025  # 2.5% perpetual growth (near risk-free rate)
DEFAULT_PROJECTION_YEARS = 10
UNDERVALUED_THRESHOLD = 0.20  # 20% below fair value = undervalued
OVERVALUED_THRESHOLD = 0.20  # 20% above fair value = overvalued


class MetricsCalculator:
    """Service for calculating financial metrics."""

    def __init__(self, db: Session):
        self.db = db
        self.finnhub_client = finnhub.Client(api_key=settings.finnhub_api_key)

    def _get_current_price_from_api(self, ticker: str) -> Optional[float]:
        """Fetch current price from Finnhub API."""
        try:
            quote = self.finnhub_client.quote(ticker)
            price = quote.get('c')
            if price and price > 0:
                return price
        except Exception as e:
            logger.warning(f"Could not fetch current price for {ticker}: {e}")
        return None

    def _estimate_ttm_fcf(self, ticker: str, annual_fcf: float, annual_eps: Optional[float]) -> float:
        """
        Estimate TTM FCF by scaling annual FCF based on recent quarterly EPS growth.

        If quarterly earnings show growth since the annual report, scale FCF proportionally.
        This gives a more current FCF estimate than waiting for the next 10-K.
        """
        if not annual_eps or annual_eps <= 0:
            return annual_fcf

        try:
            # Get last 4 quarters of earnings
            earnings = self.finnhub_client.company_earnings(ticker, limit=4)
            if not earnings or len(earnings) < 4:
                return annual_fcf

            # Calculate TTM EPS from quarterly data
            ttm_eps = sum(e.get('actual', 0) for e in earnings if e.get('actual'))
            if ttm_eps <= 0:
                return annual_fcf

            # Calculate EPS growth factor
            eps_growth_factor = ttm_eps / annual_eps

            # Cap the scaling factor to avoid extreme values (0.7x to 1.5x)
            # More conservative range since EPS growth doesn't always translate to FCF growth
            eps_growth_factor = max(0.7, min(1.5, eps_growth_factor))

            # Scale FCF by EPS growth
            ttm_fcf = annual_fcf * eps_growth_factor

            if abs(eps_growth_factor - 1.0) > 0.05:  # Only log if >5% difference
                logger.info(f"{ticker}: Scaling FCF by {eps_growth_factor:.2f}x (TTM EPS ${ttm_eps:.2f} vs Annual ${annual_eps:.2f})")

            return ttm_fcf

        except Exception as e:
            logger.warning(f"Could not estimate TTM FCF for {ticker}: {e}")
            return annual_fcf

    def calculate_all_metrics(self, stock_id: int) -> List[CalculatedMetrics]:
        """Calculate all metrics for a stock."""
        metrics = []

        # Calculate for quarterly periods
        quarterly = self._calculate_period_metrics(stock_id, 'quarterly')
        metrics.extend(quarterly)

        # Calculate for annual periods
        annual = self._calculate_period_metrics(stock_id, 'annual')
        metrics.extend(annual)

        # Calculate TTM (Trailing Twelve Months)
        ttm = self._calculate_ttm_metrics(stock_id)
        if ttm:
            metrics.append(ttm)

        # Calculate DCF fair value for the latest annual period
        if annual:
            self._calculate_dcf_valuation(stock_id, annual[0])

        return metrics

    def _calculate_dcf_valuation(self, stock_id: int, latest_metrics: CalculatedMetrics) -> None:
        """
        Calculate DCF-based fair value using SimplyWallSt-inspired methodology.

        Uses 2-Stage FCF model with CAPM discount rate.
        """
        stock = self.db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            return

        # Get the latest financial statement
        latest_stmt = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == 'annual'
        ).order_by(desc(FinancialStatement.period_end_date)).first()

        if not latest_stmt or not latest_stmt.free_cash_flow:
            logger.warning(f"No FCF data for stock {stock.ticker}")
            return

        # Skip stocks with outdated financial data (> 2 years old)
        data_age_days = (date.today() - latest_stmt.period_end_date).days
        if data_age_days > 730:  # ~2 years
            logger.warning(f"Skipping {stock.ticker}: financial data too old ({latest_stmt.period_end_date})")
            return

        # Get current price from Finnhub
        current_price = self._get_current_price_from_api(stock.ticker)
        if not current_price:
            logger.warning(f"Could not get current price for {stock.ticker}")
            return

        # Calculate shares outstanding from market cap and price if not available
        shares_outstanding = latest_stmt.shares_outstanding
        if not shares_outstanding and stock.market_cap and current_price:
            shares_outstanding = stock.market_cap / current_price

        if not shares_outstanding:
            logger.warning(f"Could not determine shares outstanding for {stock.ticker}")
            return

        # Calculate CAPM discount rate
        beta = self._estimate_beta(stock_id, latest_stmt)
        discount_rate = RISK_FREE_RATE + (beta * EQUITY_RISK_PREMIUM)

        # Estimate growth rate from Finnhub metrics or historical data
        fcf_growth_rate = self._estimate_growth_rate(stock_id, stock.ticker)

        # Try to get more current TTM FCF estimate from quarterly earnings
        current_fcf = self._estimate_ttm_fcf(
            stock.ticker,
            latest_stmt.free_cash_flow,
            latest_stmt.earnings_per_share
        )

        # Perform 2-Stage DCF calculation
        dcf_result = self._dcf_calculation(
            current_fcf=current_fcf,
            growth_rate=fcf_growth_rate,
            shares_outstanding=shares_outstanding,
            total_debt=latest_stmt.total_debt or 0,
            cash=latest_stmt.cash_and_equivalents or 0,
            discount_rate=discount_rate
        )

        if not dcf_result:
            return

        fair_value = dcf_result['fair_value_per_share']

        # Calculate margin of safety: positive = undervalued, negative = overvalued
        # Formula: (Fair Value - Current Price) / Current Price * 100
        margin_of_safety = ((fair_value - current_price) / current_price) * 100

        # Determine valuation status (SimplyWallSt uses 20% threshold)
        if margin_of_safety > UNDERVALUED_THRESHOLD * 100:
            valuation_status = 'undervalued'
        elif margin_of_safety < -OVERVALUED_THRESHOLD * 100:
            valuation_status = 'overvalued'
        else:
            valuation_status = 'fair'

        # Update the metrics
        latest_metrics.dcf_value = dcf_result['dcf_value']
        latest_metrics.fair_value_per_share = fair_value
        latest_metrics.margin_of_safety = margin_of_safety
        latest_metrics.valuation_status = valuation_status

        self.db.commit()
        logger.info(f"{stock.ticker}: Fair=${fair_value:.2f}, Current=${current_price:.2f}, "
                   f"MOS={margin_of_safety:.1f}%, Beta={beta:.2f}, Status={valuation_status}")

    def _estimate_beta(self, stock_id: int, stmt: FinancialStatement) -> float:
        """
        Estimate beta using leverage adjustment (SimplyWallSt approach).

        Levered Beta = Unlevered Beta × (1 + (1 - tax rate) × (Debt/Equity))
        """
        # Start with market beta
        unlevered_beta = 1.0

        # Adjust for leverage if we have the data
        if stmt.total_debt and stmt.total_equity and stmt.total_equity > 0:
            tax_rate = 0.21  # US corporate tax rate
            debt_to_equity = stmt.total_debt / stmt.total_equity
            levered_beta = unlevered_beta * (1 + (1 - tax_rate) * debt_to_equity)
        else:
            levered_beta = DEFAULT_BETA

        # Constrain beta (SimplyWallSt uses 0.8-2.0)
        return max(MIN_BETA, min(MAX_BETA, levered_beta))

    def _estimate_growth_rate(self, stock_id: int, ticker: str) -> float:
        """
        Estimate future growth rate using Finnhub metrics (preferred) or historical data.

        Priority:
        1. Finnhub 5-year EPS growth (most relevant for FCF proxy)
        2. Finnhub 5-year revenue growth (secondary indicator)
        3. Historical FCF growth (fallback with conservatism factor)

        Growth rate is capped at 12% (sustainable long-term growth ceiling)
        and floored at -5% (companies rarely sustain worse decline).
        """
        # Try to get growth rate from Finnhub basic financials
        try:
            financials = self.finnhub_client.company_basic_financials(ticker, 'all')
            metrics = financials.get('metric', {})

            # Prefer 5-year EPS growth as it's closer to FCF
            eps_growth_5y = metrics.get('epsGrowth5Y')
            revenue_growth_5y = metrics.get('revenueGrowth5Y')

            if eps_growth_5y is not None:
                # Convert from percentage to decimal
                growth = eps_growth_5y / 100
                logger.debug(f"{ticker}: Using Finnhub 5Y EPS growth: {growth*100:.1f}%")
                return max(-0.05, min(0.12, growth))

            if revenue_growth_5y is not None:
                # Revenue growth is often higher than earnings growth
                # Apply slight discount as FCF growth typically lags revenue
                growth = (revenue_growth_5y / 100) * 0.85
                logger.debug(f"{ticker}: Using Finnhub 5Y revenue growth (discounted): {growth*100:.1f}%")
                return max(-0.05, min(0.12, growth))

        except Exception as e:
            logger.warning(f"Could not fetch Finnhub growth metrics for {ticker}: {e}")

        # Fallback: Calculate from historical FCF data
        statements = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == 'annual',
            FinancialStatement.free_cash_flow.isnot(None)
        ).order_by(desc(FinancialStatement.period_end_date)).limit(5).all()

        if len(statements) < 2:
            return 0.05  # Default 5% growth

        # Calculate average growth rate
        growth_rates = []
        for i in range(len(statements) - 1):
            current = statements[i].free_cash_flow
            previous = statements[i + 1].free_cash_flow
            if current and previous and previous > 0:
                growth = (current - previous) / previous
                growth_rates.append(growth)

        if not growth_rates:
            return 0.05

        avg_growth = sum(growth_rates) / len(growth_rates)

        # Apply conservatism factor (historical FCF growth is volatile)
        conservative_growth = avg_growth * 0.5

        logger.debug(f"{ticker}: Using historical FCF growth (conservative): {conservative_growth*100:.1f}%")
        return max(-0.05, min(0.12, conservative_growth))

    def _dcf_calculation(
        self,
        current_fcf: float,
        growth_rate: float,
        shares_outstanding: Optional[float],
        total_debt: float = 0,
        cash: float = 0,
        discount_rate: float = None,
        terminal_growth: float = DEFAULT_TERMINAL_GROWTH,
        years: int = DEFAULT_PROJECTION_YEARS
    ) -> Optional[Dict[str, float]]:
        """
        Perform 2-Stage Discounted Cash Flow valuation (SimplyWallSt methodology).

        Stage 1: High growth period (10 years) with growth decaying toward terminal
        Stage 2: Terminal value using Gordon Growth Model

        Returns fair value per share based on projected FCF.
        """
        if not current_fcf or current_fcf <= 0 or not shares_outstanding:
            return None

        if discount_rate is None:
            discount_rate = RISK_FREE_RATE + (DEFAULT_BETA * EQUITY_RISK_PREMIUM)

        # Ensure terminal growth is less than discount rate
        if terminal_growth >= discount_rate:
            terminal_growth = discount_rate - 0.01

        # Stage 1: Project future cash flows with decaying growth
        projected_fcf = []
        fcf = current_fcf
        for year in range(1, years + 1):
            # Linear decay from initial growth rate to terminal growth
            year_growth = growth_rate - (growth_rate - terminal_growth) * (year / years)
            fcf = fcf * (1 + year_growth)
            projected_fcf.append(fcf)

        # Calculate present value of Stage 1 cash flows
        pv_stage1 = sum(
            fcf / ((1 + discount_rate) ** (i + 1))
            for i, fcf in enumerate(projected_fcf)
        )

        # Stage 2: Terminal value using Gordon Growth Model
        # Terminal Value = FCF_n × (1 + g) / (r - g)
        terminal_fcf = projected_fcf[-1] * (1 + terminal_growth)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** years)

        # Total DCF value (Enterprise Value)
        dcf_value = pv_stage1 + pv_terminal

        # Equity Value = Enterprise Value - Net Debt
        # Net Debt = Total Debt - Cash
        equity_value = dcf_value - total_debt + cash

        # Ensure equity value is positive
        if equity_value <= 0:
            return None

        # Fair value per share
        fair_value_per_share = equity_value / shares_outstanding

        return {
            'dcf_value': dcf_value,
            'equity_value': equity_value,
            'fair_value_per_share': fair_value_per_share,
            'pv_stage1': pv_stage1,
            'pv_terminal': pv_terminal
        }

    def _calculate_period_metrics(
        self,
        stock_id: int,
        period_type: str
    ) -> List[CalculatedMetrics]:
        """Calculate metrics for all periods of a given type."""
        statements = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == period_type
        ).order_by(desc(FinancialStatement.period_end_date)).all()

        if not statements:
            return []

        # Get stock for market cap
        stock = self.db.query(Stock).filter(Stock.id == stock_id).first()

        metrics_list = []
        for i, stmt in enumerate(statements):
            # Get previous period for growth calculations
            prev_stmt = statements[i + 1] if i + 1 < len(statements) else None

            # Get YoY statement for growth (4 quarters back or 1 year back)
            yoy_idx = i + 4 if period_type == 'quarterly' else i + 1
            yoy_stmt = statements[yoy_idx] if yoy_idx < len(statements) else None

            # Get current price
            current_price = self._get_price_for_date(stock_id, stmt.period_end_date)

            metrics = self._calculate_single_period(
                stmt=stmt,
                prev_stmt=prev_stmt,
                yoy_stmt=yoy_stmt,
                stock=stock,
                period_type=period_type,
                current_price=current_price
            )

            if metrics:
                # Save to database
                saved = self._save_metrics(metrics)
                metrics_list.append(saved)

        return metrics_list

    def _calculate_single_period(
        self,
        stmt: FinancialStatement,
        prev_stmt: Optional[FinancialStatement],
        yoy_stmt: Optional[FinancialStatement],
        stock: Stock,
        period_type: str,
        current_price: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """Calculate metrics for a single period."""
        try:
            metrics = {
                'stock_id': stmt.stock_id,
                'period_type': period_type,
                'period_end_date': stmt.period_end_date,
            }

            # Profitability Margins
            if stmt.revenue and stmt.revenue > 0:
                if stmt.gross_profit:
                    metrics['gross_margin'] = (stmt.gross_profit / stmt.revenue) * 100

                if stmt.operating_income:
                    metrics['operating_margin'] = (stmt.operating_income / stmt.revenue) * 100

                if stmt.net_income:
                    metrics['net_profit_margin'] = (stmt.net_income / stmt.revenue) * 100

                if stmt.free_cash_flow:
                    metrics['fcf_margin'] = (stmt.free_cash_flow / stmt.revenue) * 100

                if stmt.operating_cash_flow:
                    metrics['operating_cash_flow_margin'] = (stmt.operating_cash_flow / stmt.revenue) * 100

            # Return Metrics
            if stmt.net_income:
                if stmt.total_equity and stmt.total_equity > 0:
                    metrics['roe'] = (stmt.net_income / stmt.total_equity) * 100

                if stmt.total_assets and stmt.total_assets > 0:
                    metrics['roa'] = (stmt.net_income / stmt.total_assets) * 100

            # ROCE = EBIT / Capital Employed
            # Capital Employed = Total Assets - Current Liabilities
            if stmt.ebit and stmt.total_assets and stmt.current_liabilities:
                capital_employed = stmt.total_assets - stmt.current_liabilities
                if capital_employed > 0:
                    metrics['roce'] = (stmt.ebit / capital_employed) * 100

            # Leverage Metrics
            if stmt.total_debt and stmt.total_equity and stmt.total_equity > 0:
                metrics['debt_to_equity'] = stmt.total_debt / stmt.total_equity

            if stmt.current_assets and stmt.current_liabilities and stmt.current_liabilities > 0:
                metrics['current_ratio'] = stmt.current_assets / stmt.current_liabilities

            # Growth Metrics (YoY)
            if yoy_stmt:
                metrics['revenue_growth'] = self._calc_growth(stmt.revenue, yoy_stmt.revenue)
                metrics['net_income_growth'] = self._calc_growth(stmt.net_income, yoy_stmt.net_income)
                metrics['fcf_growth'] = self._calc_growth(stmt.free_cash_flow, yoy_stmt.free_cash_flow)
                metrics['eps_growth'] = self._calc_growth(stmt.earnings_per_share, yoy_stmt.earnings_per_share)

            # Valuation Metrics (need current price and shares)
            if current_price and stmt.shares_outstanding and stmt.shares_outstanding > 0:
                market_cap = current_price * stmt.shares_outstanding

                # P/E Ratio
                if stmt.net_income and stmt.net_income > 0:
                    metrics['pe_ratio'] = market_cap / stmt.net_income

                # P/B Ratio
                if stmt.total_equity and stmt.total_equity > 0:
                    book_value_per_share = stmt.total_equity / stmt.shares_outstanding
                    metrics['pb_ratio'] = current_price / book_value_per_share

                # P/S Ratio
                if stmt.revenue and stmt.revenue > 0:
                    metrics['ps_ratio'] = market_cap / stmt.revenue

                # Price to FCF
                if stmt.free_cash_flow and stmt.free_cash_flow > 0:
                    metrics['price_to_fcf'] = market_cap / stmt.free_cash_flow
                    metrics['fcf_yield'] = (stmt.free_cash_flow / market_cap) * 100

                # EV/EBITDA
                if stmt.ebitda and stmt.ebitda > 0:
                    ev = market_cap + (stmt.total_debt or 0) - (stmt.cash_and_equivalents or 0)
                    metrics['ev_to_ebitda'] = ev / stmt.ebitda

                # PEG Ratio
                if metrics.get('pe_ratio') and metrics.get('eps_growth') and metrics['eps_growth'] > 0:
                    metrics['peg_ratio'] = metrics['pe_ratio'] / metrics['eps_growth']

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics for stock {stmt.stock_id}: {e}")
            return None

    def _calculate_ttm_metrics(self, stock_id: int) -> Optional[CalculatedMetrics]:
        """Calculate Trailing Twelve Months metrics."""
        # Get last 4 quarters
        quarters = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == 'quarterly'
        ).order_by(desc(FinancialStatement.period_end_date)).limit(4).all()

        if len(quarters) < 4:
            return None

        stock = self.db.query(Stock).filter(Stock.id == stock_id).first()

        # Sum TTM values
        ttm_revenue = sum(q.revenue or 0 for q in quarters)
        ttm_net_income = sum(q.net_income or 0 for q in quarters)
        ttm_fcf = sum(q.free_cash_flow or 0 for q in quarters)
        ttm_ebitda = sum(q.ebitda or 0 for q in quarters)
        ttm_operating_cf = sum(q.operating_cash_flow or 0 for q in quarters)

        # Use most recent quarter for balance sheet items
        latest = quarters[0]

        current_price = self._get_price_for_date(stock_id, latest.period_end_date)

        metrics = {
            'stock_id': stock_id,
            'period_type': 'ttm',
            'period_end_date': latest.period_end_date,
        }

        # Margins
        if ttm_revenue > 0:
            if latest.gross_profit:
                ttm_gross = sum(q.gross_profit or 0 for q in quarters)
                metrics['gross_margin'] = (ttm_gross / ttm_revenue) * 100

            ttm_operating = sum(q.operating_income or 0 for q in quarters)
            metrics['operating_margin'] = (ttm_operating / ttm_revenue) * 100
            metrics['net_profit_margin'] = (ttm_net_income / ttm_revenue) * 100
            metrics['fcf_margin'] = (ttm_fcf / ttm_revenue) * 100

        # Returns
        if ttm_net_income > 0:
            if latest.total_equity and latest.total_equity > 0:
                metrics['roe'] = (ttm_net_income / latest.total_equity) * 100
            if latest.total_assets and latest.total_assets > 0:
                metrics['roa'] = (ttm_net_income / latest.total_assets) * 100

        # ROCE
        ttm_ebit = sum(q.ebit or 0 for q in quarters)
        if ttm_ebit > 0 and latest.total_assets and latest.current_liabilities:
            capital_employed = latest.total_assets - latest.current_liabilities
            if capital_employed > 0:
                metrics['roce'] = (ttm_ebit / capital_employed) * 100

        # Valuation
        if current_price and latest.shares_outstanding:
            market_cap = current_price * latest.shares_outstanding

            if ttm_net_income > 0:
                metrics['pe_ratio'] = market_cap / ttm_net_income

            if latest.total_equity and latest.total_equity > 0:
                bvps = latest.total_equity / latest.shares_outstanding
                metrics['pb_ratio'] = current_price / bvps

            if ttm_revenue > 0:
                metrics['ps_ratio'] = market_cap / ttm_revenue

            if ttm_fcf > 0:
                metrics['price_to_fcf'] = market_cap / ttm_fcf
                metrics['fcf_yield'] = (ttm_fcf / market_cap) * 100

            if ttm_ebitda > 0:
                ev = market_cap + (latest.total_debt or 0) - (latest.cash_and_equivalents or 0)
                metrics['ev_to_ebitda'] = ev / ttm_ebitda

        return self._save_metrics(metrics)

    def _get_price_for_date(self, stock_id: int, target_date: date) -> Optional[float]:
        """Get stock price for a specific date or closest available."""
        # Try exact date first
        price = self.db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock_id,
            DailyPrice.date == target_date
        ).first()

        if price:
            return price.close

        # Try within 7 days
        price = self.db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock_id,
            DailyPrice.date <= target_date,
            DailyPrice.date >= target_date - timedelta(days=7)
        ).order_by(desc(DailyPrice.date)).first()

        return price.close if price else None

    def _calc_growth(
        self,
        current: Optional[float],
        previous: Optional[float]
    ) -> Optional[float]:
        """Calculate growth rate percentage."""
        if current is None or previous is None or previous == 0:
            return None

        return ((current - previous) / abs(previous)) * 100

    def _save_metrics(self, metrics: Dict[str, Any]) -> CalculatedMetrics:
        """Save or update calculated metrics."""
        existing = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == metrics['stock_id'],
            CalculatedMetrics.period_type == metrics['period_type'],
            CalculatedMetrics.period_end_date == metrics['period_end_date']
        ).first()

        if existing:
            for key, value in metrics.items():
                setattr(existing, key, value)
            self.db.commit()
            return existing
        else:
            calc_metrics = CalculatedMetrics(**metrics)
            self.db.add(calc_metrics)
            self.db.commit()
            self.db.refresh(calc_metrics)
            return calc_metrics

    def get_latest_metrics(self, stock_id: int) -> Optional[CalculatedMetrics]:
        """Get the most recent TTM or annual metrics for a stock."""
        # Prefer TTM
        metrics = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock_id,
            CalculatedMetrics.period_type == 'ttm'
        ).order_by(desc(CalculatedMetrics.period_end_date)).first()

        if metrics:
            return metrics

        # Fall back to annual
        return self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock_id,
            CalculatedMetrics.period_type == 'annual'
        ).order_by(desc(CalculatedMetrics.period_end_date)).first()

    def get_historical_metrics(
        self,
        stock_id: int,
        metric_name: str,
        period_type: str = 'quarterly',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get historical values for a specific metric."""
        metrics = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock_id,
            CalculatedMetrics.period_type == period_type
        ).order_by(desc(CalculatedMetrics.period_end_date)).limit(limit).all()

        result = []
        for m in metrics:
            value = getattr(m, metric_name, None)
            if value is not None:
                # Get fiscal info from financial statement
                stmt = self.db.query(FinancialStatement).filter(
                    FinancialStatement.stock_id == stock_id,
                    FinancialStatement.period_type == period_type,
                    FinancialStatement.period_end_date == m.period_end_date
                ).first()

                result.append({
                    'period_end_date': m.period_end_date,
                    'fiscal_year': stmt.fiscal_year if stmt else m.period_end_date.year,
                    'fiscal_quarter': stmt.fiscal_quarter if stmt else None,
                    'value': value
                })

        return list(reversed(result))  # Chronological order
