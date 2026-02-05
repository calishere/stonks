from pydantic import BaseModel
from typing import Optional, List


class DCFInput(BaseModel):
    """Custom inputs for DCF calculation."""
    growth_rate: Optional[float] = None  # Override estimated growth rate
    discount_rate: Optional[float] = None  # Override WACC
    terminal_growth_rate: Optional[float] = 0.03  # Perpetual growth rate (default 3%)
    projection_years: int = 10


class DCFProjection(BaseModel):
    """Year-by-year DCF projection."""
    year: int
    projected_fcf: float
    discount_factor: float
    present_value: float


class ValuationResponse(BaseModel):
    """Complete valuation analysis for a stock."""
    ticker: str
    name: str
    current_price: float
    shares_outstanding: float
    market_cap: float

    # DCF Analysis
    latest_fcf: float
    estimated_growth_rate: float
    discount_rate: float
    terminal_growth_rate: float
    projection_years: int

    # DCF Projections
    projections: List[DCFProjection]
    terminal_value: float
    terminal_value_pv: float

    # Fair Value
    enterprise_value: float
    equity_value: float
    fair_value_per_share: float

    # Comparison
    upside_downside: float  # % difference from current price
    margin_of_safety: float
    valuation_status: str  # undervalued, overvalued, fair

    # Multiple-Based Valuations for comparison
    pe_based_value: Optional[float] = None
    pb_based_value: Optional[float] = None
    ps_based_value: Optional[float] = None

    # Summary
    valuation_summary: str  # Human-readable summary
