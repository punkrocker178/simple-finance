<script setup lang="ts">
import type { BacktestSeries } from '~/types/api'

useSeoMeta({
  title: 'DCA Backtest | Simple Finance',
  description: 'Run Aggressive DCA backtests',
})

const route = useRoute()
const store = useBacktestStore()

if (typeof route.query.ticker === 'string' && route.query.ticker) {
  store.form.ticker = route.query.ticker
}

const series = computed(() => store.lastReport?.series as BacktestSeries | null | undefined)

async function onSubmit() {
  try {
    await store.runDca()
  } catch {
    // error stored on store.error
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-semibold">DCA Backtest</h1>
        <p class="mt-1 text-gray-600">
          Run Aggressive DCA against Standard DCA and lump-sum benchmarks.
        </p>
      </div>
      <v-btn variant="outlined" to="/backtest/history">View history</v-btn>
    </div>

    <BacktestForm
      v-model="store.form"
      :loading="store.pending"
      @submit="onSubmit"
    />

    <v-alert v-if="store.error" type="error" variant="tonal">
      {{ store.error }}
    </v-alert>

    <template v-if="store.lastReport">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-2xl font-semibold">
          Results — {{ store.lastReport.ticker }}
        </h2>
        <v-btn
          variant="text"
          :to="`/backtest/${store.lastReport.id}`"
        >
          Open saved run
        </v-btn>
      </div>

      <BacktestMetricsCards :metrics="store.lastReport.metrics" />

      <ClientOnly>
        <ChartsBacktestSeriesChart
          v-if="series"
          :series="series"
          :start-date="store.lastReport.start_date"
          :end-date="store.lastReport.end_date"
          :effective-start-date="store.lastReport.effective_start_date"
          :effective-end-date="store.lastReport.effective_end_date"
        />
        <template #fallback>
          <div class="flex h-96 items-center justify-center rounded-lg border border-dashed border-gray-300 text-gray-500">
            Loading chart…
          </div>
        </template>
      </ClientOnly>
    </template>
  </div>
</template>
