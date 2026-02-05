from pydantic import BaseModel
from typing import Optional, List


class ScreenerFilters(BaseModel):
    """Filters for stock screening."""
    # Market Cap
    min_market_cap: Optional[float] = None  # in billions
    max_market_cap: Optional[float] = None

    # Sector/Industry
    sectors: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    exchanges: Optional[List[str]] = None  # NASDAQ, NYSE

    # Profitability
    min_gross_margin: Optional[float] = None
    min_operating_margin: Optional[float] = None
    min_net_margin: Optional[float] = None
    min_roe: Optional[float] = None
    min_roce: Optional[float] = None

    # Cash Flow
    min_fcf_margin: Optional[float] = None
    min_fcf_yield: Optional[float] = None
    positive_fcf_only: bool = False

    # Growth
    min_revenue_growth: Optional[float] = None
    min_eps_growth: Optional[float] = None

    # Valuation
    max_pe_ratio: Optional[float] = None
    min_pe_ratio: Optional[float] = None
    max_pb_ratio: Optional[float] = None
    max_ps_ratio: Optional[float] = None
    max_price_to_fcf: Optional[float] = None
    max_peg_ratio: Optional[float] = None

    # Leverage
    max_debt_to_equity: Optional[float] = None
    min_current_ratio: Optional[float] = None

    # Valuation Status
    valuation_status: Optional[str] = None  # undervalued, overvalued, fair
    min_margin_of_safety: Optional[float] = None

    # Sorting
    sort_by: str = "market_cap"
    sort_order: str = "desc"  # asc or desc

    # Pagination
    page: int = 1
    per_page: int = 50


class ScreenerResult(BaseModel):
    """Single stock result from screener."""
    id: int
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = None
    current_price: Optional[float] = None

    # Key Metrics
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    roce: Optional[float] = None
    net_profit_margin: Optional[float] = None
    fcf_yield: Optional[float] = None
    revenue_growth: Optional[float] = None
    debt_to_equity: Optional[float] = None

    # Valuation
    fair_value_per_share: Optional[float] = None
    margin_of_safety: Optional[float] = None
    valuation_status: Optional[str] = None

    class Config:
        from_attributes = True


class ScreenerResponse(BaseModel):
    results: List[ScreenerResult]
    total: int
    page: int
    per_page: int
    filters_applied: dict
