from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.stock import Stock
from app.models.financial import DailyPrice
from app.models.portfolio import Portfolio
from app.schemas.portfolio import (
    PortfolioAdd,
    PortfolioUpdate,
    PortfolioResponse,
    PortfolioSummary,
)

router = APIRouter()


@router.get("/", response_model=PortfolioSummary)
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's portfolio with summary."""
    positions = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id
    ).all()

    result = []
    total_cost = 0
    total_value = 0

    for position in positions:
        stock = db.query(Stock).filter(Stock.id == position.stock_id).first()

        # Get current price
        latest_price = db.query(DailyPrice).filter(
            DailyPrice.stock_id == stock.id
        ).order_by(desc(DailyPrice.date)).first()

        current_price = latest_price.close if latest_price else position.average_cost
        cost_basis = position.shares * position.average_cost
        current_value = position.shares * current_price
        gain_loss = current_value - cost_basis
        gain_loss_percent = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0

        total_cost += cost_basis
        total_value += current_value

        result.append(PortfolioResponse(
            id=position.id,
            stock_id=stock.id,
            ticker=stock.ticker,
            name=stock.name,
            shares=position.shares,
            average_cost=position.average_cost,
            current_price=current_price,
            current_value=round(current_value, 2),
            gain_loss=round(gain_loss, 2),
            gain_loss_percent=round(gain_loss_percent, 2),
            created_at=position.created_at
        ))

    total_gain_loss = total_value - total_cost
    total_gain_loss_percent = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0

    return PortfolioSummary(
        positions=result,
        total_cost=round(total_cost, 2),
        total_value=round(total_value, 2),
        total_gain_loss=round(total_gain_loss, 2),
        total_gain_loss_percent=round(total_gain_loss_percent, 2)
    )


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def add_position(
    data: PortfolioAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new position to portfolio."""
    stock = db.query(Stock).filter(Stock.ticker == data.ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Check if position already exists
    existing = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.stock_id == stock.id
    ).first()

    if existing:
        # Update existing position (average down/up)
        total_shares = existing.shares + data.shares
        total_cost = (existing.shares * existing.average_cost) + (data.shares * data.average_cost)
        new_average = total_cost / total_shares

        existing.shares = total_shares
        existing.average_cost = new_average
        db.commit()
        db.refresh(existing)
        position = existing
    else:
        # Create new position
        position = Portfolio(
            user_id=current_user.id,
            stock_id=stock.id,
            shares=data.shares,
            average_cost=data.average_cost
        )
        db.add(position)
        db.commit()
        db.refresh(position)

    # Get current price
    latest_price = db.query(DailyPrice).filter(
        DailyPrice.stock_id == stock.id
    ).order_by(desc(DailyPrice.date)).first()

    current_price = latest_price.close if latest_price else position.average_cost
    current_value = position.shares * current_price
    cost_basis = position.shares * position.average_cost
    gain_loss = current_value - cost_basis
    gain_loss_percent = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0

    return PortfolioResponse(
        id=position.id,
        stock_id=stock.id,
        ticker=stock.ticker,
        name=stock.name,
        shares=position.shares,
        average_cost=position.average_cost,
        current_price=current_price,
        current_value=round(current_value, 2),
        gain_loss=round(gain_loss, 2),
        gain_loss_percent=round(gain_loss_percent, 2),
        created_at=position.created_at
    )


@router.put("/{ticker}", response_model=PortfolioResponse)
async def update_position(
    ticker: str,
    data: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a portfolio position."""
    stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    position = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.stock_id == stock.id
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    if data.shares is not None:
        position.shares = data.shares
    if data.average_cost is not None:
        position.average_cost = data.average_cost

    db.commit()
    db.refresh(position)

    # Get current price
    latest_price = db.query(DailyPrice).filter(
        DailyPrice.stock_id == stock.id
    ).order_by(desc(DailyPrice.date)).first()

    current_price = latest_price.close if latest_price else position.average_cost
    current_value = position.shares * current_price
    cost_basis = position.shares * position.average_cost
    gain_loss = current_value - cost_basis
    gain_loss_percent = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0

    return PortfolioResponse(
        id=position.id,
        stock_id=stock.id,
        ticker=stock.ticker,
        name=stock.name,
        shares=position.shares,
        average_cost=position.average_cost,
        current_price=current_price,
        current_value=round(current_value, 2),
        gain_loss=round(gain_loss, 2),
        gain_loss_percent=round(gain_loss_percent, 2),
        created_at=position.created_at
    )


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_position(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a position from portfolio."""
    stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    position = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.stock_id == stock.id
    ).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    db.delete(position)
    db.commit()

    return None
