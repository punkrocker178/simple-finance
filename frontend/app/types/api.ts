export interface TickerInfo {
  symbol: string
  shortName?: string | null
  longName?: string | null
  exchange?: string | null
  quoteType?: string | null
  currency?: string | null
  market?: string | null
  sector?: string | null
  industry?: string | null
  marketCap?: number | null
  previousClose?: number | null
  regularMarketPrice?: number | null
  fiftyTwoWeekHigh?: number | null
  fiftyTwoWeekLow?: number | null
  trailingPE?: number | null
  dividendYield?: number | null
  volume?: number | null
  averageVolume?: number | null
  [key: string]: unknown
}

export interface OhlcvBar {
  date: string
  open: number
  high: number
  low: number
  close: number
}

export interface OhlcvResponse {
  ticker: string
  start: string
  end: string
  bars: OhlcvBar[]
}

export interface MarketSummaryItem {
  symbol: string
  last_price?: number | null
  previous_close?: number | null
  open?: number | null
  day_high?: number | null
  day_low?: number | null
  year_high?: number | null
  year_low?: number | null
  currency?: string | null
  exchange?: string | null
  market_cap?: number | null
  error?: string | null
  [key: string]: unknown
}

export interface MarketSummaryResponse {
  symbols: string[]
  items: MarketSummaryItem[]
}

export type VisualizationMode = 'series' | 'images' | 'both'

export interface BacktestRequest {
  ticker?: string | null
  start_date: string
  end_date: string
  optimize?: boolean
  visualization?: VisualizationMode
  lookback?: number | null
  drawdown_thresh?: number | null
  sma_period?: number | null
  initial_cash?: number | null
  monthly_cash?: number | null
  fee_rate?: number | null
}

export interface StrategyMetrics {
  total_cash_injected: number
  final_portfolio_value: number
  total_return_pct: number
  cagr_pct: number
  max_drawdown_pct: number
  sharpe_ratio: number
  dip_buys_triggered?: number | null
}

export interface BacktestSeries {
  dates: string[]
  portfolio_value: {
    aggressive_dca: number[]
    standard_dca: number[]
    lump_sum: number[]
  }
  drawdown_pct: {
    aggressive_dca: number[]
    standard_dca: number[]
    lump_sum: number[]
  }
  monthly_growth_pct?: Record<string, { dates: string[]; values: number[] }>
  dip_buys?: { dates: string[]; portfolio_values: number[] }
}

export interface BacktestReport {
  id: string
  ticker: string
  strategy: string
  visualization: VisualizationMode | string
  params: Record<string, unknown>
  metrics: Record<string, StrategyMetrics | Record<string, unknown>>
  series?: BacktestSeries | null
  images?: Record<string, unknown> | null
  created_at?: string | null
}

export interface BacktestRunSummary {
  id: string
  ticker: string
  strategy: string
  start_date: string
  end_date: string
  created_at: string
  sharpe?: number | null
  cagr?: number | null
  total_return_pct?: number | null
  max_drawdown_pct?: number | null
  visualization: VisualizationMode | string
  params: Record<string, unknown>
}

export interface BacktestRunListResponse {
  items: BacktestRunSummary[]
  count: number
}
