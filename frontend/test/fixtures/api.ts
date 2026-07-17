import type {
  BacktestReport,
  BacktestRequest,
  BacktestRunSummary,
  BacktestSeries,
  MarketSummaryItem,
  OhlcvResponse,
  StrategyMetrics,
  TickerInfo,
  TickerSearchItem,
} from '~/types/api'

export function marketSummaryItem(
  overrides: Partial<MarketSummaryItem> = {},
): MarketSummaryItem {
  return {
    symbol: 'AAA',
    last_price: 110,
    previous_close: 100,
    exchange: 'HOSE',
    ...overrides,
  }
}

export function tickerSearchItem(
  overrides: Partial<TickerSearchItem> = {},
): TickerSearchItem {
  return {
    symbol: 'AAA',
    short_name: 'Alpha',
    long_name: 'Alpha Corp',
    exchange: 'HOSE',
    ...overrides,
  }
}

export function tickerInfo(overrides: Partial<TickerInfo> = {}): TickerInfo {
  return {
    symbol: 'AAA',
    shortName: 'Alpha',
    longName: 'Alpha Corp',
    exchange: 'HOSE',
    currency: 'VND',
    sector: 'Financials',
    regularMarketPrice: 110,
    previousClose: 100,
    fiftyTwoWeekHigh: 150,
    fiftyTwoWeekLow: 80,
    ...overrides,
  }
}

export function ohlcvResponse(overrides: Partial<OhlcvResponse> = {}): OhlcvResponse {
  return {
    ticker: 'AAA',
    start: '2024-01-01',
    end: '2024-01-03',
    bars: [
      { date: '2024-01-01', open: 100, high: 105, low: 99, close: 102 },
      { date: '2024-01-02', open: 102, high: 108, low: 101, close: 107 },
      { date: '2024-01-03', open: 107, high: 110, low: 106, close: 109 },
    ],
    ...overrides,
  }
}

export function strategyMetrics(
  overrides: Partial<StrategyMetrics> = {},
): StrategyMetrics {
  return {
    total_cash_injected: 10_000_000,
    final_portfolio_value: 12_500_000,
    total_return_pct: 25,
    cagr_pct: 8.5,
    max_drawdown_pct: -12.3,
    sharpe_ratio: 1.25,
    ...overrides,
  }
}

export function backtestSeries(
  overrides: Partial<BacktestSeries> = {},
): BacktestSeries {
  return {
    dates: ['2024-01-01', '2024-01-02'],
    portfolio_value: {
      aggressive_dca: [10_000_000, 10_500_000],
      lump_sum: [10_000_000, 10_200_000],
    },
    drawdown_pct: {
      aggressive_dca: [0, -1],
      lump_sum: [0, -0.5],
    },
    ...overrides,
  }
}

export function backtestReport(
  overrides: Partial<BacktestReport> = {},
): BacktestReport {
  return {
    id: 'run-1',
    ticker: 'E1VFVN30.VN',
    strategy: 'aggressive_dca',
    visualization: 'series',
    start_date: '2020-01-01',
    end_date: '2025-01-01',
    effective_start_date: '2020-01-02',
    effective_end_date: '2024-12-31',
    params: { initial_cash: 10_000_000, monthly_cash: 1_000_000 },
    metrics: {
      aggressive_dca: strategyMetrics(),
      lump_sum: strategyMetrics({ total_return_pct: 15, sharpe_ratio: 0.9 }),
    },
    series: backtestSeries(),
    created_at: '2025-01-15T10:00:00Z',
    ...overrides,
  }
}

export function backtestRunSummary(
  overrides: Partial<BacktestRunSummary> = {},
): BacktestRunSummary {
  return {
    id: 'run-1',
    ticker: 'E1VFVN30.VN',
    strategy: 'aggressive_dca',
    start_date: '2020-01-01',
    end_date: '2025-01-01',
    effective_start_date: '2020-01-02',
    effective_end_date: '2024-12-31',
    created_at: '2025-01-15T10:00:00Z',
    sharpe: 1.25,
    cagr: 8.5,
    total_return_pct: 25,
    max_drawdown_pct: -12.3,
    visualization: 'series',
    params: {},
    ...overrides,
  }
}

export function backtestRequest(
  overrides: Partial<BacktestRequest> = {},
): BacktestRequest {
  return {
    ticker: 'E1VFVN30.VN',
    start_date: '2020-01-01',
    end_date: '2025-01-01',
    strategy: 'aggressive_dca',
    cadence: 'monthly',
    day_of_month: 1,
    weekday: 0,
    skip_after_buy_n: 0,
    optimize: true,
    visualization: 'series',
    lookback: null,
    drawdown_thresh: null,
    sma_period: null,
    initial_cash: 10_000_000,
    monthly_cash: 1_000_000,
    fee_rate: 0.0015,
    ma_type: 'sma',
    fast: 50,
    slow: 200,
    ...overrides,
  }
}
