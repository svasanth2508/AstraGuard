import type { Counterfactual, HealthResponse, HistoricalIncident, Snapshot, SystemStatus } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const REQUEST_TIMEOUT_MS = 5000

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(init?.headers ?? {}),
      },
    })

    if (!response.ok) {
      let message = `API request failed with status ${response.status}`
      try {
        const body = (await response.json()) as { detail?: string }
        if (body.detail) message = body.detail
      } catch {
        const text = await response.text().catch(() => '')
        if (text) message = text
      }
      throw new Error(message)
    }

    return response.json() as Promise<T>
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(`Backend request timed out after ${REQUEST_TIMEOUT_MS / 1000}s`)
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

export const api = {
  health: () => request<HealthResponse>('/api/health'),
  system: () => request<SystemStatus>('/api/system'),
  snapshot: () => request<Snapshot>('/api/snapshot'),
  inject: (scenario: string) => request<Snapshot>(`/api/incidents/inject/${scenario}`, { method: 'POST' }),
  counterfactual: (incidentId: string) => request<Counterfactual>(`/api/incidents/${incidentId}/counterfactual`, { method: 'POST' }),
  approve: (incidentId: string) => request<Snapshot>(`/api/incidents/${incidentId}/approve`, { method: 'POST' }),
  reject: (incidentId: string) => request<Snapshot>(`/api/incidents/${incidentId}/reject`, { method: 'POST' }),
  verify: (incidentId: string) => request<Snapshot>(`/api/incidents/${incidentId}/verify`, { method: 'POST' }),
  rollback: (incidentId: string) => request<Snapshot>(`/api/incidents/${incidentId}/rollback`, { method: 'POST' }),
  forceFailure: (enabled: boolean) => request<Snapshot>(`/api/system/force-remediation-failure/${enabled}`, { method: 'POST' }),
  reset: () => request<Snapshot>('/api/system/reset', { method: 'POST' }),
  history: () => request<HistoricalIncident[]>('/api/history'),
}
