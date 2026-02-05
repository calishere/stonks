from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional

from app.core.database import get_db
from app.models.stock import Stock
from app.models.financial import FinancialStatement, DailyPrice, CalculatedMetrics
from app.schemas.stock import StockResponse, StockDetailResponse, StockListResponse
from app.schemas.financial import (
    FinancialStatementResponse,
    DailyPriceResponse,
    MetricsResponse,
    HistoricalDataResponse,
    HistoricalMetricPoint,
)
from app.services.data_fetcher import DataFetcher
from app.services.metrics_calculator import MetricsCalculator

router = APIRouter()


@router.get("/", response_model=StockListResponse)
async def list_stocks(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    sector: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all stocks with pagination."""
    query = db.query(Stock).filter(Stock.is_active == True)

    if sector:
        query = query.filter(Stock.sector == sector)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Stock.ticker.ilike(search_term)) |
            (Stock.name.ilike(search_term))
        )

    total = query.count()

    stocks = query.order_by(desc(Stock.market_cap)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return StockListResponse(
        stocks=stocks,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{ticker}", response_model=StockDetailResponse)
async def get_stock(ticker: str, db: Session = Depends(get_db)):
    """Get detailed stock information including latest metrics."""
    stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Get latest metrics
    metrics = db.query(CalculatedMetrics).filter(
        CalculatedMetrics.stock_id == stock.id
    ).order_by(desc(CalculatedMetrics.period_end_date)).first()

    # Get latest price
    latest_price = db.query(DailyPrice).filter(
        DailyPrice.stock_id == stock.id
    ).order_by(desc(DailyPrice.date)).first()

    # Get latest FCF
    latest_stmt = db.query(FinancialStatement).filter(
        FinancialStatement.stock_id == stock.id
    ).order_by(desc(FinancialStatement.period_end_date)).first()

    response = StockDetailResponse(
        id=stock.id,
        ticker=stock.ticker,
        name=stock.name,
        sector=stock.sector,
        industry=stock.industry,
        exchange=stock.exchange,
        market_cap=stock.market_cap,
        currency=stock.currency,
        is_active=stock.is_active,
        last_updated=stock.last_updated,
        current_price=latest_price.close if latest_price else None,
    )

    if metrics:
        response.pe_ratio = metrics.pe_ratio
        response.pb_ratio = metrics.pb_ratio
        response.ps_ratio = metrics.ps_ratio
        response.gross_margin = metrics.gross_margin
        response.operating_margin = metrics.operating_margin
        response.net_profit_margin = metrics.net_profit_margin
        response.roe = metrics.roe
        response.roce = metrics.roce
        response.fcf_margin = metrics.fcf_margin
        response.fcf_yield = metrics.fcf_yield
        response.revenue_growth = metrics.revenue_growth
        response.eps_growth = metrics.eps_growth
        response.fair_value_per_share = metrics.fair_value_per_share
        response.margin_of_safety = metrics.margin_of_safety
        response.valuation_status = metrics.valuation_status

    if latest_stmt:
        response.free_cash_flow = latest_stmt.free_cash_flow

    return response


@router.get("/{ticker}/financials", response_model=List[FinancialStatementResponse])
async def get_financials(
    ticker: str,
    period_type: str = Query("quarterly", regex="^(quarterly|annual)$"),
    limit: int = Query(12, ge=1, le=40),
    db: Session = Depends(get_db)
):
    """Get financial statements for a stock."""
    stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    statements = db.query(FinancialStatement).filter(
        FinancialStatement.stock_id == stock.id,
        FinancialStatement.period_type == period_type
    ).order_by(desc(FinancialStatement.period_end_date)).limit(limit).all()

    return statements


@router.get("/{ticker}/prices", response_model=List[DailyPriceResponse])
async def get_prices(
    ticker: str,
    days: int = Query(365, ge=1, le=3650),
    db: Session = Depends(get_db)
):
    """Get historical prices for a stock."""
    stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    prices = db.query(DailyPrice).filter(
        DailyPrice.stock_id == stock.id
    ).order_by(desc(DailyPrice.date)).limit(days).all()

    return list(reversed(prices))


@router.get("/{ticker}/metrics", response_model=List[MetricsResponse])
async def get_metrics(
    ticker: str,
    period_type: str = Query("quarterly", regex="^(quarterly|annual|ttm)$"),
    limit: int = Query(12, ge=1, le=40),
    db: Session = Depends(get_db)
):
    """Get calculated metrics for a stock."""
    stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    metrics = db.query(CalculatedMetrics).filter(
        CalculatedMetrics.stock_id == stock.id,
        CalculatedMetrics.period_type == period_type
    ).order_by(desc(CalculatedMetrics.period_end_date)).limit(limit).all()

    return metrics


@router.get("/{ticker}/history/{metric}", response_model=HistoricalDataResponse)
async def get_metric_history(
    ticker: str,
    metric: str,
    period_type: str = Query("quarterly", regex="^(quarterly|annual)$"),
    limit: int = Query(20, ge=1, le=40),
    db: Session = Depends(get_db)
):
    """Get historical data for a specific metric (for charts)."""
    stock = db.query(Stock).filter(Stock.ticker == ticker.upper()).first()

    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Valid metrics
    valid_metrics = [
        'revenue', 'net_income', 'free_cash_flow', 'gross_profit', 'operating_income',
        'gross_margin', 'operating_margin', 'net_profit_margin',
        'roe', 'roce', 'roa', 'fcf_margin', 'fcf_yield',
        'revenue_growth', 'eps_growth', 'fcf_growth',
        'pe_ratio', 'pb_ratio', 'ps_ratio', 'debt_to_equity',
    ]

    if metric not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric. Valid options: {', '.join(valid_metrics)}"
        )

    # Check if metric is from FinancialStatement or CalculatedMetrics
    financial_metrics = ['revenue', 'net_income', 'free_cash_flow', 'gross_profit', 'operating_income']

    data_points = []

    if metric in financial_metrics:
        statements = db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock.id,
            FinancialStatement.period_type == period_type
        ).order_by(FinancialStatement.period_end_date).limit(limit).all()

        for stmt in statements:
            value = getattr(stmt, metric, None)
            if value is not None:
                data_points.append(HistoricalMetricPoint(
                    period_end_date=stmt.period_end_date,
                    fiscal_year=stmt.fiscal_year,
                    fiscal_quarter=stmt.fiscal_quarter,
                    value=value
                ))
    else:
        calc_metrics = db.query(CalculatedMetrics).filter(
            CalculatedMetrics.stock_id == stock.id,
            CalculatedMetrics.period_type == period_type
        ).order_by(CalculatedMetrics.period_end_date).limit(limit).all()

        for m in calc_metrics:
            value = getattr(m, metric, None)
            if value is not None:
                # Get fiscal info
                stmt = db.query(FinancialStatement).filter(
                    FinancialStatement.stock_id == stock.id,
                    FinancialStatement.period_type == period_type,
                    FinancialStatement.period_end_date == m.period_end_date
                ).first()

                data_points.append(HistoricalMetricPoint(
                    period_end_date=m.period_end_date,
                    fiscal_year=stmt.fiscal_year if stmt else m.period_end_date.year,
                    fiscal_quarter=stmt.fiscal_quarter if stmt else None,
                    value=value
                ))

    return HistoricalDataResponse(
        ticker=ticker.upper(),
        metric_name=metric,
        period_type=period_type,
        data=data_points
    )


@router.post("/{ticker}/refresh")
async def refresh_stock(ticker: str, db: Session = Depends(get_db)):
    """Manually refresh data for a stock."""
    fetcher = DataFetcher(db)
    stock = fetcher.refresh_stock_data(ticker)

    if not stock:
        raise HTTPException(status_code=404, detail="Could not fetch stock data")

    # Calculate metrics
    calculator = MetricsCalculator(db)
    calculator.calculate_all_metrics(stock.id)

    return {"message": f"Successfully refreshed data for {ticker.upper()}"}
