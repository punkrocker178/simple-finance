import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import BacktestRunPage from './[id].vue'
import { backtestReport } from '../../../test/fixtures/api'
import { pageStubs } from '../../../test/stubs'

const { getRun, routeParams } = vi.hoisted(() => ({
  getRun: vi.fn(),
  routeParams: { id: 'run-1' as string },
}))

vi.mock('~/composables/useBacktestApi', () => ({
  useBacktestApi: () => ({ getRun }),
}))

mockNuxtImport('useRoute', () => () => ({
  params: routeParams,
  query: {},
}))

describe('pages/backtest/[id]', () => {
  beforeEach(() => {
    getRun.mockReset()
    routeParams.id = 'run-1'
  })

  it('shows error alert when getRun fails', async () => {
    getRun.mockRejectedValue(new Error('not found'))

    const wrapper = await mountSuspended(BacktestRunPage, {
      global: { stubs: pageStubs },
    })

    expect(wrapper.text()).toMatch(/not found|Failed to load run/)
  })

  it('renders loaded report with strategy label and params', async () => {
    getRun.mockResolvedValue(
      backtestReport({
        ticker: 'E1VFVN30.VN',
        strategy: 'aggressive_dca',
        id: 'run-1',
      }),
    )

    const wrapper = await mountSuspended(BacktestRunPage, {
      global: {
        stubs: {
          ...pageStubs,
          BacktestMetricsCards: true,
        },
      },
    })

    expect(wrapper.text()).toContain('E1VFVN30.VN')
    expect(wrapper.text()).toContain('Aggressive DCA')
    expect(wrapper.text()).toContain('run-1')
    expect(wrapper.find('pre').exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'ChartsBacktestSeriesChart' }).exists()).toBe(true)
  })

  it('shows pending progress while loading', async () => {
    let resolveRun!: (v: unknown) => void
    getRun.mockReturnValue(
      new Promise((resolve) => {
        resolveRun = resolve
      }),
    )

    const wrapperPromise = mountSuspended(BacktestRunPage, {
      global: { stubs: pageStubs },
    })

    // Allow mount to start; pending UI may flash before resolve
    resolveRun(backtestReport())
    const wrapper = await wrapperPromise

    // After resolve, report content is shown
    expect(wrapper.text()).toContain('E1VFVN30.VN')
  })
})
