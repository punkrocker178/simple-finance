import { useApi } from '~/composables/useApi'
import type {
  MarketSummaryResponse,
  OhlcvResponse,
  TickerInfo,
  TickerSearchResponse,
} from '~/types/api'

/**
 * Typed market endpoints. No state — pair with useAsyncData in pages,
 * or call imperatively for ephemeral UI (e.g. search).
 */
export function useMarketApi() {
  const { apiFetch } = useApi()

  function getSummary(symbols?: string): Promise<MarketSummaryResponse> {
    if (!symbols) {
      return Promise.resolve({ symbols: [], items: [] })
    }
    return apiFetch<MarketSummaryResponse>('/api/v1/market/summary', {
      query: { symbols },
    })
  }

  function getTicker(ticker: string): Promise<TickerInfo> {
    return apiFetch<TickerInfo>(
      `/api/v1/market/tickers/${encodeURIComponent(ticker)}`,
    )
  }

  function getOhlcv(ticker: string, start: string, end: string): Promise<OhlcvResponse> {
    return apiFetch<OhlcvResponse>(
      `/api/v1/market/tickers/${encodeURIComponent(ticker)}/ohlcv`,
      { query: { start, end } },
    )
  }

  function searchTickers(
    q: string,
    opts?: { limit?: number; signal?: AbortSignal },
  ): Promise<TickerSearchResponse> {
    return apiFetch<TickerSearchResponse>('/api/v1/market/tickers/search', {
      query: { q, limit: opts?.limit ?? 20 },
      signal: opts?.signal,
    })
  }

  return { getSummary, getTicker, getOhlcv, searchTickers }
}
