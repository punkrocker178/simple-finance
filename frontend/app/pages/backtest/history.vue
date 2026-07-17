<script setup lang="ts">
import { useBacktestApi } from '~/composables/useBacktestApi'

useSeoMeta({
  title: 'Backtest History | Simple Finance',
  description: 'Past backtest runs',
})

const { listRuns } = useBacktestApi()
const router = useRouter()
const tickerFilter = ref('')

const { data, pending, error, refresh } = await useAsyncData(
  'backtest-runs',
  () =>
    listRuns(tickerFilter.value ? { ticker: tickerFilter.value } : undefined),
  { watch: [tickerFilter] },
)

function onSelect(id: string) {
  void router.push(`/backtest/${id}`)
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-semibold">Backtest history</h1>
        <p class="mt-1 text-gray-600">Persisted backtest runs from the API.</p>
      </div>
      <v-btn color="primary" to="/backtest">New backtest</v-btn>
    </div>

    <div class="flex flex-wrap items-end gap-4">
      <v-text-field
        v-model="tickerFilter"
        label="Filter by ticker"
        density="comfortable"
        clearable
        class="max-w-xs"
        hide-details
      />
      <v-btn variant="outlined" :loading="pending" @click="refresh()">Refresh</v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal">
      {{ error.message || 'Failed to load runs' }}
    </v-alert>

    <BacktestRunsTable
      :items="data?.items ?? []"
      :loading="pending"
      @select="onSelect"
    />
  </div>
</template>
