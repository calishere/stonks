# Stonks - Stock Fundamental Analysis Platform

A web-based system for analyzing the fundamentals of US stocks (NASDAQ & S&P 500 companies) with market cap over $1 billion.

## Features

- **Fundamental Metrics**: FCF, profit margins, ROE, ROCE, growth rates
- **DCF Valuation**: Calculate intrinsic value with customizable assumptions
- **Stock Screener**: Filter stocks by multiple criteria
- **Watchlist**: Track stocks you're interested in
- **Portfolio**: Monitor your investments
- **Historical Charts**: Quarterly and annual trends
- **Daily Updates**: Automated data refresh via Celery

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Celery
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS, Recharts
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **Containerization**: Docker, Docker Compose

## Quick Start (Local Development)

### Prerequisites

- Docker & Docker Compose
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd stonks
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

4. Initialize data (run once):
   ```bash
   # Connect to backend container
   docker exec -it stonks_backend bash

   # Run initial data fetch (this takes a while)
   python -c "from app.core.database import SessionLocal; from app.services.data_fetcher import DataFetcher; db = SessionLocal(); fetcher = DataFetcher(db); fetcher.refresh_all_stocks()"
   ```

## Project Structure

```
stonks/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── core/          # Config, security, database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── tasks/         # Celery background tasks
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API client
│   │   ├── context/       # React context
│   │   └── types/         # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── nginx/                 # Production Nginx config
├── docker-compose.yml     # Development
└── docker-compose.prod.yml # Production
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user

### Stocks
- `GET /api/stocks/` - List all stocks
- `GET /api/stocks/{ticker}` - Get stock details
- `GET /api/stocks/{ticker}/financials` - Get financial statements
- `GET /api/stocks/{ticker}/metrics` - Get calculated metrics
- `GET /api/stocks/{ticker}/history/{metric}` - Get historical data

### Valuation
- `GET /api/valuation/{ticker}` - Get DCF valuation
- `POST /api/valuation/{ticker}` - Calculate custom valuation

### Screener
- `POST /api/screener/` - Screen stocks with filters
- `GET /api/screener/undervalued` - Find undervalued stocks
- `GET /api/screener/quality` - Find quality stocks
- `GET /api/screener/growth` - Find growth stocks

### Watchlist & Portfolio
- `GET/POST/DELETE /api/watchlist/` - Manage watchlist
- `GET/POST/PUT/DELETE /api/portfolio/` - Manage portfolio

## Metrics Calculated

### Profitability
- Gross Margin
- Operating Margin
- Net Profit Margin
- ROE (Return on Equity)
- ROCE (Return on Capital Employed)
- ROA (Return on Assets)

### Cash Flow
- Free Cash Flow
- FCF Margin
- FCF Yield
- Operating Cash Flow Margin

### Growth (YoY)
- Revenue Growth
- Net Income Growth
- EPS Growth
- FCF Growth

### Valuation
- P/E Ratio
- P/B Ratio
- P/S Ratio
- Price to FCF
- EV/EBITDA
- PEG Ratio

### DCF Valuation
- Fair Value per Share
- Margin of Safety
- Valuation Status (undervalued/fair/overvalued)

## Production Deployment

1. Copy and configure production environment:
   ```bash
   cp .env.prod.example .env.prod
   # Edit .env.prod with secure values
   ```

2. Generate self-signed SSL (for initial setup):
   ```bash
   mkdir -p nginx/ssl
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout nginx/ssl/nginx.key \
     -out nginx/ssl/nginx.crt
   ```

3. Start production services:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. Setup Let's Encrypt SSL (replace yourdomain.com):
   ```bash
   docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
     --webroot -w /var/www/certbot \
     -d yourdomain.com
   ```

## Data Sources

- **Primary**: yfinance (Yahoo Finance)
- **Backup**: Financial Modeling Prep API (requires API key)

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| refresh-stock-list | Daily 6:00 AM UTC | Update stock list |
| update-prices | Daily 6:30 AM UTC | Fetch latest prices |
| update-financials | Weekly Sunday 7:00 AM UTC | Update financial statements |
| recalculate-metrics | Daily 7:30 AM UTC | Recalculate all metrics |
| update-valuations | Daily 8:00 AM UTC | Update DCF valuations |

## License

MIT
