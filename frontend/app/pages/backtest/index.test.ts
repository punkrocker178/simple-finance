import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import BacktestPage from './index.vue'
import { backtestReport } from '../../../test/fixtures/api'
import { pageStubs } from '../../../test/stubs'
import { useBacktestStore } from '~/stores/backtest'

const { routeQuery } = vi.hoisted(() => ({
  routeQuery: { ticker: undefined as string | undefined },
}))

mockNuxtImport('useRoute', () => () => ({
  params: {},
  query: routeQuery,
}))

describe('pages/backtest/index', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    routeQuery.ticker = undefined
  })

  it('renders form and heading', async () => {
    const wrapper = await mountSuspended(BacktestPage, {
      global: { stubs: { ...pageStubs, BacktestForm: true } },
    })

    expect(wrapper.text()).toContain('Backtest')
    expect(wrapper.text()).toContain('View history')
  })

  it('prefills ticker from query string', async () => {
    routeQuery.ticker = 'FOO.VN'
    await mountSuspended(BacktestPage, {
      global: { stubs: { ...pageStubs, BacktestForm: true } },
    })

    const store = useBacktestStore()
    expect(store.form.ticker).toBe('FOO.VN')
  })

  it('shows results when lastReport is set', async () => {
    const wrapper = await mountSuspended(BacktestPage, {
      global: {
        stubs: {
          ...pageStubs,
          BacktestForm: true,
          BacktestMetricsCards: true,
        },
      },
    })

    const store = useBacktestStore()
    store.lastReport = backtestReport({ ticker: 'E1VFVN30.VN' })
    await nextTick()

    expect(wrapper.text()).toContain('Results — E1VFVN30.VN')
    expect(wrapper.text()).toContain('Open saved run')
    expect(wrapper.findComponent({ name: 'ChartsBacktestSeriesChart' }).exists()).toBe(true)
  })

  it('shows error alert from store', async () => {
    const wrapper = await mountSuspended(BacktestPage, {
      global: { stubs: { ...pageStubs, BacktestForm: true } },
    })

    const store = useBacktestStore()
    store.error = 'Backtest failed'
    await nextTick()

    expect(wrapper.text()).toContain('Backtest failed')
  })
})
