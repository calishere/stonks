from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.stock import Stock
from app.models.financial import DailyPrice
from app.models.portfolio import Watchlist
from app.schemas.portfolio import WatchlistAdd, WatchlistResponse

router = APIRouter()


@router.get("/", response_model=List[WatchlistResponse])
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's watchlist."""
    watchlist_items = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id
    ).order_by(desc(Watchlist.added_at)).all()

    result = []
    for item in watchlist_items:
        stock = db.query(Stock).filter(Stock.id == item.stock_id).first()

        # Get current price
        latest_price = db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock.id
        ).order_by(desc(DailyPrice.date)).first()

        result.append(WatchlistResponse(
            id=item.id,
            stock_id=stock.id,
            ticker=stock.ticker,
            name=stock.name,
            sector=stock.sector,
            current_price=latest_price.close if latest_price else None,
            market_cap=stock.market_cap,
            added_at=item.added_at
        ))

    return result


@router.post("/", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    data: WatchlistAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a stock to watchlist."""
    stock = db.query(Stock).filter(Stock.ticker == data.ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Check if already in watchlist
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.stock_id == stock.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock already in watchlist"
        )

    watchlist_item = Watchlist(
        user_id=current_user.id,
        stock_id=stock.id
    )
    db.add(watchlist_item)
    db.commit()
    db.refresh(watchlist_item)

    # Get current price
    latest_price = db.query(DailyPrice).filter(
        DailyPrice.stock_id == stock.id
    ).order_by(desc(DailyPrice.date)).first()

    return WatchlistResponse(
        id=watchlist_item.id,
        stock_id=stock.id,
        ticker=stock.ticker,
        name=stock.name,
        sector=stock.sector,
        current_price=latest_price.close if latest_price else None,
        market_cap=stock.market_cap,
        added_at=watchlist_item.added_at
    )


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a stock from watchlist."""
    stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    watchlist_item = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.stock_id == stock.id
    ).first()

    if not watchlist_item:
        raise HTTPException(status_code=404, detail="Stock not in watchlist")

    db.delete(watchlist_item)
    db.commit()

    return None
