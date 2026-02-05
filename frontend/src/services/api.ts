import axios from 'axios'
import type {
  Stock,
  StockDetail,
  FinancialStatement,
  Metrics,
  HistoricalData,
  Valuation,
  ScreenerFilters,
  ScreenerResult,
  WatchlistItem,
  PortfolioSummary,
  User,
} from '../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auth
export const authApi = {
  login: async (email: string, password: string) => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data as { access_token: string; token_type: string }
  },

  register: async (email: string, password: string, fullName?: string) => {
    const response = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    return response.data as User
  },

  getMe: async () => {
    const response = await api.get('/auth/me')
    return response.data as User
  },
}

// Stocks
export const stocksApi = {
  list: async (page = 1, perPage = 50, sector?: string, search?: string) => {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
    })
    if (sector) params.append('sector', sector)
    if (search) params.append('search', search)

    const response = await api.get(`/stocks/?${params}`)
    return response.data as {
      stocks: Stock[]
      total: number
      page: number
      per_page: number
    }
  },

  get: async (ticker: string) => {
    const response = await api.get(`/stocks/${ticker}`)
    return response.data as StockDetail
  },

  getFinancials: async (ticker: string, periodType = 'quarterly', limit = 12) => {
    const response = await api.get(
      `/stocks/${ticker}/financials?period_type=${periodType}&limit=${limit}`
    )
    return response.data as FinancialStatement[]
  },

  getPrices: async (ticker: string, days = 365) => {
    const response = await api.get(`/stocks/${ticker}/prices?days=${days}`)
    return response.data as { date: string; close: number; volume: number }[]
  },

  getMetrics: async (ticker: string, periodType = 'quarterly', limit = 12) => {
    const response = await api.get(
      `/stocks/${ticker}/metrics?period_type=${periodType}&limit=${limit}`
    )
    return response.data as Metrics[]
  },

  getMetricHistory: async (
    ticker: string,
    metric: string,
    periodType = 'quarterly',
    limit = 20
  ) => {
    const response = await api.get(
      `/stocks/${ticker}/history/${metric}?period_type=${periodType}&limit=${limit}`
    )
    return response.data as HistoricalData
  },

  refresh: async (ticker: string) => {
    const response = await api.post(`/stocks/${ticker}/refresh`)
    return response.data
  },
}

// Valuation
export const valuationApi = {
  get: async (ticker: string) => {
    const response = await api.get(`/valuation/${ticker}`)
    return response.data as Valuation
  },

  calculate: async (
    ticker: string,
    params: {
      growth_rate?: number
      discount_rate?: number
      terminal_growth_rate?: number
      projection_years?: number
    }
  ) => {
    const response = await api.post(`/valuation/${ticker}`, params)
    return response.data as Valuation
  },

  getStatus: async (ticker: string) => {
    const response = await api.get(`/valuation/${ticker}/status`)
    return response.data
  },
}

// Screener
export const screenerApi = {
  screen: async (filters: ScreenerFilters) => {
    const response = await api.post('/screener/', filters)
    return response.data as {
      results: ScreenerResult[]
      total: number
      page: number
      per_page: number
      filters_applied: Record<string, unknown>
    }
  },

  getSectors: async () => {
    const response = await api.get('/screener/sectors')
    return response.data as string[]
  },

  getIndustries: async (sector?: string) => {
    const url = sector ? `/screener/industries?sector=${sector}` : '/screener/industries'
    const response = await api.get(url)
    return response.data as string[]
  },

  getExchanges: async () => {
    const response = await api.get('/screener/exchanges')
    return response.data as string[]
  },

  getTop: async (metric: string, limit = 10) => {
    const response = await api.get(`/screener/top/${metric}?limit=${limit}`)
    return response.data as ScreenerResult[]
  },

  getUndervalued: async (minMargin = 20) => {
    const response = await api.get(`/screener/undervalued?min_margin=${minMargin}`)
    return response.data as ScreenerResult[]
  },

  getQuality: async () => {
    const response = await api.get('/screener/quality')
    return response.data as ScreenerResult[]
  },

  getGrowth: async () => {
    const response = await api.get('/screener/growth')
    return response.data as ScreenerResult[]
  },
}

// Watchlist
export const watchlistApi = {
  get: async () => {
    const response = await api.get('/watchlist/')
    return response.data as WatchlistItem[]
  },

  add: async (ticker: string) => {
    const response = await api.post('/watchlist/', { ticker })
    return response.data as WatchlistItem
  },

  remove: async (ticker: string) => {
    await api.delete(`/watchlist/${ticker}`)
  },
}

// Portfolio
export const portfolioApi = {
  get: async () => {
    const response = await api.get('/portfolio/')
    return response.data as PortfolioSummary
  },

  add: async (ticker: string, shares: number, averageCost: number) => {
    const response = await api.post('/portfolio/', {
      ticker,
      shares,
      average_cost: averageCost,
    })
    return response.data
  },

  update: async (ticker: string, shares?: number, averageCost?: number) => {
    const response = await api.put(`/portfolio/${ticker}`, {
      shares,
      average_cost: averageCost,
    })
    return response.data
  },

  remove: async (ticker: string) => {
    await api.delete(`/portfolio/${ticker}`)
  },
}

export default api
