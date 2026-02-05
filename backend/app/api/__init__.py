from fastapi import APIRouter
from app.api.routes import auth, stocks, watchlist, portfolio, screener, valuation

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["Stocks"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["Watchlist"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(screener.router, prefix="/screener", tags=["Screener"])
api_router.include_router(valuation.router, prefix="/valuation", tags=["Valuation"])
