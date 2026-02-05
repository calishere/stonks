from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.valuation import DCFInput, ValuationResponse
from app.services.valuation_engine import ValuationEngine

router = APIRouter()


@router.get("/{ticker}", response_model=ValuationResponse)
async def get_valuation(
    ticker: str,
    db: Session = Depends(get_db)
):
    """Get DCF valuation for a stock using default assumptions."""
    engine = ValuationEngine(db)
    result = engine.calculate_dcf(ticker)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Could not calculate valuation. Stock may not have sufficient data."
        )

    return result


@router.post("/{ticker}", response_model=ValuationResponse)
async def calculate_custom_valuation(
    ticker: str,
    inputs: DCFInput,
    db: Session = Depends(get_db)
):
    """Calculate DCF valuation with custom inputs."""
    engine = ValuationEngine(db)
    result = engine.calculate_dcf(
        ticker=ticker,
        growth_rate=inputs.growth_rate,
        discount_rate=inputs.discount_rate,
        terminal_growth_rate=inputs.terminal_growth_rate,
        projection_years=inputs.projection_years
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Could not calculate valuation. Stock may not have sufficient data."
        )

    return result


@router.get("/{ticker}/status")
async def get_valuation_status(
    ticker: str,
    db: Session = Depends(get_db)
):
    """Get quick valuation status for a stock."""
    engine = ValuationEngine(db)
    result = engine.get_valuation_status(ticker)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Valuation not available for this stock"
        )

    return result
