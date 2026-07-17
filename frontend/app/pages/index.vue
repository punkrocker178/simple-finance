<script setup lang="ts">
import { useMarketApi } from '~/composables/useMarketApi'

useSeoMeta({
  title: 'Watchlist | Simple Finance',
  description: 'Market summary watchlist',
})

const { getSummary } = useMarketApi()
const router = useRouter()
const watchlist = useWatchlist()

const symbolsParam = computed(() => watchlist.symbols.value.join(','))

const { data, pending, error, refresh } = await useAsyncData(
  'market-summary',
  () => getSummary(symbolsParam.value || undefined),
  { server: false, watch: [symbolsParam] },
)

function onSelect(symbol: string) {
  void router.push(`/market/${encodeURIComponent(symbol)}`)
}

function onRemove(symbol: string) {
  watchlist.remove(symbol)
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-semibold">Watchlist</h1>
        <p class="mt-1 text-gray-600">Your tickers are saved in this browser.</p>
      </div>
      <div class="flex gap-2">
        <v-btn variant="outlined" :loading="pending" @click="refresh()">Refresh</v-btn>
        <v-btn color="primary" to="/backtest">Run backtest</v-btn>
      </div>
    </div>

    <MarketWatchlistAddTicker :on-add="watchlist.add" />

    <v-alert v-if="error" type="error" variant="tonal">
      {{ error.message || 'Failed to load watchlist' }}
    </v-alert>

    <p v-if="watchlist.ready && !watchlist.symbols.value.length" class="text-gray-600">
      No tickers yet. Search above to add Vietnamese market symbols.
    </p>

    <MarketWatchlistTable
      v-else
      :items="data?.items ?? []"
      :loading="pending || !watchlist.ready"
      @select="onSelect"
      @remove="onRemove"
    />
  </div>
</template>
