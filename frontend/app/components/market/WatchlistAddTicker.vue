<script setup lang="ts">
import { useMarketApi } from '~/composables/useMarketApi'
import type { TickerSearchItem } from '~/types/api'

const props = defineProps<{
  onAdd: (symbol: string) => boolean
}>()

const { searchTickers } = useMarketApi()

const search = ref('')
const selected = ref<TickerSearchItem | null>(null)
const items = ref<TickerSearchItem[]>([])
const loading = ref(false)
const duplicateHint = ref(false)

let debounceTimer: ReturnType<typeof setTimeout> | undefined
let abortController: AbortController | undefined

watch(search, (query) => {
  duplicateHint.value = false
  if (debounceTimer) clearTimeout(debounceTimer)
  const trimmed = query.trim()
  if (!trimmed) {
    items.value = []
    return
  }
  debounceTimer = setTimeout(() => void fetchResults(trimmed), 300)
})

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  abortController?.abort()
})

async function fetchResults(query: string) {
  abortController?.abort()
  abortController = new AbortController()
  const { signal } = abortController
  loading.value = true
  try {
    const data = await searchTickers(query, { limit: 20, signal })
    if (signal.aborted) return
    items.value = data.items
  } catch {
    if (signal.aborted) return
    items.value = []
  } finally {
    if (!signal.aborted) loading.value = false
  }
}

function itemTitle(item: TickerSearchItem): string {
  const name = item.short_name || item.long_name
  return name ? `${item.symbol} — ${name}` : item.symbol
}

function tryAdd(symbol: string) {
  const added = props.onAdd(symbol)
  if (!added) {
    duplicateHint.value = true
    return
  }
  duplicateHint.value = false
  search.value = ''
  selected.value = null
  items.value = []
}

function onSelect(item: TickerSearchItem | null) {
  if (!item) return
  tryAdd(item.symbol)
}
</script>

<template>
  <div class="flex flex-wrap items-start gap-3">
    <v-autocomplete
      v-model="selected"
      v-model:search="search"
      :items="items"
      :loading="loading"
      :item-title="itemTitle"
      item-value="symbol"
      return-object
      label="Add ticker"
      placeholder="Search Vietnamese tickers…"
      density="comfortable"
      hide-details="auto"
      no-filter
      clearable
      class="min-w-72 max-w-md flex-1"
      @update:model-value="onSelect"
    />
    <v-btn
      color="primary"
      variant="outlined"
      :disabled="!selected"
      @click="selected && tryAdd(selected.symbol)"
    >
      Add
    </v-btn>
    <p v-if="duplicateHint" class="w-full text-sm text-amber-700">
      Already in watchlist
    </p>
  </div>
</template>
