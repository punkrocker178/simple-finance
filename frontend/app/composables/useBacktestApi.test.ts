import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useBacktestApi } from './useBacktestApi'
import type { BacktestRequest } from '~/types/api'

const { apiFetch } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
}))

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({ apiFetch, errorMessage: vi.fn(), baseURL: '' }),
}))

const baseDca: BacktestRequest = {
  start_date: '2020-01-01',
  end_date: '2025-01-01',
  ticker: 'E1VFVN30.VN',
  strategy: 'aggressive_dca',
  initial_cash: 10_000_000,
  monthly_cash: 1_000_000,
  fee_rate: 0.0015,
}

describe('useBacktestApi', () => {
  beforeEach(() => {
    apiFetch.mockReset()
    apiFetch.mockResolvedValue({ id: 'run-1' })
  })

  it('listRuns forwards query params', async () => {
    const { listRuns } = useBacktestApi()
    await listRuns({ ticker: 'AAA', strategy: 'aggressive_dca' })
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/backtest/runs', {
      query: { ticker: 'AAA', strategy: 'aggressive_dca' },
    })
  })

  it('getRun fetches by id', async () => {
    const { getRun } = useBacktestApi()
    await getRun('abc-123')
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/backtest/runs/abc-123')
  })

  it('runDca POSTs to /dca', async () => {
    const { runDca } = useBacktestApi()
    await runDca(baseDca)
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/backtest/dca', {
      method: 'POST',
      body: baseDca,
    })
  })

  it('runMaCrossover POSTs to /ma-crossover', async () => {
    const { runMaCrossover } = useBacktestApi()
    const body = {
      ticker: 'AAA',
      start_date: '2020-01-01',
      end_date: '2025-01-01',
      ma_type: 'sma' as const,
      fast: 50,
      slow: 200,
    }
    await runMaCrossover(body)
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/backtest/ma-crossover', {
      method: 'POST',
      body,
    })
  })

  it('runBacktest routes DCA strategies to /dca with visualization series', async () => {
    const { runBacktest } = useBacktestApi()
    await runBacktest(baseDca)
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/backtest/dca', {
      method: 'POST',
      body: { ...baseDca, visualization: 'series' },
    })
  })

  it('runBacktest routes ma_crossover and shapes the body', async () => {
    const { runBacktest } = useBacktestApi()
    await runBacktest({
      ...baseDca,
      strategy: 'ma_crossover',
      ma_type: undefined,
      fast: null,
      slow: null,
    })
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/backtest/ma-crossover', {
      method: 'POST',
      body: {
        ticker: 'E1VFVN30.VN',
        start_date: '2020-01-01',
        end_date: '2025-01-01',
        ma_type: 'sma',
        fast: 50,
        slow: 200,
        initial_cash: 10_000_000,
        fee_rate: 0.0015,
        visualization: 'series',
      },
    })
  })
})
