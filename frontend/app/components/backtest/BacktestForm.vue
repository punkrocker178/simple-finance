<script setup lang="ts">
import type { BacktestRequest } from '~/types/api'
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

function onSubmit() {
  if (dateError.value) return
  emit('submit')
}
</script>

<template>
  <v-form class="flex flex-col gap-4" @submit.prevent="onSubmit">
    <div class="grid gap-4 md:grid-cols-2">
      <v-text-field v-model="model.ticker" label="Ticker" density="comfortable" />
      <v-switch v-model="model.optimize" label="Optimize parameters" color="primary" hide-details />
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
        v-model.number="model.initial_cash"
        label="Initial cash"
        type="number"
        density="comfortable"
      />
      <v-text-field
        v-model.number="model.monthly_cash"
        label="Monthly cash"
        type="number"
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
    </div>

    <v-alert v-if="dateError" type="warning" variant="tonal">
      {{ dateError }}
    </v-alert>

    <div>
      <v-btn type="submit" color="primary" :loading="loading" :disabled="!!dateError">
        Run DCA backtest
      </v-btn>
    </div>
  </v-form>
</template>
