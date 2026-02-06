from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_
import logging

from app.models.stock import Stock
from app.models.financial import CalculatedMetrics, DailyPrice
from app.schemas.screener import ScreenerFilters, ScreenerResult

logger = logging.getLogger(__name__)


class StockScreener:
    """Service for screening stocks based on various criteria."""

    def __init__(self, db: Session):
        self.db = db

    def screen(self, filters: ScreenerFilters) -> Dict[str, Any]:
        """
        Screen stocks based on provided filters.

        Returns paginated results with applied filters.
        """
        from sqlalchemy import func

        # Subquery to get the latest period_end_date for each stock
        latest_metrics = self.db.query(
            CalculatedMetrics.stock_id,
            func.max(CalculatedMetrics.period_end_date).label('max_date')
        ).filter(
            CalculatedMetrics.period_type.in_(['ttm', 'annual'])
        ).group_by(
            CalculatedMetrics.stock_id
        ).subquery()

        # Join stocks with only their latest metrics
        query = self.db.query(Stock, CalculatedMetrics).join(
            CalculatedMetrics,
            and_(
                Stock.id == CalculatedMetrics.stock_id,
                CalculatedMetrics.period_type.in_(['ttm', 'annual'])
            )
        ).join(
            latest_metrics,
            and_(
                CalculatedMetrics.stock_id == latest_metrics.c.stock_id,
                CalculatedMetrics.period_end_date == latest_metrics.c.max_date
            )
        ).filter(
            Stock.is_active == True
        )

        # Apply filters
        query = self._apply_filters(query, filters)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        query = self._apply_sorting(query, filters)

        # Apply pagination
        offset = (filters.page - 1) * filters.per_page
        query = query.offset(offset).limit(filters.per_page)

        # Execute query
        results = query.all()

        # Format results
        formatted_results = []
        for stock, metrics in results:
            # Get current price
            current_price = self._get_current_price(stock.id)

            formatted_results.append(ScreenerResult(
                id=stock.id,
                ticker=stock.ticker,
                name=stock.name,
                sector=stock.sector,
                industry=stock.industry,
                exchange=stock.exchange,
                market_cap=stock.market_cap,
                current_price=current_price,
                pe_ratio=metrics.pe_ratio,
                pb_ratio=metrics.pb_ratio,
                roe=metrics.roe,
                roce=metrics.roce,
                net_profit_margin=metrics.net_profit_margin,
                fcf_yield=metrics.fcf_yield,
                revenue_growth=metrics.revenue_growth,
                debt_to_equity=metrics.debt_to_equity,
                fair_value_per_share=metrics.fair_value_per_share,
                margin_of_safety=metrics.margin_of_safety,
                valuation_status=metrics.valuation_status,
            ))

        return {
            'results': formatted_results,
            'total': total,
            'page': filters.page,
            'per_page': filters.per_page,
            'filters_applied': filters.model_dump(exclude_none=True)
        }

    def _apply_filters(self, query, filters: ScreenerFilters):
        """Apply all filters to the query."""
        # Market Cap filters (convert from billions to actual)
        if filters.min_market_cap is not None:
            query = query.filter(Stock.market_cap >= filters.min_market_cap * 1_000_000_000)
        if filters.max_market_cap is not None:
            query = query.filter(Stock.market_cap <= filters.max_market_cap * 1_000_000_000)

        # Sector/Industry filters
        if filters.sectors:
            query = query.filter(Stock.sector.in_(filters.sectors))
        if filters.industries:
            query = query.filter(Stock.industry.in_(filters.industries))
        if filters.exchanges:
            query = query.filter(Stock.exchange.in_(filters.exchanges))

        # Profitability filters
        if filters.min_gross_margin is not None:
            query = query.filter(CalculatedMetrics.gross_margin >= filters.min_gross_margin)
        if filters.min_operating_margin is not None:
            query = query.filter(CalculatedMetrics.operating_margin >= filters.min_operating_margin)
        if filters.min_net_margin is not None:
            query = query.filter(CalculatedMetrics.net_profit_margin >= filters.min_net_margin)
        if filters.min_roe is not None:
            query = query.filter(CalculatedMetrics.roe >= filters.min_roe)
        if filters.min_roce is not None:
            query = query.filter(CalculatedMetrics.roce >= filters.min_roce)

        # Cash flow filters
        if filters.min_fcf_margin is not None:
            query = query.filter(CalculatedMetrics.fcf_margin >= filters.min_fcf_margin)
        if filters.min_fcf_yield is not None:
            query = query.filter(CalculatedMetrics.fcf_yield >= filters.min_fcf_yield)
        if filters.positive_fcf_only:
            query = query.filter(CalculatedMetrics.fcf_margin > 0)

        # Growth filters
        if filters.min_revenue_growth is not None:
            query = query.filter(CalculatedMetrics.revenue_growth >= filters.min_revenue_growth)
        if filters.min_eps_growth is not None:
            query = query.filter(CalculatedMetrics.eps_growth >= filters.min_eps_growth)

        # Valuation filters
        if filters.min_pe_ratio is not None:
            query = query.filter(CalculatedMetrics.pe_ratio >= filters.min_pe_ratio)
        if filters.max_pe_ratio is not None:
            query = query.filter(CalculatedMetrics.pe_ratio <= filters.max_pe_ratio)
        if filters.max_pb_ratio is not None:
            query = query.filter(CalculatedMetrics.pb_ratio <= filters.max_pb_ratio)
        if filters.max_ps_ratio is not None:
            query = query.filter(CalculatedMetrics.ps_ratio <= filters.max_ps_ratio)
        if filters.max_price_to_fcf is not None:
            query = query.filter(CalculatedMetrics.price_to_fcf <= filters.max_price_to_fcf)
        if filters.max_peg_ratio is not None:
            query = query.filter(CalculatedMetrics.peg_ratio <= filters.max_peg_ratio)

        # Leverage filters
        if filters.max_debt_to_equity is not None:
            query = query.filter(CalculatedMetrics.debt_to_equity <= filters.max_debt_to_equity)
        if filters.min_current_ratio is not None:
            query = query.filter(CalculatedMetrics.current_ratio >= filters.min_current_ratio)

        # Valuation status filter
        if filters.valuation_status:
            query = query.filter(CalculatedMetrics.valuation_status == filters.valuation_status)
        if filters.min_margin_of_safety is not None:
            query = query.filter(CalculatedMetrics.margin_of_safety >= filters.min_margin_of_safety)

        return query

    def _apply_sorting(self, query, filters: ScreenerFilters):
        """Apply sorting to the query."""
        sort_mapping = {
            'market_cap': Stock.market_cap,
            'ticker': Stock.ticker,
            'name': Stock.name,
            'pe_ratio': CalculatedMetrics.pe_ratio,
            'pb_ratio': CalculatedMetrics.pb_ratio,
            'roe': CalculatedMetrics.roe,
            'roce': CalculatedMetrics.roce,
            'net_profit_margin': CalculatedMetrics.net_profit_margin,
            'fcf_yield': CalculatedMetrics.fcf_yield,
            'revenue_growth': CalculatedMetrics.revenue_growth,
            'margin_of_safety': CalculatedMetrics.margin_of_safety,
        }

        sort_column = sort_mapping.get(filters.sort_by, Stock.market_cap)

        if filters.sort_order == 'asc':
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        return query

    def _get_current_price(self, stock_id: int) -> Optional[float]:
        """Get the most recent price for a stock."""
        price = self.db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock_id
        ).order_by(desc(DailyPrice.date)).first()

        return price.close if price else None

    def get_sectors(self) -> List[str]:
        """Get all unique sectors."""
        sectors = self.db.query(Stock.sector).filter(
            Stock.sector.isnot(None),
            Stock.is_active == True
        ).distinct().all()

        return sorted([s[0] for s in sectors if s[0]])

    def get_industries(self, sector: Optional[str] = None) -> List[str]:
        """Get all unique industries, optionally filtered by sector."""
        query = self.db.query(Stock.industry).filter(
            Stock.industry.isnot(None),
            Stock.is_active == True
        )

        if sector:
            query = query.filter(Stock.sector == sector)

        industries = query.distinct().all()

        return sorted([i[0] for i in industries if i[0]])

    def get_exchanges(self) -> List[str]:
        """Get all unique exchanges."""
        exchanges = self.db.query(Stock.exchange).filter(
            Stock.exchange.isnot(None),
            Stock.is_active == True
        ).distinct().all()

        return sorted([e[0] for e in exchanges if e[0]])

    def get_top_stocks(
        self,
        metric: str = 'margin_of_safety',
        limit: int = 10
    ) -> List[ScreenerResult]:
        """Get top stocks by a specific metric."""
        filters = ScreenerFilters(
            sort_by=metric,
            sort_order='desc',
            per_page=limit
        )

        result = self.screen(filters)
        return result['results']

    def find_undervalued(self, min_margin: float = 20) -> List[ScreenerResult]:
        """Find undervalued stocks with minimum margin of safety."""
        # First try to find stocks with actual valuation data
        filters = ScreenerFilters(
            valuation_status='undervalued',
            min_margin_of_safety=min_margin,
            sort_by='margin_of_safety',
            sort_order='desc',
            per_page=50
        )

        result = self.screen(filters)

        # If no undervalued stocks found (no price data), return empty list
        # Don't mislead users with random stocks
        return result['results']

    def find_quality_stocks(self) -> List[ScreenerResult]:
        """Find high-quality stocks based on fundamentals."""
        filters = ScreenerFilters(
            min_roe=15,
            # min_roce=12,  # Disabled - not all data sources provide ROCE
            min_net_margin=10,
            # positive_fcf_only=True,  # Disabled - not all stocks have FCF data
            max_debt_to_equity=1.0,
            sort_by='roe',
            sort_order='desc',
            per_page=50
        )

        result = self.screen(filters)
        return result['results']

    def find_growth_stocks(self) -> List[ScreenerResult]:
        """Find stocks with strong revenue and earnings growth."""
        filters = ScreenerFilters(
            min_revenue_growth=10,
            # min_eps_growth=10,  # Disabled - not always available
            # positive_fcf_only=True,  # Disabled - not all stocks have FCF data
            sort_by='revenue_growth',
            sort_order='desc',
            per_page=50
        )

        result = self.screen(filters)
        return result['results']
