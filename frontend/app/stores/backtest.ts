import { useApi } from '~/composables/useApi'
import type {
  BacktestReport,
  BacktestRequest,
  BacktestRunListResponse,
  BacktestRunSummary,
} from '~/types/api'

function defaultEndDate(): string {
  return new Date().toISOString().slice(0, 10)
}

function defaultStartDate(): string {
  const d = new Date()
  d.setFullYear(d.getFullYear() - 5)
  return d.toISOString().slice(0, 10)
}

export const useBacktestStore = defineStore('backtest', () => {
  const form = reactive<BacktestRequest>({
    ticker: 'E1VFVN30.VN',
    start_date: defaultStartDate(),
    end_date: defaultEndDate(),
    strategy: 'aggressive_dca',
    cadence: 'monthly',
    day_of_month: 1,
    weekday: 0,
    skip_after_buy_n: 0,
    ma_type: 'sma',
    fast: 50,
    slow: 200,
    optimize: true,
    visualization: 'series',
    lookback: null,
    drawdown_thresh: null,
    sma_period: null,
    initial_cash: 10_000_000,
    monthly_cash: 1_000_000,
    fee_rate: 0.0015,
  })

  const lastReport = ref<BacktestReport | null>(null)
  const runs = ref<BacktestRunSummary[]>([])
  const pending = ref(false)
  const error = ref<string | null>(null)

  async function runBacktest(payload?: Partial<BacktestRequest>) {
    const { apiFetch, errorMessage } = useApi()
    pending.value = true
    error.value = null
    try {
      const body = { ...form, ...payload, visualization: 'series' as const }
      const path =
        body.strategy === 'ma_crossover'
          ? '/api/v1/backtest/ma-crossover'
          : '/api/v1/backtest/dca'
      const apiBody =
        body.strategy === 'ma_crossover'
          ? {
              ticker: body.ticker,
              start_date: body.start_date,
              end_date: body.end_date,
              ma_type: body.ma_type ?? 'sma',
              fast: body.fast ?? 50,
              slow: body.slow ?? 200,
              initial_cash: body.initial_cash,
              fee_rate: body.fee_rate,
              visualization: body.visualization,
            }
          : body
      lastReport.value = await apiFetch<BacktestReport>(path, {
        method: 'POST',
        body: apiBody,
      })
      return lastReport.value
    } catch (err) {
      error.value = errorMessage(err, 'Backtest failed')
      throw err
    } finally {
      pending.value = false
    }
  }

  async function runDca(payload?: Partial<BacktestRequest>) {
    return runBacktest(payload)
  }

  async function fetchRuns(params?: { ticker?: string; strategy?: string }) {
    const { apiFetch, errorMessage } = useApi()
    pending.value = true
    error.value = null
    try {
      const data = await apiFetch<BacktestRunListResponse>('/api/v1/backtest/runs', {
        query: params,
      })
      runs.value = data.items
      return data
    } catch (err) {
      error.value = errorMessage(err, 'Failed to load runs')
      throw err
    } finally {
      pending.value = false
    }
  }

  async function fetchRun(id: string) {
    const { apiFetch, errorMessage } = useApi()
    pending.value = true
    error.value = null
    try {
      lastReport.value = await apiFetch<BacktestReport>(`/api/v1/backtest/runs/${id}`)
      return lastReport.value
    } catch (err) {
      error.value = errorMessage(err, 'Failed to load run')
      throw err
    } finally {
      pending.value = false
    }
  }

  return {
    form,
    lastReport,
    runs,
    pending,
    error,
    runBacktest,
    runDca,
    fetchRuns,
    fetchRun,
  }
})
