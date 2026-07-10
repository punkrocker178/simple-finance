import { useApi } from '~/composables/useApi'
import type {
  MarketSummaryItem,
  MarketSummaryResponse,
  OhlcvResponse,
  TickerInfo,
} from '~/types/api'

export const useMarketStore = defineStore('market', () => {
  const summaryItems = ref<MarketSummaryItem[]>([])
  const tickerInfo = ref<TickerInfo | null>(null)
  const ohlcv = ref<OhlcvResponse | null>(null)
  const pending = ref(false)
  const error = ref<string | null>(null)

  async function fetchSummary(symbols?: string) {
    const { apiFetch, errorMessage } = useApi()
    pending.value = true
    error.value = null
    try {
      const query = symbols ? { symbols } : undefined
      const data = await apiFetch<MarketSummaryResponse>('/api/v1/market/summary', {
        query,
      })
      summaryItems.value = data.items
      return data
    } catch (err) {
      error.value = errorMessage(err, 'Failed to load market summary')
      throw err
    } finally {
      pending.value = false
    }
  }

  async function fetchTicker(ticker: string) {
    const { apiFetch, errorMessage } = useApi()
    pending.value = true
    error.value = null
    try {
      tickerInfo.value = await apiFetch<TickerInfo>(
        `/api/v1/market/tickers/${encodeURIComponent(ticker)}`,
      )
      return tickerInfo.value
    } catch (err) {
      error.value = errorMessage(err, 'Failed to load ticker')
      throw err
    } finally {
      pending.value = false
    }
  }

  async function fetchOhlcv(ticker: string, start: string, end: string) {
    const { apiFetch, errorMessage } = useApi()
    pending.value = true
    error.value = null
    try {
      ohlcv.value = await apiFetch<OhlcvResponse>(
        `/api/v1/market/tickers/${encodeURIComponent(ticker)}/ohlcv`,
        { query: { start, end } },
      )
      return ohlcv.value
    } catch (err) {
      error.value = errorMessage(err, 'Failed to load OHLCV')
      throw err
    } finally {
      pending.value = false
    }
  }

  return {
    summaryItems,
    tickerInfo,
    ohlcv,
    pending,
    error,
    fetchSummary,
    fetchTicker,
    fetchOhlcv,
  }
})
