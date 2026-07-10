<script setup lang="ts">
import type { StrategyMetrics } from '~/types/api'

const props = defineProps<{
  metrics: Record<string, StrategyMetrics | Record<string, unknown>>
}>()

const labels: Record<string, string> = {
  aggressive_dca: 'Aggressive DCA',
  standard_dca: 'Standard DCA',
  lump_sum: 'Lump Sum',
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
      finalValue: m.final_portfolio_value,
      dipBuys: m.dip_buys_triggered,
    }
  }),
)

function fmtPct(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${value.toFixed(2)}%`
}

function fmtNum(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 })
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
        <dt class="text-gray-600">Final value</dt>
        <dd class="text-right font-medium">{{ fmtNum(card.finalValue) }}</dd>
        <template v-if="card.dipBuys != null">
          <dt class="text-gray-600">Dip buys</dt>
          <dd class="text-right font-medium">{{ card.dipBuys }}</dd>
        </template>
      </dl>
    </div>
  </div>
</template>
