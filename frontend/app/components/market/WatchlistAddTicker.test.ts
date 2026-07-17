import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { nextTick } from 'vue'
import WatchlistAddTicker from './WatchlistAddTicker.vue'
import { tickerSearchItem } from '../../../test/fixtures/api'

const { searchTickers } = vi.hoisted(() => ({
  searchTickers: vi.fn(),
}))

vi.mock('~/composables/useMarketApi', () => ({
  useMarketApi: () => ({ searchTickers }),
}))

describe('WatchlistAddTicker', () => {
  beforeEach(() => {
    searchTickers.mockReset()
    searchTickers.mockResolvedValue({
      items: [tickerSearchItem({ symbol: 'AAA', short_name: 'Alpha' })],
    })
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('debounces search and calls searchTickers', async () => {
    const wrapper = await mountSuspended(WatchlistAddTicker, {
      props: { onAdd: () => true },
    })

    const autocomplete = wrapper.findComponent({ name: 'VAutocomplete' })
    await autocomplete.vm.$emit('update:search', 'aa')
    expect(searchTickers).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(300)
    expect(searchTickers).toHaveBeenCalledWith('aa', {
      limit: 20,
      signal: expect.any(AbortSignal),
    })
  })

  it('shows duplicate hint when onAdd returns false', async () => {
    const onAdd = vi.fn().mockReturnValue(false)
    const wrapper = await mountSuspended(WatchlistAddTicker, {
      props: { onAdd },
    })

    const item = tickerSearchItem({ symbol: 'AAA' })
    const autocomplete = wrapper.findComponent({ name: 'VAutocomplete' })
    await autocomplete.vm.$emit('update:model-value', item)
    await nextTick()

    expect(onAdd).toHaveBeenCalledWith('AAA')
    expect(wrapper.text()).toContain('Already in watchlist')
  })

  it('clears search state after successful add', async () => {
    const onAdd = vi.fn().mockReturnValue(true)
    const wrapper = await mountSuspended(WatchlistAddTicker, {
      props: { onAdd },
    })

    const autocomplete = wrapper.findComponent({ name: 'VAutocomplete' })
    await autocomplete.vm.$emit('update:search', 'aa')
    await vi.advanceTimersByTimeAsync(300)
    await nextTick()

    await autocomplete.vm.$emit('update:model-value', tickerSearchItem({ symbol: 'AAA' }))
    await nextTick()

    expect(onAdd).toHaveBeenCalledWith('AAA')
    expect(wrapper.text()).not.toContain('Already in watchlist')
    // selected cleared — Add button disabled when nothing selected
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('Add'))
    expect(addBtn?.attributes('disabled')).toBeDefined()
  })
})
