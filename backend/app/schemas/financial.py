from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class FinancialStatementResponse(BaseModel):
    id: int
    stock_id: int
    period_type: str
    period_end_date: date
    fiscal_year: int
    fiscal_quarter: Optional[int] = None

    # Income Statement
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None

    # Balance Sheet
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    total_debt: Optional[float] = None
    cash_and_equivalents: Optional[float] = None

    # Cash Flow
    operating_cash_flow: Optional[float] = None
    capital_expenditure: Optional[float] = None
    free_cash_flow: Optional[float] = None

    # Per Share
    earnings_per_share: Optional[float] = None
    shares_outstanding: Optional[float] = None

    class Config:
        from_attributes = True


class DailyPriceResponse(BaseModel):
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[float] = None

    class Config:
        from_attributes = True


class MetricsResponse(BaseModel):
    stock_id: int
    period_type: str
    period_end_date: date

    # Profitability
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_profit_margin: Optional[float] = None
    roe: Optional[float] = None
    roce: Optional[float] = None
    roa: Optional[float] = None

    # Cash Flow
    fcf_margin: Optional[float] = None
    fcf_yield: Optional[float] = None

    # Growth
    revenue_growth: Optional[float] = None
    net_income_growth: Optional[float] = None
    fcf_growth: Optional[float] = None
    eps_growth: Optional[float] = None

    # Valuation
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    price_to_fcf: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    peg_ratio: Optional[float] = None

    # Leverage
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None

    # DCF
    fair_value_per_share: Optional[float] = None
    margin_of_safety: Optional[float] = None
    valuation_status: Optional[str] = None

    class Config:
        from_attributes = True


class HistoricalMetricPoint(BaseModel):
    """Single data point for historical charts."""
    period_end_date: date
    fiscal_year: int
    fiscal_quarter: Optional[int] = None
    value: Optional[float] = None


class HistoricalDataResponse(BaseModel):
    """Response for historical chart data."""
    ticker: str
    metric_name: str
    period_type: str  # quarterly or annual
    data: List[HistoricalMetricPoint]
