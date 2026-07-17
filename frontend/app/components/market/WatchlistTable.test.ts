import { describe, expect, it } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import WatchlistTable from './WatchlistTable.vue'
import { marketSummaryItem } from '../../../test/fixtures/api'

describe('WatchlistTable', () => {
  it('renders prices and positive day change', async () => {
    const wrapper = await mountSuspended(WatchlistTable, {
      props: {
        items: [marketSummaryItem({ symbol: 'AAA', last_price: 110, previous_close: 100 })],
      },
    })

    expect(wrapper.text()).toContain('AAA')
    expect(wrapper.text()).toContain('10.00%')
    const dayPct = wrapper.find('.text-green-700')
    expect(dayPct.exists()).toBe(true)
  })

  it('renders em dash for null prices and day change', async () => {
    const wrapper = await mountSuspended(WatchlistTable, {
      props: {
        items: [
          marketSummaryItem({
            symbol: 'BBB',
            last_price: null,
            previous_close: null,
            exchange: null,
          }),
        ],
      },
    })

    expect(wrapper.text()).toContain('BBB')
    expect(wrapper.text()).toContain('—')
  })

  it('applies red class for negative day change', async () => {
    const wrapper = await mountSuspended(WatchlistTable, {
      props: {
        items: [marketSummaryItem({ last_price: 90, previous_close: 100 })],
      },
    })

    expect(wrapper.text()).toContain('-10.00%')
    expect(wrapper.find('.text-red-700').exists()).toBe(true)
  })

  it('emits select on row click and remove on Remove button', async () => {
    const wrapper = await mountSuspended(WatchlistTable, {
      props: {
        items: [marketSummaryItem({ symbol: 'AAA' })],
      },
    })

    const table = wrapper.findComponent({ name: 'VDataTable' })
    await table.vm.$emit('click:row', new Event('click'), {
      item: marketSummaryItem({ symbol: 'AAA' }),
    })
    expect(wrapper.emitted('select')?.[0]).toEqual(['AAA'])

    const removeBtn = wrapper.findAll('button').find((b) => b.text().includes('Remove'))
    expect(removeBtn).toBeTruthy()
    await removeBtn!.trigger('click')
    expect(wrapper.emitted('remove')?.[0]).toEqual(['AAA'])
  })
})
