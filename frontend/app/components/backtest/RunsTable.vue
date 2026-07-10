<script setup lang="ts">
import type { BacktestRunSummary } from '~/types/api'

defineProps<{
  items: BacktestRunSummary[]
  loading?: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
}>()

function fmtPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${value.toFixed(2)}%`
}

function fmtSharpe(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return value.toFixed(2)
}
</script>

<template>
  <v-data-table
    :items="items"
    :loading="loading"
    :headers="[
      { title: 'Ticker', key: 'ticker' },
      { title: 'Start', key: 'start_date' },
      { title: 'End', key: 'end_date' },
      { title: 'Sharpe', key: 'sharpe' },
      { title: 'CAGR', key: 'cagr' },
      { title: 'Return', key: 'total_return_pct' },
      { title: 'Max DD', key: 'max_drawdown_pct' },
      { title: 'Created', key: 'created_at' },
    ]"
    item-value="id"
    hover
    class="rounded-lg"
    @click:row="(_e: Event, row: { item: BacktestRunSummary }) => emit('select', row.item.id)"
  >
    <template #item.sharpe="{ item }">
      {{ fmtSharpe(item.sharpe) }}
    </template>
    <template #item.cagr="{ item }">
      {{ fmtPct(item.cagr) }}
    </template>
    <template #item.total_return_pct="{ item }">
      {{ fmtPct(item.total_return_pct) }}
    </template>
    <template #item.max_drawdown_pct="{ item }">
      {{ fmtPct(item.max_drawdown_pct) }}
    </template>
    <template #item.created_at="{ item }">
      {{ new Date(item.created_at).toLocaleString() }}
    </template>
  </v-data-table>
</template>
