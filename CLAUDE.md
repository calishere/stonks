# CLAUDE.md

## Project Overview

Stonks is a full-stack stock fundamental analysis platform for US stocks (NASDAQ & S&P 500, market cap > $1B). Monorepo with a Python/FastAPI backend and a React/TypeScript frontend, orchestrated with Docker Compose.

## Tech Stack

- **Backend**: Python 3.11, FastAPI 0.109, SQLAlchemy 2.0, Alembic, Celery 5.3 + Redis 7
- **Frontend**: React 18, TypeScript 5.2, Vite 5, TailwindCSS 3.4, TanStack React Query 5
- **Database**: PostgreSQL 15
- **Infrastructure**: Docker Compose, Nginx (production reverse proxy with SSL)

## Project Structure

```
backend/
  app/
    api/routes/     # FastAPI route handlers (auth, stocks, valuation, screener, watchlist, portfolio)
    core/           # Config (Pydantic settings), security, database setup
    models/         # SQLAlchemy ORM models (Stock, FinancialStatement, DailyPrice, CalculatedMetrics, User)
    schemas/        # Pydantic request/response schemas
    services/       # Business logic (data_fetcher, metrics_calculator, valuation_engine, screener)
    tasks/          # Celery background tasks (data refresh, price updates, metrics recalculation)
    main.py         # FastAPI app entrypoint
  requirements.txt

frontend/
  src/
    components/     # Reusable React components
    pages/          # Page components (Dashboard, StockDetail, Screener, Watchlist, Portfolio, Login, Register)
    services/       # Axios API client
    context/        # React context (AuthContext)
    types/          # TypeScript type definitions
    App.tsx         # Root component with routing
  package.json
  vite.config.ts
  tsconfig.json
  tailwind.config.js
```

## Development Commands

### Running the full stack (Docker)

```bash
docker compose up          # Start all services (backend:8000, frontend:3000, db, redis, celery)
docker compose down        # Stop all services
```

### Frontend

```bash
cd frontend
npm install                # Install dependencies
npm run dev                # Vite dev server on port 3000
npm run build              # TypeScript check + Vite production build
npm run lint               # ESLint (--max-warnings 0, strict)
npm run preview            # Preview production build
```

### Backend

```bash
cd backend
pip install -r requirements.txt   # Install dependencies
uvicorn app.main:app --reload     # Dev server on port 8000
celery -A app.tasks.celery_app worker --loglevel=info   # Celery worker
celery -A app.tasks.celery_app beat --loglevel=info      # Celery beat scheduler
```

### Database

```bash
# Alembic migrations (from backend/)
alembic upgrade head       # Apply migrations
alembic revision --autogenerate -m "description"   # Generate migration
```

## Key Configuration

- Backend settings are in `backend/app/core/config.py` using Pydantic `BaseSettings` (env vars)
- Environment variables: see `.env.example` and `.env.prod.example`
- Required env vars: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`
- Optional API keys: `FMP_API_KEY`, `FINNHUB_API_KEY`
- Frontend API URL configured via `VITE_API_URL` env var

## API

- Base URL: `http://localhost:8000`
- Swagger docs: `/docs`, ReDoc: `/redoc`
- Health check: `GET /health`
- Auth routes: `/api/auth/register`, `/api/auth/login`
- Stock data: `/api/stocks/`, `/api/stocks/{ticker}`
- Screening: `/api/screener/`
- Valuation: `/api/valuation/{ticker}`

## Background Tasks (Celery Beat Schedule)

| Task                  | Schedule              |
|-----------------------|-----------------------|
| refresh-stock-list    | Daily 6:00 AM UTC     |
| update-prices         | Daily 6:30 AM UTC     |
| update-financials     | Weekly Sundays 7:00 AM UTC |
| recalculate-metrics   | Daily 7:30 AM UTC     |
| update-valuations     | Daily 8:00 AM UTC     |

## Coding Conventions

- Backend: FastAPI dependency injection, Pydantic schemas for validation, SQLAlchemy ORM models
- Frontend: Functional React components, TanStack React Query for data fetching, Tailwind for styling
- TypeScript strict mode enabled (`noUnusedLocals`, `noUnusedParameters`)
- ESLint enforced with zero warnings tolerance
