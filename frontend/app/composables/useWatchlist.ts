const STORAGE_KEY = 'sf-watchlist'

const DEFAULT_SYMBOLS = ['E1VFVN30.VN', 'FUEVFVND.VN', '^VNINDEX.VN']

function normalizeSymbol(symbol: string): string {
  return symbol.trim().toUpperCase()
}

function loadFromStorage(): string[] {
  if (!import.meta.client) return [...DEFAULT_SYMBOLS]
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_SYMBOLS))
      return [...DEFAULT_SYMBOLS]
    }
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return [...DEFAULT_SYMBOLS]
    return parsed.map((s) => normalizeSymbol(String(s))).filter(Boolean)
  } catch {
    return [...DEFAULT_SYMBOLS]
  }
}

function saveToStorage(symbols: string[]) {
  if (!import.meta.client) return
  localStorage.setItem(STORAGE_KEY, JSON.stringify(symbols))
}

export function useWatchlist() {
  const symbols = ref<string[]>([])
  const ready = ref(false)

  onMounted(() => {
    symbols.value = loadFromStorage()
    ready.value = true
  })

  function has(symbol: string): boolean {
    const normalized = normalizeSymbol(symbol)
    return symbols.value.includes(normalized)
  }

  function add(symbol: string): boolean {
    const normalized = normalizeSymbol(symbol)
    if (!normalized || has(normalized)) return false
    symbols.value = [...symbols.value, normalized]
    saveToStorage(symbols.value)
    return true
  }

  function remove(symbol: string): void {
    const normalized = normalizeSymbol(symbol)
    symbols.value = symbols.value.filter((s) => s !== normalized)
    saveToStorage(symbols.value)
  }

  return { symbols, ready, has, add, remove }
}
