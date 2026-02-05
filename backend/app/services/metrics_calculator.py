from typing import Optional, List, Dict, Any
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from app.models.stock import Stock
from app.models.financial import FinancialStatement, DailyPrice, CalculatedMetrics

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Service for calculating financial metrics."""

    def __init__(self, db: Session):
        self.db = db

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

        return metrics

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
