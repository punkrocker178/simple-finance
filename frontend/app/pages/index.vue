<script setup lang="ts">
import { useApi } from '~/composables/useApi'
import type { MarketSummaryResponse } from '~/types/api'

useSeoMeta({
  title: 'Watchlist | Simple Finance',
  description: 'Market summary watchlist',
})

const { apiFetch } = useApi()
const router = useRouter()

const { data, pending, error, refresh } = await useAsyncData(
  'market-summary',
  () => apiFetch<MarketSummaryResponse>('/api/v1/market/summary'),
)

function onSelect(symbol: string) {
  void router.push(`/market/${encodeURIComponent(symbol)}`)
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-semibold">Watchlist</h1>
        <p class="mt-1 text-gray-600">Live snapshot from the market summary API.</p>
      </div>
      <div class="flex gap-2">
        <v-btn variant="outlined" :loading="pending" @click="refresh()">Refresh</v-btn>
        <v-btn color="primary" to="/backtest">Run backtest</v-btn>
      </div>
    </div>

    <v-alert v-if="error" type="error" variant="tonal">
      {{ error.message || 'Failed to load watchlist' }}
    </v-alert>

    <MarketWatchlistTable
      :items="data?.items ?? []"
      :loading="pending"
      @select="onSelect"
    />
  </div>
</template>
