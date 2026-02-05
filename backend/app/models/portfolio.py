from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Watchlist(Base):
    """User's stock watchlist."""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Integer, nullable=True)  # Optional user notes

    # Relationships
    user = relationship("User", back_populates="watchlist")
    stock = relationship("Stock", back_populates="watchlist_items")

    __table_args__ = (
        UniqueConstraint('user_id', 'stock_id', name='uq_watchlist'),
    )


class Portfolio(Base):
    """User's stock portfolio with positions."""
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    shares = Column(Float, nullable=False)
    average_cost = Column(Float, nullable=False)  # Average cost per share
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="portfolio")
    stock = relationship("Stock", back_populates="portfolio_items")

    __table_args__ = (
        UniqueConstraint('user_id', 'stock_id', name='uq_portfolio'),
    )
