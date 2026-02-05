from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class FinancialStatement(Base):
    """Stores quarterly and annual financial data."""
    __tablename__ = "financial_statements"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    period_type = Column(String(10), nullable=False)  # 'quarterly' or 'annual'
    period_end_date = Column(Date, nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer, nullable=True)  # 1-4 for quarterly, null for annual

    # Income Statement
    revenue = Column(Float, nullable=True)
    cost_of_revenue = Column(Float, nullable=True)
    gross_profit = Column(Float, nullable=True)
    operating_income = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)
    ebitda = Column(Float, nullable=True)
    ebit = Column(Float, nullable=True)

    # Balance Sheet
    total_assets = Column(Float, nullable=True)
    total_liabilities = Column(Float, nullable=True)
    total_equity = Column(Float, nullable=True)
    current_assets = Column(Float, nullable=True)
    current_liabilities = Column(Float, nullable=True)
    total_debt = Column(Float, nullable=True)
    cash_and_equivalents = Column(Float, nullable=True)

    # Cash Flow Statement
    operating_cash_flow = Column(Float, nullable=True)
    capital_expenditure = Column(Float, nullable=True)
    free_cash_flow = Column(Float, nullable=True)
    dividends_paid = Column(Float, nullable=True)

    # Per Share Data
    earnings_per_share = Column(Float, nullable=True)
    book_value_per_share = Column(Float, nullable=True)
    shares_outstanding = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    stock = relationship("Stock", back_populates="financial_statements")

    __table_args__ = (
        UniqueConstraint('stock_id', 'period_type', 'period_end_date', name='uq_financial_statement'),
    )


class DailyPrice(Base):
    """Stores daily price data for stocks."""
    __tablename__ = "daily_prices"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    adjusted_close = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    stock = relationship("Stock", back_populates="daily_prices")

    __table_args__ = (
        UniqueConstraint('stock_id', 'date', name='uq_daily_price'),
    )


class CalculatedMetrics(Base):
    """Stores calculated financial metrics for analysis."""
    __tablename__ = "calculated_metrics"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    period_type = Column(String(10), nullable=False)  # 'quarterly', 'annual', 'ttm'
    period_end_date = Column(Date, nullable=False, index=True)

    # Profitability Metrics
    gross_margin = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)
    net_profit_margin = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)  # Return on Equity
    roce = Column(Float, nullable=True)  # Return on Capital Employed
    roa = Column(Float, nullable=True)  # Return on Assets

    # Cash Flow Metrics
    fcf_margin = Column(Float, nullable=True)  # FCF / Revenue
    fcf_yield = Column(Float, nullable=True)  # FCF / Market Cap
    operating_cash_flow_margin = Column(Float, nullable=True)

    # Growth Metrics (YoY)
    revenue_growth = Column(Float, nullable=True)
    net_income_growth = Column(Float, nullable=True)
    fcf_growth = Column(Float, nullable=True)
    eps_growth = Column(Float, nullable=True)

    # Valuation Metrics
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)  # Price to Book
    ps_ratio = Column(Float, nullable=True)  # Price to Sales
    price_to_fcf = Column(Float, nullable=True)
    ev_to_ebitda = Column(Float, nullable=True)
    peg_ratio = Column(Float, nullable=True)

    # Leverage Metrics
    debt_to_equity = Column(Float, nullable=True)
    current_ratio = Column(Float, nullable=True)
    interest_coverage = Column(Float, nullable=True)

    # DCF Valuation
    dcf_value = Column(Float, nullable=True)
    fair_value_per_share = Column(Float, nullable=True)
    margin_of_safety = Column(Float, nullable=True)  # % difference from current price
    valuation_status = Column(String(20), nullable=True)  # 'undervalued', 'overvalued', 'fair'

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    stock = relationship("Stock", back_populates="calculated_metrics")

    __table_args__ = (
        UniqueConstraint('stock_id', 'period_type', 'period_end_date', name='uq_calculated_metrics'),
    )
