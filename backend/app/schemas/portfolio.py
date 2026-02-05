from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class WatchlistAdd(BaseModel):
    ticker: str


class WatchlistResponse(BaseModel):
    id: int
    stock_id: int
    ticker: str
    name: str
    sector: Optional[str] = None
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    added_at: datetime

    class Config:
        from_attributes = True


class PortfolioAdd(BaseModel):
    ticker: str
    shares: float
    average_cost: float


class PortfolioUpdate(BaseModel):
    shares: Optional[float] = None
    average_cost: Optional[float] = None


class PortfolioResponse(BaseModel):
    id: int
    stock_id: int
    ticker: str
    name: str
    shares: float
    average_cost: float
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_percent: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    positions: List[PortfolioResponse]
    total_cost: float
    total_value: float
    total_gain_loss: float
    total_gain_loss_percent: float
