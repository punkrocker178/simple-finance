import { useApi } from '~/composables/useApi'
import type {
  BacktestReport,
  BacktestRequest,
  BacktestRunListResponse,
  MaCrossoverRequest,
} from '~/types/api'

/**
 * Typed backtest endpoints. No state — pair with useAsyncData for reads,
 * or call from the backtest store for interactive runs.
 */
export function useBacktestApi() {
  const { apiFetch } = useApi()

  function listRuns(params?: {
    ticker?: string
    strategy?: string
  }): Promise<BacktestRunListResponse> {
    return apiFetch<BacktestRunListResponse>('/api/v1/backtest/runs', {
      query: params,
    })
  }

  function getRun(id: string): Promise<BacktestReport> {
    return apiFetch<BacktestReport>(`/api/v1/backtest/runs/${id}`)
  }

  function runDca(body: BacktestRequest): Promise<BacktestReport> {
    return apiFetch<BacktestReport>('/api/v1/backtest/dca', {
      method: 'POST',
      body,
    })
  }

  function runMaCrossover(body: MaCrossoverRequest): Promise<BacktestReport> {
    return apiFetch<BacktestReport>('/api/v1/backtest/ma-crossover', {
      method: 'POST',
      body,
    })
  }

  /** Route by strategy and build the correct request body. */
  function runBacktest(body: BacktestRequest): Promise<BacktestReport> {
    const withViz = { ...body, visualization: 'series' as const }
    if (withViz.strategy === 'ma_crossover') {
      return runMaCrossover({
        ticker: withViz.ticker,
        start_date: withViz.start_date,
        end_date: withViz.end_date,
        ma_type: withViz.ma_type ?? 'sma',
        fast: withViz.fast ?? 50,
        slow: withViz.slow ?? 200,
        initial_cash: withViz.initial_cash,
        fee_rate: withViz.fee_rate,
        visualization: withViz.visualization,
      })
    }
    return runDca(withViz)
  }

  return { listRuns, getRun, runDca, runMaCrossover, runBacktest }
}
