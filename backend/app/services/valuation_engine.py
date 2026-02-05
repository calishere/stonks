from typing import Optional, Dict, Any, List
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
import numpy as np

from app.models.stock import Stock
from app.models.financial import FinancialStatement, DailyPrice, CalculatedMetrics
from app.services.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class ValuationEngine:
    """Service for calculating stock valuations using DCF and other methods."""

    # Default assumptions
    DEFAULT_DISCOUNT_RATE = 0.10  # 10% WACC
    DEFAULT_TERMINAL_GROWTH = 0.03  # 3% perpetual growth
    DEFAULT_PROJECTION_YEARS = 10
    RISK_FREE_RATE = 0.04  # 4% risk-free rate
    MARKET_RISK_PREMIUM = 0.06  # 6% market risk premium

    def __init__(self, db: Session):
        self.db = db
        self.data_fetcher = DataFetcher(db)

    def calculate_dcf(
        self,
        ticker: str,
        growth_rate: Optional[float] = None,
        discount_rate: Optional[float] = None,
        terminal_growth_rate: Optional[float] = None,
        projection_years: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate Discounted Cash Flow valuation for a stock.

        Args:
            ticker: Stock ticker symbol
            growth_rate: Override for estimated FCF growth rate
            discount_rate: Override for discount rate (WACC)
            terminal_growth_rate: Perpetual growth rate (default 3%)
            projection_years: Number of years to project (default 10)

        Returns:
            Complete DCF valuation analysis
        """
        stock = self.db.query(Stock).filter(Stock.ticker == ticker.upper()).first()
        if not stock:
            logger.warning(f"Stock {ticker} not found")
            return None

        # Get latest financial data
        latest_fcf = self._get_latest_fcf(stock.id)
        if latest_fcf is None or latest_fcf <= 0:
            logger.warning(f"No positive FCF for {ticker}")
            return None

        # Get current price
        current_price = self.data_fetcher.get_current_price(ticker)
        if not current_price:
            current_price = self._get_latest_price(stock.id)
            if not current_price:
                return None

        # Get shares outstanding
        shares = self._get_shares_outstanding(stock.id)
        if not shares:
            return None

        market_cap = current_price * shares

        # Determine growth rate
        if growth_rate is None:
            growth_rate = self._estimate_growth_rate(stock.id)

        # Cap growth rate to reasonable bounds
        growth_rate = max(-0.10, min(0.30, growth_rate))  # -10% to 30%

        # Use default or provided discount rate
        if discount_rate is None:
            discount_rate = self._estimate_wacc(stock.id)

        if terminal_growth_rate is None:
            terminal_growth_rate = self.DEFAULT_TERMINAL_GROWTH

        # Ensure terminal growth < discount rate
        if terminal_growth_rate >= discount_rate:
            terminal_growth_rate = discount_rate - 0.02

        # Calculate DCF projections
        projections = []
        total_pv = 0

        for year in range(1, projection_years + 1):
            # Project FCF with growth
            projected_fcf = latest_fcf * ((1 + growth_rate) ** year)

            # Decay growth rate over time (mean reversion)
            if year > 5:
                growth_rate = growth_rate * 0.9  # Reduce growth assumption

            # Discount factor
            discount_factor = 1 / ((1 + discount_rate) ** year)

            # Present value
            pv = projected_fcf * discount_factor

            projections.append({
                'year': year,
                'projected_fcf': round(projected_fcf, 2),
                'discount_factor': round(discount_factor, 4),
                'present_value': round(pv, 2)
            })

            total_pv += pv

        # Terminal value (Gordon Growth Model)
        final_fcf = projections[-1]['projected_fcf']
        terminal_value = (final_fcf * (1 + terminal_growth_rate)) / (discount_rate - terminal_growth_rate)
        terminal_value_pv = terminal_value / ((1 + discount_rate) ** projection_years)

        # Enterprise Value = PV of projected FCFs + PV of Terminal Value
        enterprise_value = total_pv + terminal_value_pv

        # Equity Value = Enterprise Value - Net Debt
        net_debt = self._get_net_debt(stock.id)
        equity_value = enterprise_value - net_debt

        # Fair value per share
        fair_value_per_share = equity_value / shares

        # Calculate upside/downside
        upside_downside = ((fair_value_per_share - current_price) / current_price) * 100
        margin_of_safety = upside_downside

        # Determine valuation status
        if margin_of_safety > 20:
            valuation_status = "undervalued"
        elif margin_of_safety < -20:
            valuation_status = "overvalued"
        else:
            valuation_status = "fair"

        # Generate summary
        summary = self._generate_summary(
            ticker, current_price, fair_value_per_share,
            margin_of_safety, valuation_status, growth_rate
        )

        # Calculate alternative valuations for comparison
        pe_value = self._calculate_pe_based_value(stock.id, current_price, shares)
        pb_value = self._calculate_pb_based_value(stock.id, shares)
        ps_value = self._calculate_ps_based_value(stock.id, shares)

        # Save valuation metrics
        self._save_valuation_metrics(
            stock.id, fair_value_per_share, margin_of_safety, valuation_status
        )

        return {
            'ticker': ticker.upper(),
            'name': stock.name,
            'current_price': round(current_price, 2),
            'shares_outstanding': shares,
            'market_cap': round(market_cap, 2),

            'latest_fcf': round(latest_fcf, 2),
            'estimated_growth_rate': round(growth_rate * 100, 2),  # As percentage
            'discount_rate': round(discount_rate * 100, 2),
            'terminal_growth_rate': round(terminal_growth_rate * 100, 2),
            'projection_years': projection_years,

            'projections': projections,
            'terminal_value': round(terminal_value, 2),
            'terminal_value_pv': round(terminal_value_pv, 2),

            'enterprise_value': round(enterprise_value, 2),
            'equity_value': round(equity_value, 2),
            'fair_value_per_share': round(fair_value_per_share, 2),

            'upside_downside': round(upside_downside, 2),
            'margin_of_safety': round(margin_of_safety, 2),
            'valuation_status': valuation_status,

            'pe_based_value': pe_value,
            'pb_based_value': pb_value,
            'ps_based_value': ps_value,

            'valuation_summary': summary
        }

    def _get_latest_fcf(self, stock_id: int) -> Optional[float]:
        """Get latest TTM or annual FCF."""
        # Try TTM first (sum of last 4 quarters)
        quarters = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == 'quarterly'
        ).order_by(desc(FinancialStatement.period_end_date)).limit(4).all()

        if len(quarters) >= 4:
            ttm_fcf = sum(q.free_cash_flow or 0 for q in quarters)
            if ttm_fcf > 0:
                return ttm_fcf

        # Fall back to latest annual
        annual = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == 'annual'
        ).order_by(desc(FinancialStatement.period_end_date)).first()

        if annual and annual.free_cash_flow:
            return annual.free_cash_flow

        return None

    def _get_latest_price(self, stock_id: int) -> Optional[float]:
        """Get most recent stock price from database."""
        price = self.db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock_id
        ).order_by(desc(DailyPrice.date)).first()

        return price.close if price else None

    def _get_shares_outstanding(self, stock_id: int) -> Optional[float]:
        """Get shares outstanding from latest financial statement."""
        stmt = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.shares_outstanding.isnot(None)
        ).order_by(desc(FinancialStatement.period_end_date)).first()

        return stmt.shares_outstanding if stmt else None

    def _get_net_debt(self, stock_id: int) -> float:
        """Calculate net debt (Total Debt - Cash)."""
        stmt = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id
        ).order_by(desc(FinancialStatement.period_end_date)).first()

        if not stmt:
            return 0

        total_debt = stmt.total_debt or 0
        cash = stmt.cash_and_equivalents or 0

        return total_debt - cash

    def _estimate_growth_rate(self, stock_id: int) -> float:
        """Estimate future growth rate based on historical data."""
        # Get historical FCF growth
        metrics = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock_id,
            CalculatedMetrics.fcf_growth.isnot(None)
        ).order_by(desc(CalculatedMetrics.period_end_date)).limit(5).all()

        if metrics:
            avg_fcf_growth = np.mean([m.fcf_growth for m in metrics if m.fcf_growth])
            # Convert from percentage to decimal and apply margin
            return (avg_fcf_growth / 100) * 0.8  # Conservative 80% of historical

        # Fall back to revenue growth
        revenue_metrics = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock_id,
            CalculatedMetrics.revenue_growth.isnot(None)
        ).order_by(desc(CalculatedMetrics.period_end_date)).limit(5).all()

        if revenue_metrics:
            avg_revenue_growth = np.mean([m.revenue_growth for m in revenue_metrics])
            return (avg_revenue_growth / 100) * 0.7  # Even more conservative

        # Default moderate growth
        return 0.08  # 8% default

    def _estimate_wacc(self, stock_id: int) -> float:
        """Estimate Weighted Average Cost of Capital."""
        # Simplified WACC calculation
        # For a more accurate calculation, you'd need beta, debt costs, etc.

        stmt = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id
        ).order_by(desc(FinancialStatement.period_end_date)).first()

        if not stmt or not stmt.total_equity:
            return self.DEFAULT_DISCOUNT_RATE

        # Simple approach: higher debt = higher discount rate
        debt_to_equity = (stmt.total_debt or 0) / stmt.total_equity if stmt.total_equity > 0 else 0

        # Base discount rate + adjustment for leverage
        wacc = 0.08 + (debt_to_equity * 0.02)

        return min(0.15, max(0.06, wacc))  # Bound between 6% and 15%

    def _calculate_pe_based_value(
        self,
        stock_id: int,
        current_price: float,
        shares: float
    ) -> Optional[float]:
        """Calculate fair value based on P/E ratio."""
        # Get average historical P/E
        metrics = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock_id,
            CalculatedMetrics.pe_ratio.isnot(None),
            CalculatedMetrics.pe_ratio > 0,
            CalculatedMetrics.pe_ratio < 100  # Filter outliers
        ).order_by(desc(CalculatedMetrics.period_end_date)).limit(8).all()

        if not metrics:
            return None

        avg_pe = np.median([m.pe_ratio for m in metrics])

        # Get current EPS
        quarters = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == 'quarterly'
        ).order_by(desc(FinancialStatement.period_end_date)).limit(4).all()

        if len(quarters) < 4:
            return None

        ttm_earnings = sum(q.net_income or 0 for q in quarters)
        if ttm_earnings <= 0:
            return None

        eps = ttm_earnings / shares
        fair_value = eps * avg_pe

        return round(fair_value, 2)

    def _calculate_pb_based_value(
        self,
        stock_id: int,
        shares: float
    ) -> Optional[float]:
        """Calculate fair value based on P/B ratio."""
        stmt = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.total_equity.isnot(None)
        ).order_by(desc(FinancialStatement.period_end_date)).first()

        if not stmt or not stmt.total_equity or stmt.total_equity <= 0:
            return None

        # Get average historical P/B
        metrics = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock_id,
            CalculatedMetrics.pb_ratio.isnot(None),
            CalculatedMetrics.pb_ratio > 0,
            CalculatedMetrics.pb_ratio < 20
        ).order_by(desc(CalculatedMetrics.period_end_date)).limit(8).all()

        if not metrics:
            return None

        avg_pb = np.median([m.pb_ratio for m in metrics])
        book_value_per_share = stmt.total_equity / shares

        return round(book_value_per_share * avg_pb, 2)

    def _calculate_ps_based_value(
        self,
        stock_id: int,
        shares: float
    ) -> Optional[float]:
        """Calculate fair value based on P/S ratio."""
        # Get TTM revenue
        quarters = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock_id,
            FinancialStatement.period_type == 'quarterly'
        ).order_by(desc(FinancialStatement.period_end_date)).limit(4).all()

        if len(quarters) < 4:
            return None

        ttm_revenue = sum(q.revenue or 0 for q in quarters)
        if ttm_revenue <= 0:
            return None

        # Get average historical P/S
        metrics = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock_id,
            CalculatedMetrics.ps_ratio.isnot(None),
            CalculatedMetrics.ps_ratio > 0,
            CalculatedMetrics.ps_ratio < 30
        ).order_by(desc(CalculatedMetrics.period_end_date)).limit(8).all()

        if not metrics:
            return None

        avg_ps = np.median([m.ps_ratio for m in metrics])
        revenue_per_share = ttm_revenue / shares

        return round(revenue_per_share * avg_ps, 2)

    def _generate_summary(
        self,
        ticker: str,
        current_price: float,
        fair_value: float,
        margin_of_safety: float,
        valuation_status: str,
        growth_rate: float
    ) -> str:
        """Generate a human-readable valuation summary."""
        if valuation_status == "undervalued":
            return (
                f"{ticker} appears undervalued with a fair value of ${fair_value:.2f} "
                f"compared to current price of ${current_price:.2f} "
                f"(potential upside of {margin_of_safety:.1f}%). "
                f"This assumes a growth rate of {growth_rate*100:.1f}% annually."
            )
        elif valuation_status == "overvalued":
            return (
                f"{ticker} appears overvalued at ${current_price:.2f} "
                f"compared to fair value estimate of ${fair_value:.2f} "
                f"(potential downside of {abs(margin_of_safety):.1f}%). "
                f"Consider waiting for a better entry point."
            )
        else:
            return (
                f"{ticker} appears fairly valued at ${current_price:.2f} "
                f"with fair value estimate of ${fair_value:.2f}. "
                f"The stock is trading close to its intrinsic value."
            )

    def _save_valuation_metrics(
        self,
        stock_id: int,
        fair_value: float,
        margin_of_safety: float,
        valuation_status: str
    ):
        """Save valuation results to latest metrics record."""
        metrics = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock_id
        ).order_by(desc(CalculatedMetrics.period_end_date)).first()

        if metrics:
            metrics.fair_value_per_share = fair_value
            metrics.margin_of_safety = margin_of_safety
            metrics.valuation_status = valuation_status
            self.db.commit()

    def get_valuation_status(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get quick valuation status for a stock."""
        stock = self.db.query(Stock).filter(Stock.ticker == ticker.upper()).first()
        if not stock:
            return None

        metrics = self.db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock.id,
            CalculatedMetrics.fair_value_per_share.isnot(None)
        ).order_by(desc(CalculatedMetrics.period_end_date)).first()

        if not metrics:
            return None

        current_price = self.data_fetcher.get_current_price(ticker)
        if not current_price:
            current_price = self._get_latest_price(stock.id)

        return {
            'ticker': ticker.upper(),
            'current_price': current_price,
            'fair_value': metrics.fair_value_per_share,
            'margin_of_safety': metrics.margin_of_safety,
            'valuation_status': metrics.valuation_status
        }
