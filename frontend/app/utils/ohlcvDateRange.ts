/** vnstock history tops out ~9y; keep 8y headroom. */
export const MAX_OHLCV_HISTORY_YEARS = 8

export function toDateInput(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function yearsBefore(dateStr: string, years: number): string {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setFullYear(d.getFullYear() - years)
  return toDateInput(d)
}

export function todayDateInput(): string {
  return toDateInput(new Date())
}

export function earliestStartForEnd(
  endDate: string,
  years = MAX_OHLCV_HISTORY_YEARS,
): string {
  return yearsBefore(endDate || todayDateInput(), years)
}

export function ohlcvDateError(
  startDate: string,
  endDate: string,
  years = MAX_OHLCV_HISTORY_YEARS,
): string | null {
  const today = todayDateInput()
  if (!startDate || !endDate) return 'Start and end dates are required'
  if (endDate > today) return 'End cannot be in the future'
  if (startDate > endDate) return 'Start must be on or before end'
  const earliest = earliestStartForEnd(endDate, years)
  if (startDate < earliest) {
    return `Start cannot be more than ${years} years before end`
  }
  return null
}
