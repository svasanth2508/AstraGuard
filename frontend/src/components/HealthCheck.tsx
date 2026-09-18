import { Activity, CheckCircle2, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { HealthResponse } from '../types'

type State =
  | { kind: 'loading' }
  | { kind: 'success'; data: HealthResponse }
  | { kind: 'error'; message: string }

export function HealthCheck() {
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    let cancelled = false

    api.health()
      .then((data) => {
        if (!cancelled) setState({ kind: 'success', data })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        const message = error instanceof Error ? error.message : 'Unknown connection error'
        setState({ kind: 'error', message })
      })

    return () => {
      cancelled = true
    }
  }, [])

  if (state.kind === 'loading') {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/70 p-4 text-slate-300">
        <Activity className="h-5 w-5 animate-pulse" />
        Checking backend communication...
      </div>
    )
  }

  if (state.kind === 'error') {
    return (
      <div className="rounded-xl border border-red-900/70 bg-red-950/40 p-4">
        <div className="flex items-center gap-2 font-semibold text-red-300">
          <XCircle className="h-5 w-5" /> Backend connection failed
        </div>
        <p className="mt-2 text-sm text-red-200/80">{state.message}</p>
        <p className="mt-1 text-xs text-slate-400">Expected API: http://127.0.0.1:8000</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-emerald-900/60 bg-emerald-950/25 p-4">
      <div className="flex items-center gap-2 font-semibold text-emerald-300">
        <CheckCircle2 className="h-5 w-5" /> Frontend ↔ Backend connected
      </div>
      <div className="mt-3 grid gap-2 text-sm text-slate-300 sm:grid-cols-3">
        <div><span className="text-slate-500">Status:</span> {state.data.status}</div>
        <div><span className="text-slate-500">Service:</span> {state.data.service}</div>
        <div><span className="text-slate-500">Time:</span> {new Date(state.data.timestamp).toLocaleTimeString()}</div>
      </div>
    </div>
  )
}
