import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useMarketApi } from './useMarketApi'

const { apiFetch } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
}))

vi.mock('~/composables/useApi', () => ({
  useApi: () => ({ apiFetch, errorMessage: vi.fn(), baseURL: '' }),
}))

describe('useMarketApi', () => {
  beforeEach(() => {
    apiFetch.mockReset()
  })

  it('getSummary skips HTTP when symbols is empty/undefined', async () => {
    const { getSummary } = useMarketApi()
    await expect(getSummary()).resolves.toEqual({ symbols: [], items: [] })
    await expect(getSummary('')).resolves.toEqual({ symbols: [], items: [] })
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('getSummary fetches with symbols query', async () => {
    apiFetch.mockResolvedValue({ symbols: ['AAA'], items: [] })
    const { getSummary } = useMarketApi()
    await getSummary('AAA,BBB')
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/market/summary', {
      query: { symbols: 'AAA,BBB' },
    })
  })

  it('getTicker encodes the ticker path', async () => {
    apiFetch.mockResolvedValue({ symbol: 'E1VFVN30.VN' })
    const { getTicker } = useMarketApi()
    await getTicker('E1VFVN30.VN')
    expect(apiFetch).toHaveBeenCalledWith(
      '/api/v1/market/tickers/E1VFVN30.VN',
    )
  })

  it('getOhlcv passes start/end query', async () => {
    apiFetch.mockResolvedValue({ ticker: 'AAA', start: '2020-01-01', end: '2021-01-01', bars: [] })
    const { getOhlcv } = useMarketApi()
    await getOhlcv('AAA', '2020-01-01', '2021-01-01')
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/market/tickers/AAA/ohlcv', {
      query: { start: '2020-01-01', end: '2021-01-01' },
    })
  })

  it('searchTickers defaults limit to 20 and forwards signal', async () => {
    apiFetch.mockResolvedValue({ items: [] })
    const { searchTickers } = useMarketApi()
    const signal = new AbortController().signal
    await searchTickers('vn', { signal })
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/market/tickers/search', {
      query: { q: 'vn', limit: 20 },
      signal,
    })
  })

  it('searchTickers respects custom limit', async () => {
    apiFetch.mockResolvedValue({ items: [] })
    const { searchTickers } = useMarketApi()
    await searchTickers('vn', { limit: 5 })
    expect(apiFetch).toHaveBeenCalledWith('/api/v1/market/tickers/search', {
      query: { q: 'vn', limit: 5 },
      signal: undefined,
    })
  })
})
