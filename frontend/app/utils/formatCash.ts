import { Mask, type MaskaDetail } from 'maska'

export const cashNumberOptions = {
  locale: 'en',
  fraction: 0,
  unsigned: true,
} as const

export const cashMaskOptions = { number: cashNumberOptions }

const cashMasker = new Mask(cashMaskOptions)

/** Display helper: nullish/NaN → em dash. */
export function formatCash(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  return cashMasker.masked(n)
}

export function unmaskCash(value: string): string {
  return cashMasker.unmasked(value)
}

export function cashInputMask(set: (n: number) => void) {
  return {
    number: { ...cashNumberOptions },
    onMaska: (detail: MaskaDetail) => {
      set(detail.unmasked === '' ? 0 : Number(detail.unmasked))
    },
  }
}

const CASH_PARAM_KEYS = ['initial_cash', 'monthly_cash'] as const

/** Clone params and replace known cash fields with formatted strings. */
export function formatParamsCash(
  params: Record<string, unknown> | null | undefined,
): Record<string, unknown> {
  if (!params) return {}
  const out: Record<string, unknown> = { ...params }
  for (const key of CASH_PARAM_KEYS) {
    const v = out[key]
    if (typeof v === 'number') out[key] = formatCash(v)
  }
  return out
}
