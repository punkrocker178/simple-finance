import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import HistoryPage from './history.vue'
import { backtestRunSummary } from '../../../test/fixtures/api'

const { listRuns } = vi.hoisted(() => ({
  listRuns: vi.fn(),
}))

vi.mock('~/composables/useBacktestApi', () => ({
  useBacktestApi: () => ({ listRuns }),
}))

function findRunsTable(wrapper: Awaited<ReturnType<typeof mountSuspended>>) {
  return wrapper.findComponent({ name: 'BacktestRunsTable' }).exists()
    ? wrapper.findComponent({ name: 'BacktestRunsTable' })
    : wrapper.findComponent({ name: 'RunsTable' })
}

describe('pages/backtest/history', () => {
  beforeEach(() => {
    clearNuxtData('backtest-runs')
    listRuns.mockReset()
    listRuns.mockResolvedValue({ items: [], count: 0 })
  })

  it('renders heading and filter field', async () => {
    const wrapper = await mountSuspended(HistoryPage)

    expect(wrapper.text()).toContain('Backtest history')
    expect(wrapper.text()).toContain('Filter by ticker')
  })

  it('shows error alert when listRuns fails', async () => {
    listRuns.mockRejectedValue(new Error('list failed'))

    const wrapper = await mountSuspended(HistoryPage)
    expect(wrapper.text()).toMatch(/list failed|Failed to load runs/)
  })

  it('renders runs and navigates on select', async () => {
    listRuns.mockResolvedValue({
      items: [backtestRunSummary({ id: 'run-9', ticker: 'FOO' })],
      count: 1,
    })

    const wrapper = await mountSuspended(HistoryPage)

    expect(wrapper.text()).toContain('FOO')

    const pushSpy = vi.spyOn(useRouter(), 'push').mockResolvedValue(undefined as never)
    await findRunsTable(wrapper).vm.$emit('select', 'run-9')
    expect(pushSpy).toHaveBeenCalledWith('/backtest/run-9')
  })

  it('loads runs without ticker filter on mount', async () => {
    listRuns.mockResolvedValue({
      items: [backtestRunSummary({ id: 'run-1', ticker: 'AAA' })],
      count: 1,
    })

    const wrapper = await mountSuspended(HistoryPage)
    expect(listRuns).toHaveBeenCalledWith(undefined)
    expect(wrapper.text()).toContain('AAA')
  })
})
