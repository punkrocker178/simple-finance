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

  async function runDca(payload?: Partial<BacktestRequest>) {
    const { apiFetch, errorMessage } = useApi()
    pending.value = true
    error.value = null
    try {
      const body: BacktestRequest = {
        ...form,
        ...payload,
        visualization: 'series',
      }
      lastReport.value = await apiFetch<BacktestReport>('/api/v1/backtest/dca', {
        method: 'POST',
        body,
      })
      return lastReport.value
    } catch (err) {
      error.value = errorMessage(err, 'Backtest failed')
      throw err
    } finally {
      pending.value = false
    }
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
    runDca,
    fetchRuns,
    fetchRun,
  }
})
