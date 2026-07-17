import { describe, expect, it } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import RunsTable from './RunsTable.vue'
import { backtestRunSummary } from '../../../test/fixtures/api'

describe('RunsTable', () => {
  it('formats metrics and date ranges', async () => {
    const wrapper = await mountSuspended(RunsTable, {
      props: {
        items: [backtestRunSummary()],
      },
    })

    expect(wrapper.text()).toContain('E1VFVN30.VN')
    expect(wrapper.text()).toContain('2020-01-01 – 2025-01-01')
    expect(wrapper.text()).toContain('2020-01-02 – 2024-12-31')
    expect(wrapper.text()).toContain('1.25')
    expect(wrapper.text()).toContain('8.50%')
    expect(wrapper.text()).toContain('25.00%')
    expect(wrapper.text()).toContain('-12.30%')
  })

  it('shows em dash when effective dates and metrics are missing', async () => {
    const wrapper = await mountSuspended(RunsTable, {
      props: {
        items: [
          backtestRunSummary({
            effective_start_date: null,
            effective_end_date: null,
            sharpe: null,
            cagr: null,
            total_return_pct: null,
            max_drawdown_pct: null,
          }),
        ],
      },
    })

    expect(wrapper.text()).toContain('—')
  })

  it('emits select with run id on row click', async () => {
    const item = backtestRunSummary({ id: 'run-42', ticker: 'FOO' })
    const wrapper = await mountSuspended(RunsTable, {
      props: { items: [item] },
    })

    const table = wrapper.findComponent({ name: 'VDataTable' })
    await table.vm.$emit('click:row', new Event('click'), { item })
    expect(wrapper.emitted('select')?.[0]).toEqual(['run-42'])
  })
})
