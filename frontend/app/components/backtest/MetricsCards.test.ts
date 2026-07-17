import { describe, expect, it } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import MetricsCards from './MetricsCards.vue'
import { strategyMetrics } from '../../../test/fixtures/api'
import { formatCash } from '~/utils/formatCash'

describe('MetricsCards', () => {
  it('renders strategy labels and formatted metrics', async () => {
    const wrapper = await mountSuspended(MetricsCards, {
      props: {
        metrics: {
          aggressive_dca: strategyMetrics({
            dip_buys_triggered: 3,
          }),
          lump_sum: strategyMetrics({
            total_return_pct: 15,
            sharpe_ratio: 0.9,
          }),
        },
      },
    })

    expect(wrapper.text()).toContain('Aggressive DCA')
    expect(wrapper.text()).toContain('Lump Sum')
    expect(wrapper.text()).toContain('25.00%')
    expect(wrapper.text()).toContain('1.25')
    expect(wrapper.text()).toContain(formatCash(10_000_000))
    expect(wrapper.text()).toContain('Dip buys')
    expect(wrapper.text()).toContain('3')
  })

  it('shows buys and sells only when present', async () => {
    const wrapper = await mountSuspended(MetricsCards, {
      props: {
        metrics: {
          ma_crossover: strategyMetrics({
            buys_triggered: 5,
            sells_triggered: 2,
          }),
        },
      },
    })

    expect(wrapper.text()).toContain('MA Crossover')
    expect(wrapper.text()).toContain('Buys')
    expect(wrapper.text()).toContain('5')
    expect(wrapper.text()).toContain('Sells')
    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).not.toContain('Dip buys')
  })

  it('renders em dash for nullish sharpe', async () => {
    const wrapper = await mountSuspended(MetricsCards, {
      props: {
        metrics: {
          idle_cash: {
            ...strategyMetrics(),
            sharpe_ratio: null as unknown as number,
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Idle Cash')
    expect(wrapper.text()).toContain('—')
  })
})
