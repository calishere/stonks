from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    exchange = Column(String(20), nullable=True)  # NASDAQ, NYSE
    market_cap = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    financial_statements = relationship("FinancialStatement", back_populates="stock", cascade="all, delete-orphan")
    daily_prices = relationship("DailyPrice", back_populates="stock", cascade="all, delete-orphan")
    calculated_metrics = relationship("CalculatedMetrics", back_populates="stock", cascade="all, delete-orphan")
    watchlist_items = relationship("Watchlist", back_populates="stock", cascade="all, delete-orphan")
    portfolio_items = relationship("Portfolio", back_populates="stock", cascade="all, delete-orphan")
