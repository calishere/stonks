from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.screener import ScreenerFilters, ScreenerResult
from app.services.screener import StockScreener

router = APIRouter()


@router.post("/", response_model=dict)
async def screen_stocks(
    filters: ScreenerFilters,
    db: Session = Depends(get_db)
):
    """Screen stocks based on filters."""
    screener = StockScreener(db)
    return screener.screen(filters)


@router.get("/sectors", response_model=List[str])
async def get_sectors(db: Session = Depends(get_db)):
    """Get all available sectors."""
    screener = StockScreener(db)
    return screener.get_sectors()


@router.get("/industries", response_model=List[str])
async def get_industries(
    sector: str = None,
    db: Session = Depends(get_db)
):
    """Get all available industries, optionally filtered by sector."""
    screener = StockScreener(db)
    return screener.get_industries(sector)


@router.get("/exchanges", response_model=List[str])
async def get_exchanges(db: Session = Depends(get_db)):
    """Get all available exchanges."""
    screener = StockScreener(db)
    return screener.get_exchanges()


@router.get("/top/{metric}", response_model=List[ScreenerResult])
async def get_top_stocks(
    metric: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get top stocks by a specific metric."""
    screener = StockScreener(db)
    return screener.get_top_stocks(metric, limit)


@router.get("/undervalued", response_model=List[ScreenerResult])
async def find_undervalued(
    min_margin: float = 20,
    db: Session = Depends(get_db)
):
    """Find undervalued stocks."""
    screener = StockScreener(db)
    return screener.find_undervalued(min_margin)


@router.get("/quality", response_model=List[ScreenerResult])
async def find_quality_stocks(db: Session = Depends(get_db)):
    """Find high-quality stocks based on fundamentals."""
    screener = StockScreener(db)
    return screener.find_quality_stocks()


@router.get("/growth", response_model=List[ScreenerResult])
async def find_growth_stocks(db: Session = Depends(get_db)):
    """Find stocks with strong growth."""
    screener = StockScreener(db)
    return screener.find_growth_stocks()
