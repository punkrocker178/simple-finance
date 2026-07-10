<script setup lang="ts">
import type { MarketSummaryItem } from '~/types/api'

defineProps<{
  items: MarketSummaryItem[]
  loading?: boolean
}>()

const emit = defineEmits<{
  select: [symbol: string]
}>()

function formatPrice(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function dayChange(item: MarketSummaryItem): number | null {
  if (item.last_price == null || item.previous_close == null || item.previous_close === 0) {
    return null
  }
  return ((item.last_price - item.previous_close) / item.previous_close) * 100
}
</script>

<template>
  <v-data-table
    :items="items"
    :loading="loading"
    :headers="[
      { title: 'Symbol', key: 'symbol' },
      { title: 'Last', key: 'last_price' },
      { title: 'Prev close', key: 'previous_close' },
      { title: 'Day %', key: 'day_pct' },
      { title: 'Exchange', key: 'exchange' },
    ]"
    item-value="symbol"
    hover
    class="rounded-lg"
    @click:row="(_e: Event, row: { item: MarketSummaryItem }) => emit('select', row.item.symbol)"
  >
    <template #item.last_price="{ item }">
      {{ formatPrice(item.last_price) }}
    </template>
    <template #item.previous_close="{ item }">
      {{ formatPrice(item.previous_close) }}
    </template>
    <template #item.day_pct="{ item }">
      <span
        :class="{
          'text-green-700': (dayChange(item) ?? 0) > 0,
          'text-red-700': (dayChange(item) ?? 0) < 0,
        }"
      >
        {{ dayChange(item) == null ? '—' : `${dayChange(item)!.toFixed(2)}%` }}
      </span>
    </template>
    <template #item.exchange="{ item }">
      {{ item.exchange || '—' }}
    </template>
  </v-data-table>
</template>
