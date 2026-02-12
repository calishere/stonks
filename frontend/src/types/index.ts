export interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  created_at: string
}

export interface Stock {
  id: number
  ticker: string
  name: string
  sector: string | null
  industry: string | null
  exchange: string | null
  market_cap: number | null
  currency: string
  is_active: boolean
  last_updated: string | null
}

export interface StockDetail extends Stock {
  current_price: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  ps_ratio: number | null
  gross_margin: number | null
  operating_margin: number | null
  net_profit_margin: number | null
  roe: number | null
  roce: number | null
  free_cash_flow: number | null
  fcf_margin: number | null
  fcf_yield: number | null
  revenue_growth: number | null
  eps_growth: number | null
  fair_value_per_share: number | null
  margin_of_safety: number | null
  valuation_status: 'undervalued' | 'overvalued' | 'fair' | null
}

export interface FinancialStatement {
  id: number
  stock_id: number
  period_type: string
  period_end_date: string
  fiscal_year: number
  fiscal_quarter: number | null
  revenue: number | null
  gross_profit: number | null
  operating_income: number | null
  net_income: number | null
  ebitda: number | null
  total_assets: number | null
  total_liabilities: number | null
  total_equity: number | null
  total_debt: number | null
  cash_and_equivalents: number | null
  operating_cash_flow: number | null
  capital_expenditure: number | null
  free_cash_flow: number | null
  earnings_per_share: number | null
  shares_outstanding: number | null
}

export interface Metrics {
  stock_id: number
  period_type: string
  period_end_date: string
  gross_margin: number | null
  operating_margin: number | null
  net_profit_margin: number | null
  roe: number | null
  roce: number | null
  roa: number | null
  fcf_margin: number | null
  fcf_yield: number | null
  revenue_growth: number | null
  net_income_growth: number | null
  fcf_growth: number | null
  eps_growth: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  ps_ratio: number | null
  price_to_fcf: number | null
  ev_to_ebitda: number | null
  peg_ratio: number | null
  debt_to_equity: number | null
  current_ratio: number | null
  fair_value_per_share: number | null
  margin_of_safety: number | null
  valuation_status: string | null
}

export interface HistoricalDataPoint {
  period_end_date: string
  fiscal_year: number
  fiscal_quarter: number | null
  value: number
}

export interface HistoricalData {
  ticker: string
  metric_name: string
  period_type: string
  data: HistoricalDataPoint[]
}

export interface DCFProjection {
  year: number
  projected_fcf: number
  discount_factor: number
  present_value: number
}

export interface Valuation {
  ticker: string
  name: string
  current_price: number
  shares_outstanding: number
  market_cap: number
  latest_fcf: number
  estimated_growth_rate: number
  discount_rate: number
  terminal_growth_rate: number
  projection_years: number
  projections: DCFProjection[]
  terminal_value: number
  terminal_value_pv: number
  enterprise_value: number
  equity_value: number
  fair_value_per_share: number
  upside_downside: number
  margin_of_safety: number
  valuation_status: string
  pe_based_value: number | null
  forward_pe_ratio: number | null
  forward_pe_based_value: number | null
  peg_ratio: number | null
  peg_based_value: number | null
  pb_based_value: number | null
  ps_based_value: number | null
  valuation_summary: string
}

export interface ScreenerFilters {
  min_market_cap?: number
  max_market_cap?: number
  sectors?: string[]
  industries?: string[]
  exchanges?: string[]
  min_gross_margin?: number
  min_operating_margin?: number
  min_net_margin?: number
  min_roe?: number
  min_roce?: number
  min_fcf_margin?: number
  min_fcf_yield?: number
  positive_fcf_only?: boolean
  min_revenue_growth?: number
  min_eps_growth?: number
  max_pe_ratio?: number
  min_pe_ratio?: number
  max_pb_ratio?: number
  max_ps_ratio?: number
  max_price_to_fcf?: number
  max_peg_ratio?: number
  max_debt_to_equity?: number
  min_current_ratio?: number
  valuation_status?: string
  min_margin_of_safety?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  per_page?: number
}

export interface ScreenerResult {
  id: number
  ticker: string
  name: string
  sector: string | null
  industry: string | null
  exchange: string | null
  market_cap: number | null
  current_price: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  roe: number | null
  roce: number | null
  net_profit_margin: number | null
  fcf_yield: number | null
  revenue_growth: number | null
  debt_to_equity: number | null
  fair_value_per_share: number | null
  margin_of_safety: number | null
  valuation_status: string | null
}

export interface WatchlistItem {
  id: number
  stock_id: number
  ticker: string
  name: string
  sector: string | null
  current_price: number | null
  market_cap: number | null
  added_at: string
}

export interface PortfolioPosition {
  id: number
  stock_id: number
  ticker: string
  name: string
  shares: number
  average_cost: number
  current_price: number | null
  current_value: number | null
  gain_loss: number | null
  gain_loss_percent: number | null
  created_at: string
}

export interface PortfolioSummary {
  positions: PortfolioPosition[]
  total_cost: number
  total_value: number
  total_gain_loss: number
  total_gain_loss_percent: number
}
