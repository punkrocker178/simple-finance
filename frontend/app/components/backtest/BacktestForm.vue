<script setup lang="ts">
import { vMaska } from 'maska/vue'
import type { BacktestRequest } from '~/types/api'
import {
  cashInputMask,
  formatCash,
  unmaskCash,
} from '~/utils/formatCash'
import {
  earliestStartForEnd,
  ohlcvDateError,
  todayDateInput,
} from '~/utils/ohlcvDateRange'

const model = defineModel<BacktestRequest>({ required: true })

defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: []
}>()

const today = todayDateInput()
const earliestStart = computed(() => earliestStartForEnd(model.value.end_date))
const dateError = computed(() =>
  ohlcvDateError(model.value.start_date, model.value.end_date),
)

const isMa = computed(() => model.value.strategy === 'ma_crossover')
const isAggressive = computed(() => model.value.strategy === 'aggressive_dca')
const isScheduled = computed(() => model.value.strategy === 'scheduled_dca')

const cashLabel = computed(() =>
  model.value.cadence === 'monthly' ? 'Monthly cash' : 'Period cash',
)

function cashDisplay(n: number | null | undefined): string {
  return formatCash(n ?? 0)
}

const initialCashText = ref(cashDisplay(model.value.initial_cash))
const monthlyCashText = ref(cashDisplay(model.value.monthly_cash))
const initialCashMask = cashInputMask((n) => {
  model.value.initial_cash = n
})
const monthlyCashMask = cashInputMask((n) => {
  model.value.monthly_cash = n
})

watch(
  () => model.value.initial_cash,
  (n) => {
    if (unmaskCash(initialCashText.value) !== String(n ?? 0)) {
      initialCashText.value = cashDisplay(n)
    }
  },
)
watch(
  () => model.value.monthly_cash,
  (n) => {
    if (unmaskCash(monthlyCashText.value) !== String(n ?? 0)) {
      monthlyCashText.value = cashDisplay(n)
    }
  },
)

const weekdayItems = [
  { title: 'Monday', value: 0 },
  { title: 'Tuesday', value: 1 },
  { title: 'Wednesday', value: 2 },
  { title: 'Thursday', value: 3 },
  { title: 'Friday', value: 4 },
]

function onSubmit() {
  if (dateError.value) return
  emit('submit')
}
</script>

<template>
  <v-form class="flex flex-col gap-4" @submit.prevent="onSubmit">
    <div class="grid gap-4 md:grid-cols-2">
      <v-text-field v-model="model.ticker" label="Ticker" density="comfortable" />
      <v-select
        v-model="model.strategy"
        :items="[
          { title: 'Aggressive DCA', value: 'aggressive_dca' },
          { title: 'Scheduled DCA', value: 'scheduled_dca' },
          { title: 'MA Crossover', value: 'ma_crossover' },
        ]"
        label="Strategy"
        density="comfortable"
      />
      <v-switch
        v-if="isAggressive"
        v-model="model.optimize"
        label="Optimize parameters"
        color="primary"
        hide-details
      />
      <v-text-field
        v-model="model.start_date"
        label="Start date"
        type="date"
        density="comfortable"
        :min="earliestStart"
        :max="model.end_date"
        hide-details
      />
      <v-text-field
        v-model="model.end_date"
        label="End date"
        type="date"
        density="comfortable"
        :min="model.start_date"
        :max="today"
        hide-details
      />
      <v-text-field
        v-model="initialCashText"
        v-maska="initialCashMask"
        label="Initial cash"
        type="text"
        inputmode="numeric"
        density="comfortable"
      />
      <v-text-field
        v-model="monthlyCashText"
        v-maska="monthlyCashMask"
        v-if="!isMa"
        :label="cashLabel"
        type="text"
        inputmode="numeric"
        density="comfortable"
      />
      <v-text-field
        v-model.number="model.fee_rate"
        label="Fee rate (fraction)"
        type="number"
        step="0.0001"
        density="comfortable"
        hint="e.g. 0.0015 = 0.15%"
        persistent-hint
      />
      <template v-if="isAggressive">
        <v-text-field
          v-model.number="model.lookback"
          label="Lookback (optional)"
          type="number"
          density="comfortable"
          clearable
        />
        <v-text-field
          v-model.number="model.drawdown_thresh"
          label="Drawdown thresh (optional)"
          type="number"
          step="0.01"
          density="comfortable"
          clearable
        />
        <v-text-field
          v-model.number="model.sma_period"
          label="SMA period (optional)"
          type="number"
          density="comfortable"
          clearable
        />
      </template>
      <template v-if="isMa">
        <v-select
          v-model="model.ma_type"
          :items="[
            { title: 'SMA', value: 'sma' },
            { title: 'EMA', value: 'ema' },
          ]"
          label="MA type"
          density="comfortable"
        />
        <v-text-field
          v-model.number="model.fast"
          label="Fast period"
          type="number"
          min="1"
          density="comfortable"
        />
        <v-text-field
          v-model.number="model.slow"
          label="Slow period"
          type="number"
          min="1"
          density="comfortable"
        />
      </template>
      <template v-if="isScheduled">
        <v-select
          v-model="model.cadence"
          :items="[
            { title: 'Weekly', value: 'weekly' },
            { title: 'Biweekly', value: 'biweekly' },
            { title: 'Monthly', value: 'monthly' },
          ]"
          label="Cadence"
          density="comfortable"
        />
        <v-text-field
          v-if="model.cadence === 'monthly'"
          v-model.number="model.day_of_month"
          label="Day of month"
          type="number"
          min="1"
          max="28"
          density="comfortable"
        />
        <v-select
          v-if="model.cadence === 'weekly' || model.cadence === 'biweekly'"
          v-model="model.weekday"
          :items="weekdayItems"
          label="Weekday"
          density="comfortable"
        />
        <v-text-field
          v-model.number="model.skip_after_buy_n"
          label="Skip after buy N"
          type="number"
          min="0"
          density="comfortable"
        />
      </template>
    </div>

    <v-alert v-if="dateError" type="warning" variant="tonal">
      {{ dateError }}
    </v-alert>

    <div>
      <v-btn type="submit" color="primary" :loading="loading" :disabled="!!dateError">
        Run backtest
      </v-btn>
    </div>
  </v-form>
</template>
