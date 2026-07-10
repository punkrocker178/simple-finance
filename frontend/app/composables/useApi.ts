/**
 * API client that hits FastAPI directly during SSR and the Nitro proxy in the browser.
 */
export function useApi() {
  const config = useRuntimeConfig()

  const baseURL = import.meta.server
    ? String(config.apiTarget)
    : String(config.public.apiBase)

  function apiFetch<T>(
    path: string,
    opts?: Parameters<typeof $fetch<T>>[1],
  ): Promise<T> {
    return $fetch<T>(path, {
      baseURL,
      ...opts,
    })
  }

  function errorMessage(err: unknown, fallback: string): string {
    if (err && typeof err === 'object') {
      const e = err as { data?: { detail?: unknown }; message?: string; statusMessage?: string }
      const detail = e.data?.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) return JSON.stringify(detail)
      if (typeof e.statusMessage === 'string' && e.statusMessage) return e.statusMessage
      if (typeof e.message === 'string' && e.message) return e.message
    }
    if (err instanceof Error) return err.message
    return fallback
  }

  return { apiFetch, baseURL, errorMessage }
}
