from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class StockBase(BaseModel):
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = None


class StockResponse(StockBase):
    id: int
    currency: str
    is_active: bool
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True


class StockDetailResponse(StockResponse):
    """Extended stock response with latest metrics."""
    current_price: Optional[float] = None

    # Latest metrics
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None

    # Profitability
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_profit_margin: Optional[float] = None
    roe: Optional[float] = None
    roce: Optional[float] = None

    # Cash flow
    free_cash_flow: Optional[float] = None
    fcf_margin: Optional[float] = None
    fcf_yield: Optional[float] = None

    # Growth
    revenue_growth: Optional[float] = None
    eps_growth: Optional[float] = None

    # Valuation
    fair_value_per_share: Optional[float] = None
    margin_of_safety: Optional[float] = None
    valuation_status: Optional[str] = None  # undervalued, overvalued, fair


class StockListResponse(BaseModel):
    stocks: List[StockResponse]
    total: int
    page: int
    per_page: int
