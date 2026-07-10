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
}>()

const option = computed(() => {
  const { dates, portfolio_value, dip_buys } = props.series

  const seriesList: Record<string, unknown>[] = [
    {
      name: 'Aggressive DCA',
      type: 'line',
      data: portfolio_value.aggressive_dca,
      showSymbol: false,
    },
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
  ]

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

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: seriesList.map((s) => String(s.name)) },
    grid: { left: 56, right: 24, top: 48, bottom: 64 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', scale: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    series: seriesList,
  }
})
</script>

<template>
  <VChart class="h-96 w-full" :option="option" autoresize />
</template>
