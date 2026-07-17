import { describe, expect, it } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { nextTick, reactive } from 'vue'
import BacktestForm from './BacktestForm.vue'
import { backtestRequest } from '../../../test/fixtures/api'

describe('BacktestForm', () => {
  it('renders base fields from v-model', async () => {
    const model = reactive(backtestRequest({ ticker: 'FOO.VN' }))
    const wrapper = await mountSuspended(BacktestForm, {
      props: { modelValue: model, 'onUpdate:modelValue': (v: typeof model) => Object.assign(model, v) },
    })

    expect(wrapper.text()).toContain('Ticker')
    expect(wrapper.text()).toContain('Strategy')
    expect(wrapper.text()).toContain('Run backtest')
    const tickerInput = wrapper.find('input')
    expect((tickerInput.element as HTMLInputElement).value).toBe('FOO.VN')
  })

  it('shows MA fields and hides monthly cash for ma_crossover', async () => {
    const model = reactive(backtestRequest({ strategy: 'ma_crossover' }))
    const wrapper = await mountSuspended(BacktestForm, {
      props: { modelValue: model },
    })

    expect(wrapper.text()).toContain('MA type')
    expect(wrapper.text()).toContain('Fast period')
    expect(wrapper.text()).toContain('Slow period')
    expect(wrapper.text()).not.toContain('Monthly cash')
    expect(wrapper.text()).not.toContain('Period cash')
  })

  it('shows cadence fields for scheduled_dca', async () => {
    const model = reactive(
      backtestRequest({ strategy: 'scheduled_dca', cadence: 'monthly' }),
    )
    const wrapper = await mountSuspended(BacktestForm, {
      props: { modelValue: model },
    })

    expect(wrapper.text()).toContain('Cadence')
    expect(wrapper.text()).toContain('Day of month')
  })

  it('blocks submit when date range is invalid', async () => {
    const model = reactive(
      backtestRequest({ start_date: '2025-01-01', end_date: '2020-01-01' }),
    )
    const wrapper = await mountSuspended(BacktestForm, {
      props: { modelValue: model },
    })
    await nextTick()

    expect(wrapper.text()).toContain('Start must be on or before end')
    const submitBtn = wrapper.find('button[type="submit"]')
    expect(submitBtn.attributes('disabled')).toBeDefined()

    await wrapper.find('form').trigger('submit.prevent')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('emits submit for valid dates', async () => {
    const model = reactive(backtestRequest())
    const wrapper = await mountSuspended(BacktestForm, {
      props: { modelValue: model },
    })

    await wrapper.find('form').trigger('submit.prevent')
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })
})
