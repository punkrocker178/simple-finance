import { useApi } from '~/composables/useApi'
import { useBacktestApi } from '~/composables/useBacktestApi'
import type { BacktestReport, BacktestRequest } from '~/types/api'

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
  const pending = ref(false)
  const error = ref<string | null>(null)

  async function runBacktest(payload?: Partial<BacktestRequest>) {
    const { runBacktest: apiRun } = useBacktestApi()
    const { errorMessage } = useApi()
    pending.value = true
    error.value = null
    try {
      lastReport.value = await apiRun({ ...form, ...payload })
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

  return {
    form,
    lastReport,
    pending,
    error,
    runBacktest,
    runDca,
  }
})
