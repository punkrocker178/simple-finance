import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import TickerPage from './[ticker].vue'
import { ohlcvResponse, tickerInfo } from '../../../test/fixtures/api'
import { pageStubs } from '../../../test/stubs'

const { getTicker, getOhlcv, routeParams } = vi.hoisted(() => ({
  getTicker: vi.fn(),
  getOhlcv: vi.fn(),
  routeParams: { ticker: 'AAA' as string },
}))

vi.mock('~/composables/useMarketApi', () => ({
  useMarketApi: () => ({ getTicker, getOhlcv }),
}))

mockNuxtImport('useRoute', () => () => ({
  params: routeParams,
  query: {},
}))

describe('pages/market/[ticker]', () => {
  beforeEach(() => {
    getTicker.mockReset()
    getOhlcv.mockReset()
    routeParams.ticker = 'AAA'
    getTicker.mockResolvedValue(tickerInfo({ symbol: 'AAA', exchange: 'HOSE' }))
    getOhlcv.mockResolvedValue(ohlcvResponse())
  })

  it('renders ticker heading and info chips', async () => {
    const wrapper = await mountSuspended(TickerPage, {
      global: { stubs: pageStubs },
    })

    expect(wrapper.text()).toContain('AAA')
    expect(wrapper.text()).toContain('Alpha Corp')
    expect(wrapper.text()).toContain('HOSE')
    expect(wrapper.text()).toContain('VND')
  })

  it('shows info error alert', async () => {
    // Unique ticker avoids useAsyncData cache from prior tests
    routeParams.ticker = 'MISSING'
    getTicker.mockRejectedValue(new Error('ticker missing'))
    getOhlcv.mockResolvedValue(ohlcvResponse({ ticker: 'MISSING', bars: [] }))

    const wrapper = await mountSuspended(TickerPage, {
      global: { stubs: pageStubs },
    })

    expect(wrapper.text()).toMatch(/ticker missing|Failed to load ticker info/)
  })

  it('shows ohlcv error alert', async () => {
    routeParams.ticker = 'OHLCVERR'
    getTicker.mockResolvedValue(tickerInfo({ symbol: 'OHLCVERR' }))
    getOhlcv.mockRejectedValue(new Error('ohlcv failed'))

    const wrapper = await mountSuspended(TickerPage, {
      global: { stubs: pageStubs },
    })

    expect(wrapper.text()).toMatch(/ohlcv failed|Failed to load OHLCV/)
  })

  it('shows bar count and chart stub for valid data', async () => {
    routeParams.ticker = 'CHART'
    getTicker.mockResolvedValue(tickerInfo({ symbol: 'CHART' }))
    getOhlcv.mockResolvedValue(ohlcvResponse({ ticker: 'CHART' }))

    const wrapper = await mountSuspended(TickerPage, {
      global: { stubs: pageStubs },
    })

    expect(wrapper.text()).toContain('3 bars from 2024-01-01 to 2024-01-03')
    expect(wrapper.findComponent({ name: 'ChartsOhlcvChart' }).exists()).toBe(true)
  })

  it('disables reload when date range is invalid', async () => {
    routeParams.ticker = 'DATES'
    getTicker.mockResolvedValue(tickerInfo({ symbol: 'DATES' }))
    getOhlcv.mockResolvedValue(ohlcvResponse({ ticker: 'DATES' }))

    const wrapper = await mountSuspended(TickerPage, {
      global: { stubs: pageStubs },
    })

    const vm = wrapper.vm as { startDate: string; endDate: string }
    vm.startDate = '2025-01-01'
    vm.endDate = '2020-01-01'
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Start must be on or before end')
    const reloadBtn = wrapper.findAll('button').find((b) => b.text().includes('Reload'))
    expect(reloadBtn?.attributes('disabled')).toBeDefined()
  })
})
