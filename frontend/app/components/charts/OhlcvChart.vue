<script setup lang="ts">
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart, LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { OhlcvBar } from '~/types/api'

use([
  CanvasRenderer,
  CandlestickChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
])

const props = defineProps<{
  bars: OhlcvBar[]
  mode?: 'candlestick' | 'line'
}>()

const ready = ref(false)

onMounted(() => {
  nextTick(() => {
    ready.value = true
  })
})

const option = computed(() => {
  const dates = props.bars.map((b) => b.date)
  const candleData = props.bars.map((b) => [b.open, b.close, b.low, b.high])
  const closeData = props.bars.map((b) => b.close)
  const isCandle = (props.mode ?? 'candlestick') === 'candlestick'

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: isCandle ? ['OHLC'] : ['Close'] },
    grid: { left: 48, right: 24, top: 40, bottom: 64 },
    xAxis: { type: 'category', data: dates, boundaryGap: isCandle },
    yAxis: { type: 'value', scale: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    series: isCandle
      ? [
          {
            name: 'OHLC',
            type: 'candlestick',
            data: candleData,
          },
        ]
      : [
          {
            name: 'Close',
            type: 'line',
            data: closeData,
            showSymbol: false,
          },
        ],
  }
})
</script>

<template>
  <div class="chart-host">
    <VChart v-if="ready" :option="option" autoresize />
  </div>
</template>

<style scoped>
.chart-host {
  width: 100%;
  height: 24rem;
}
</style>
