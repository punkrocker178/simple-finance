<script setup lang="ts">
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, ScatterChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { BacktestSeries } from '~/types/api'
import { formatCash } from '~/utils/formatCash'

function formatCashAxis(value: number | string): string {
  const n = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(n)) return String(value)
  return formatCash(n)
}

use([
  CanvasRenderer,
  LineChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
])

const props = defineProps<{
  series: BacktestSeries
  startDate?: string | null
  endDate?: string | null
  effectiveStartDate?: string | null
  effectiveEndDate?: string | null
}>()

function fmtDate(value: string | null | undefined): string {
  if (!value) return ''
  return new Date(`${value}T00:00:00`).toLocaleDateString()
}

const periodLabel = computed(() => {
  const effectiveStart = props.effectiveStartDate
  const effectiveEnd = props.effectiveEndDate
  if (!effectiveStart || !effectiveEnd) return null

  const simulated = `${fmtDate(effectiveStart)} – ${fmtDate(effectiveEnd)}`
  const requestedStart = props.startDate
  const requestedEnd = props.endDate
  if (
    requestedStart
    && requestedEnd
    && (requestedStart !== effectiveStart || requestedEnd !== effectiveEnd)
  ) {
    return `Simulated period: ${simulated} · Requested range: ${fmtDate(requestedStart)} – ${fmtDate(requestedEnd)}`
  }
  return `Period: ${simulated}`
})

const ready = ref(false)

onMounted(() => {
  nextTick(() => {
    ready.value = true
  })
})

const primaryKey = computed(() => {
  const pv = props.series.portfolio_value
  if (pv.ma_crossover != null) return 'ma_crossover'
  if (pv.scheduled_dca != null) return 'scheduled_dca'
  return 'aggressive_dca'
})
const primaryName = computed(() =>
  ({
    ma_crossover: 'MA Crossover',
    scheduled_dca: 'Scheduled DCA',
    aggressive_dca: 'Aggressive DCA',
  } as Record<string, string>)[primaryKey.value],
)

const option = computed(() => {
  const { dates, portfolio_value, dip_buys, trade_signals } = props.series

  const seriesList: Record<string, unknown>[] = [
    {
      name: primaryName.value,
      type: 'line',
      data: portfolio_value[primaryKey.value],
      showSymbol: false,
    },
  ]

  if (primaryKey.value === 'ma_crossover') {
    seriesList.push(
      {
        name: 'Lump Sum',
        type: 'line',
        data: portfolio_value.lump_sum,
        showSymbol: false,
      },
      {
        name: 'Idle Cash',
        type: 'line',
        data: portfolio_value.idle_cash,
        showSymbol: false,
      },
    )
  } else {
    seriesList.push(
      {
        name: 'Standard DCA',
        type: 'line',
        data: portfolio_value.standard_dca,
        showSymbol: false,
      },
      {
        name: 'Lump Sum',
        type: 'line',
        data: portfolio_value.lump_sum,
        showSymbol: false,
      },
    )
  }

  if (dip_buys?.dates?.length) {
    const dateIndex = new Map(dates.map((d, i) => [d, i]))
    seriesList.push({
      name: 'Dip buys',
      type: 'scatter',
      data: dip_buys.dates.map((d, i) => {
        const idx = dateIndex.get(d)
        return idx === undefined ? null : [idx, dip_buys.portfolio_values[i]]
      }).filter(Boolean),
      symbolSize: 8,
    })
  }

  if (primaryKey.value === 'ma_crossover' && trade_signals) {
    const dateIndex = new Map(dates.map((d, i) => [d, i]))
    const scatter = (
      name: string,
      marker: { dates: string[]; portfolio_values: number[] },
      color: string,
      symbol: string,
    ) => {
      if (!marker.dates.length) return
      seriesList.push({
        name,
        type: 'scatter',
        data: marker.dates.map((d, i) => {
          const idx = dateIndex.get(d)
          return idx === undefined ? null : [idx, marker.portfolio_values[i]]
        }).filter(Boolean),
        symbol,
        symbolSize: 10,
        symbolRotate: name === 'Sell' ? 180 : 0,
        itemStyle: { color },
      })
    }
    scatter('Buy', trade_signals.buys, '#16a34a', 'triangle')
    scatter('Sell', trade_signals.sells, '#dc2626', 'triangle')
  }

  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: number | string) => formatCashAxis(value),
    },
    legend: { data: seriesList.map((s) => String(s.name)) },
    grid: { left: 72, right: 24, top: 48, bottom: 64 },
    xAxis: { type: 'category', data: dates },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: { formatter: (value: number) => formatCashAxis(value) },
    },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    series: seriesList,
  }
})
</script>

<template>
  <div class="chart-host">
    <p v-if="periodLabel" class="mb-2 text-sm text-gray-600">
      {{ periodLabel }}
    </p>
    <VChart v-if="ready" :option="option" autoresize />
  </div>
</template>

<style scoped>
.chart-host {
  width: 100%;
  height: 24rem;
}
</style>
