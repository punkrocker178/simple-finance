<script setup lang="ts">
import { useApi } from '~/composables/useApi'
import type { BacktestReport, BacktestSeries } from '~/types/api'

const route = useRoute()
const runId = computed(() => String(route.params.id))

useSeoMeta({
  title: () => `Backtest ${runId.value} | Simple Finance`,
  description: 'Stored DCA backtest report',
})

const { apiFetch } = useApi()

const { data: report, pending, error } = await useAsyncData(
  () => `backtest-run-${runId.value}`,
  () => apiFetch<BacktestReport>(`/api/v1/backtest/runs/${runId.value}`),
  { watch: [runId] },
)

const series = computed(() => report.value?.series as BacktestSeries | null | undefined)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <v-btn variant="text" to="/backtest/history" class="mb-2 px-0">← History</v-btn>
      <h1 class="text-3xl font-semibold">
        {{ report?.ticker || 'Backtest run' }}
      </h1>
      <p v-if="report" class="mt-1 text-gray-600">
        {{ report.strategy }} · {{ report.id }}
        <span v-if="report.created_at">
          · {{ new Date(report.created_at).toLocaleString() }}
        </span>
      </p>
    </div>

    <v-progress-linear v-if="pending" indeterminate color="primary" />

    <v-alert v-if="error" type="error" variant="tonal">
      {{ error.message || 'Failed to load run' }}
    </v-alert>

    <template v-if="report">
      <div class="rounded-lg border border-gray-200 p-4 text-sm">
        <h2 class="mb-2 text-lg font-semibold">Parameters</h2>
        <pre class="overflow-x-auto whitespace-pre-wrap">{{ JSON.stringify(report.params, null, 2) }}</pre>
      </div>

      <BacktestMetricsCards :metrics="report.metrics" />

      <ClientOnly>
        <ChartsBacktestSeriesChart v-if="series" :series="series" />
        <template #fallback>
          <div class="flex h-96 items-center justify-center rounded-lg border border-dashed border-gray-300 text-gray-500">
            Loading chart…
          </div>
        </template>
      </ClientOnly>
    </template>
  </div>
</template>
