<script setup lang="ts">
import type { StrategyMetrics } from '~/types/api'
import { formatCash } from '~/utils/formatCash'

const props = defineProps<{
  metrics: Record<string, StrategyMetrics | Record<string, unknown>>
}>()

const labels: Record<string, string> = {
  aggressive_dca: 'Aggressive DCA',
  scheduled_dca: 'Scheduled DCA',
  ma_crossover: 'MA Crossover',
  standard_dca: 'Standard DCA',
  lump_sum: 'Lump Sum',
  idle_cash: 'Idle Cash',
}

const cards = computed(() =>
  Object.entries(props.metrics).map(([key, raw]) => {
    const m = raw as StrategyMetrics
    return {
      key,
      title: labels[key] ?? key,
      totalReturn: m.total_return_pct,
      cagr: m.cagr_pct,
      sharpe: m.sharpe_ratio,
      maxDd: m.max_drawdown_pct,
      cashInjected: m.total_cash_injected,
      finalValue: m.final_portfolio_value,
      dipBuys: m.dip_buys_triggered,
      buys: m.buys_triggered,
      sells: m.sells_triggered,
    }
  }),
)

function fmtPct(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${value.toFixed(2)}%`
}
</script>

<template>
  <div class="grid gap-4 md:grid-cols-3">
    <div
      v-for="card in cards"
      :key="card.key"
      class="rounded-lg border border-gray-200 p-4"
    >
      <h3 class="mb-3 text-lg font-semibold">{{ card.title }}</h3>
      <dl class="grid grid-cols-2 gap-2 text-sm">
        <dt class="text-gray-600">Total return</dt>
        <dd class="text-right font-medium">{{ fmtPct(card.totalReturn) }}</dd>
        <dt class="text-gray-600">CAGR</dt>
        <dd class="text-right font-medium">{{ fmtPct(card.cagr) }}</dd>
        <dt class="text-gray-600">Sharpe</dt>
        <dd class="text-right font-medium">
          {{ card.sharpe == null ? '—' : card.sharpe.toFixed(2) }}
        </dd>
        <dt class="text-gray-600">Max drawdown</dt>
        <dd class="text-right font-medium">{{ fmtPct(card.maxDd) }}</dd>
        <dt class="text-gray-600">Cash injected</dt>
        <dd class="text-right font-medium">{{ formatCash(card.cashInjected) }}</dd>
        <dt class="text-gray-600">Final value</dt>
        <dd class="text-right font-medium">{{ formatCash(card.finalValue) }}</dd>
        <template v-if="card.dipBuys != null">
          <dt class="text-gray-600">Dip buys</dt>
          <dd class="text-right font-medium">{{ card.dipBuys }}</dd>
        </template>
        <template v-if="card.buys != null">
          <dt class="text-gray-600">Buys</dt>
          <dd class="text-right font-medium">{{ card.buys }}</dd>
        </template>
        <template v-if="card.sells != null">
          <dt class="text-gray-600">Sells</dt>
          <dd class="text-right font-medium">{{ card.sells }}</dd>
        </template>
      </dl>
    </div>
  </div>
</template>
