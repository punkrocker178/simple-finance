<script setup lang="ts">
import { useApi } from '~/composables/useApi'
import type { OhlcvResponse, TickerInfo } from '~/types/api'

const route = useRoute()
const ticker = computed(() => String(route.params.ticker))

useSeoMeta({
  title: () => `${ticker.value} | Simple Finance`,
  description: () => `Ticker detail and OHLCV for ${ticker.value}`,
})

const { apiFetch } = useApi()

/** vnstock history tops out ~9y; keep 8y headroom. */
const MAX_HISTORY_YEARS = 8

function toDateInput(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function yearsBefore(dateStr: string, years: number): string {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setFullYear(d.getFullYear() - years)
  return toDateInput(d)
}

const today = toDateInput(new Date())
const endDate = ref(today)
const startDate = ref(yearsBefore(today, 2))

const earliestStart = computed(() => yearsBefore(endDate.value || today, MAX_HISTORY_YEARS))

const dateError = computed(() => {
  if (!startDate.value || !endDate.value) return 'Start and end dates are required'
  if (endDate.value > today) return 'End cannot be in the future'
  if (startDate.value > endDate.value) return 'Start must be on or before end'
  if (startDate.value < earliestStart.value) {
    return `Start cannot be more than ${MAX_HISTORY_YEARS} years before end`
  }
  return null
})

const { data: info, error: infoError } = await useAsyncData(
  () => `ticker-info-${ticker.value}`,
  () => apiFetch<TickerInfo>(`/api/v1/market/tickers/${encodeURIComponent(ticker.value)}`),
  { watch: [ticker] },
)

const {
  data: ohlcv,
  pending: ohlcvPending,
  error: ohlcvError,
  refresh: refreshOhlcv,
} = await useAsyncData(
  () => `ticker-ohlcv-${ticker.value}-${startDate.value}-${endDate.value}`,
  () => {
    if (dateError.value) {
      throw createError({ statusCode: 400, message: dateError.value })
    }
    return apiFetch<OhlcvResponse>(
      `/api/v1/market/tickers/${encodeURIComponent(ticker.value)}/ohlcv`,
      { query: { start: startDate.value, end: endDate.value } },
    )
  },
  { watch: [ticker, startDate, endDate] },
)

const chartMode = ref<'candlestick' | 'line'>('candlestick')

function formatPrice(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <v-btn variant="text" to="/" class="mb-2 px-0">← Watchlist</v-btn>
      <h1 class="text-3xl font-semibold">{{ ticker }}</h1>
      <p class="mt-1 text-gray-600">
        {{ info?.longName || info?.shortName || 'Ticker detail' }}
      </p>
    </div>

    <v-alert v-if="infoError" type="error" variant="tonal">
      {{ infoError.message || 'Failed to load ticker info' }}
    </v-alert>

    <div v-if="info" class="flex flex-wrap gap-2">
      <v-chip v-if="info.exchange" size="small">{{ info.exchange }}</v-chip>
      <v-chip v-if="info.currency" size="small">{{ info.currency }}</v-chip>
      <v-chip v-if="info.sector" size="small">{{ info.sector }}</v-chip>
      <v-chip size="small">Price: {{ formatPrice(info.regularMarketPrice) }}</v-chip>
      <v-chip size="small">Prev: {{ formatPrice(info.previousClose) }}</v-chip>
      <v-chip size="small">52w H: {{ formatPrice(info.fiftyTwoWeekHigh) }}</v-chip>
      <v-chip size="small">52w L: {{ formatPrice(info.fiftyTwoWeekLow) }}</v-chip>
    </div>

    <div class="flex flex-wrap items-end gap-4">
      <v-text-field
        v-model="startDate"
        label="Start"
        type="date"
        density="comfortable"
        class="max-w-xs"
        :min="earliestStart"
        :max="endDate"
        hide-details
      />
      <v-text-field
        v-model="endDate"
        label="End"
        type="date"
        density="comfortable"
        class="max-w-xs"
        :min="startDate"
        :max="today"
        hide-details
      />
      <v-btn-toggle v-model="chartMode" mandatory density="comfortable" color="primary">
        <v-btn value="candlestick">Candlestick</v-btn>
        <v-btn value="line">Line</v-btn>
      </v-btn-toggle>
      <v-btn
        variant="outlined"
        :loading="ohlcvPending"
        :disabled="!!dateError"
        @click="refreshOhlcv()"
      >
        Reload
      </v-btn>
      <v-btn color="primary" :to="`/backtest?ticker=${encodeURIComponent(ticker)}`">
        Backtest
      </v-btn>
    </div>

    <v-alert v-if="dateError" type="warning" variant="tonal">
      {{ dateError }}
    </v-alert>

    <v-alert v-else-if="ohlcvError" type="error" variant="tonal">
      {{ ohlcvError.message || 'Failed to load OHLCV' }}
    </v-alert>

    <p v-if="ohlcv" class="text-sm text-gray-600">
      {{ ohlcv.bars.length }} bars from {{ ohlcv.start }} to {{ ohlcv.end }}
    </p>

    <ClientOnly>
      <ChartsOhlcvChart
        v-if="ohlcv?.bars?.length"
        :bars="ohlcv.bars"
        :mode="chartMode"
      />
      <template #fallback>
        <div class="flex h-96 items-center justify-center rounded-lg border border-dashed border-gray-300 text-gray-500">
          Loading chart…
        </div>
      </template>
    </ClientOnly>
  </div>
</template>
