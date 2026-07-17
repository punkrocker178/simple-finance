import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import IndexPage from './index.vue'
import { marketSummaryItem } from '../../test/fixtures/api'

const { getSummary, watchlistAdd, watchlistRemove, symbols, ready } = vi.hoisted(() => {
  const { ref: hoistedRef } = require('vue') as typeof import('vue')
  return {
    getSummary: vi.fn(),
    watchlistAdd: vi.fn(),
    watchlistRemove: vi.fn(),
    symbols: hoistedRef<string[]>([]),
    ready: hoistedRef(true),
  }
})

vi.mock('~/composables/useMarketApi', () => ({
  useMarketApi: () => ({ getSummary }),
}))

mockNuxtImport('useWatchlist', () => () => ({
  symbols,
  ready,
  add: watchlistAdd,
  remove: watchlistRemove,
  has: (s: string) => symbols.value.includes(s),
}))

function findWatchlistTable(wrapper: Awaited<ReturnType<typeof mountSuspended>>) {
  return wrapper.findComponent({ name: 'MarketWatchlistTable' }).exists()
    ? wrapper.findComponent({ name: 'MarketWatchlistTable' })
    : wrapper.findComponent({ name: 'WatchlistTable' })
}

describe('pages/index', () => {
  beforeEach(() => {
    getSummary.mockReset()
    watchlistAdd.mockReset()
    watchlistRemove.mockReset()
    symbols.value = []
    ready.value = true
    getSummary.mockResolvedValue({ symbols: [], items: [] })
  })

  it('shows empty state when watchlist has no tickers', async () => {
    const wrapper = await mountSuspended(IndexPage)
    expect(wrapper.text()).toContain('No tickers yet')
  })

  it('shows error alert when summary fails', async () => {
    symbols.value = ['ERR1']
    getSummary.mockRejectedValue(new Error('network down'))

    const wrapper = await mountSuspended(IndexPage)
    expect(wrapper.text()).toMatch(/network down|Failed to load watchlist/)
  })

  it('renders summary table and navigates on select', async () => {
    symbols.value = ['AAA']
    getSummary.mockResolvedValue({
      symbols: ['AAA'],
      items: [marketSummaryItem({ symbol: 'AAA' })],
    })

    const wrapper = await mountSuspended(IndexPage, {
      global: {
        stubs: {
          MarketWatchlistAddTicker: true,
        },
      },
    })

    expect(wrapper.text()).toContain('AAA')
    expect(wrapper.text()).not.toContain('No tickers yet')

    const pushSpy = vi.spyOn(useRouter(), 'push').mockResolvedValue(undefined as never)
    await findWatchlistTable(wrapper).vm.$emit('select', 'AAA')
    expect(pushSpy).toHaveBeenCalledWith('/market/AAA')
  })

  it('calls watchlist.remove on remove', async () => {
    symbols.value = ['BBB']
    getSummary.mockResolvedValue({
      symbols: ['BBB'],
      items: [marketSummaryItem({ symbol: 'BBB' })],
    })

    const wrapper = await mountSuspended(IndexPage, {
      global: {
        stubs: { MarketWatchlistAddTicker: true },
      },
    })

    await findWatchlistTable(wrapper).vm.$emit('remove', 'BBB')
    expect(watchlistRemove).toHaveBeenCalledWith('BBB')
  })
})
