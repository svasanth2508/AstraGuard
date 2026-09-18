import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Database,
  Gauge,
  GitMerge,
  Network,
  Mail,
  Menu,
  RefreshCw,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Siren,
  XCircle,
  Zap,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from './services/api'
import ServiceGraph from './components/ServiceGraph'
import type { Metrics, Service, Snapshot } from './types'

const scenarios = [
  { id: 'db-overload', label: 'Inject DB Overload', icon: Database },
  { id: 'payment-failure', label: 'Inject Payment Failure', icon: Zap },
  { id: 'network-latency', label: 'Inject Network Latency', icon: Network },
  { id: 'traffic-spike', label: 'Inject Traffic Spike', icon: Activity },
]


function lifecycleStage(snapshot: Snapshot) {
  const incident = snapshot.incident
  if (!snapshot.simulation.active && !incident) return 0
  if (snapshot.alerts.length > 0 && !incident) return 1
  if (incident && !incident.rca) return 2
  if (incident?.rca && !incident.counterfactual) return 3
  if (incident?.counterfactual && incident.status === 'OPEN') return 4
  if (incident?.status === 'REMEDIATING' || incident?.status === 'VERIFYING') return 5
  if (incident?.status === 'RESOLVED' || incident?.status === 'CLOSED') return 6
  return 2
}

const lifecycleSteps = [
  'Observe',
  'Detect',
  'Correlate',
  'Diagnose',
  'Decide',
  'Verify',
  'Learn',
]

const commandNav = [
  { href: '#overview', label: 'Overview' },
  { href: '#adaptive', label: 'Adaptive' },
  { href: '#incidents', label: 'Incidents' },
  { href: '#topology', label: 'Topology' },
  { href: '#audit', label: 'Audit' },
]

function metricCards(metrics: Metrics) {
  return [
    ['DB CPU', `${metrics.database_cpu.toFixed(1)}%`, 'Healthy ~42%'],
    ['DB Connections', `${metrics.database_connections.toFixed(1)}%`, 'Healthy ~45%'],
    ['Payment P95', `${Math.round(metrics.payment_latency_ms)} ms`, 'Healthy ~240 ms'],
    ['Checkout Errors', `${metrics.checkout_error_rate.toFixed(1)}%`, 'Healthy ~1%'],
    ['API 5xx', `${metrics.api_5xx_rate.toFixed(1)}%`, 'Healthy ~1%'],
    ['Failed Txns', `${Math.round(metrics.failed_transactions)}`, 'Healthy 0'],
  ]
}



export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [lastSync, setLastSync] = useState<Date | null>(null)
  const [navOpen, setNavOpen] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const data = await api.snapshot()
      setSnapshot(data)
      setLastSync(new Date())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Backend unavailable')
    }
  }, [])

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => void refresh(), 1000)
    return () => window.clearInterval(timer)
  }, [refresh])

  const inject = async (scenario: string) => {
    try {
      setBusy(scenario)
      setSnapshot(await api.inject(scenario))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to inject incident')
    } finally {
      setBusy(null)
    }
  }

  const runCounterfactual = async () => {
    if (!snapshot?.incident) return
    try {
      setBusy('counterfactual')
      await api.counterfactual(snapshot.incident.id)
      await refresh()
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to run counterfactual test')
    } finally {
      setBusy(null)
    }
  }

  const approveRemediation = async () => {
    if (!snapshot?.incident) return
    try {
      setBusy('approve')
      setSnapshot(await api.approve(snapshot.incident.id))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to approve remediation')
    } finally {
      setBusy(null)
    }
  }

  const rejectRemediation = async () => {
    if (!snapshot?.incident) return
    try {
      setBusy('reject')
      setSnapshot(await api.reject(snapshot.incident.id))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reject remediation')
    } finally {
      setBusy(null)
    }
  }

  const forceFailure = async (enabled: boolean) => {
    try {
      setBusy('failure-mode')
      setSnapshot(await api.forceFailure(enabled))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to change failure test mode')
    } finally {
      setBusy(null)
    }
  }

  const manualRollback = async () => {
    if (!snapshot?.incident) return
    try {
      setBusy('rollback')
      setSnapshot(await api.rollback(snapshot.incident.id))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start rollback')
    } finally {
      setBusy(null)
    }
  }

  const reset = async () => {
    try {
      setBusy('reset')
      setSnapshot(await api.reset())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reset simulator')
    } finally {
      setBusy(null)
    }
  }

  const chartData = useMemo(
    () =>
      (snapshot?.history ?? []).map((point) => ({
        ...point,
        time: new Date(point.timestamp).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' }),
      })),
    [snapshot],
  )

  if (!snapshot) {
    return (
      <main className="app-shell flex min-h-screen items-center justify-center text-slate-100">
        <div className="loading-panel text-center">
          <div className="loading-orbit" />
          <Activity className="mx-auto mb-4 h-9 w-9 animate-pulse text-cyan-300" />
          <p className="font-semibold">Connecting to AstraGuard backend…</p>
          {error && <p className="mt-2 text-sm text-red-300">{error}</p>}
        </div>
      </main>
    )
  }

  const { system, simulation, metrics, services, alerts, incident, adaptive_monitoring } = snapshot
  const rca = incident?.rca
  const currentStage = lifecycleStage(snapshot)

  return (
    <main className="app-shell min-h-screen text-slate-100">
      <div className="ambient-orb ambient-orb-one" />
      <div className="ambient-orb ambient-orb-two" />
      <div className="noise-layer" />
      <div className="mx-auto max-w-[1600px] px-4 py-4 md:px-7 lg:py-6">
        <header id="overview" className="premium-header mb-5">
          <div className="brand-lockup">
            <div className="eyebrow mb-2 flex items-center gap-2 text-cyan-300">
              <ShieldCheck className="h-6 w-6" />
              <span className="text-xs font-bold uppercase tracking-[0.28em]">Autonomous Incident Command Center</span>
            </div>
            <div className="flex items-center gap-3"><h1 className="brand-title text-4xl font-black tracking-tight">AstraGuard</h1><span className="hidden rounded-full border border-cyan-400/20 bg-cyan-400/5 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-cyan-200 sm:inline">Live</span></div>
            <p className="mt-1 text-sm text-slate-400">Autonomous learning · streaming anomaly detection · verified feedback loop</p>
          </div>
          <div className="header-actions flex flex-wrap items-center gap-2">
            <button aria-label="Toggle navigation" onClick={() => setNavOpen((value) => !value)} className="icon-button lg:hidden"><Menu className="h-4 w-4" /></button>
            <span className="status-pill api-pill">
              API CONNECTED{lastSync ? ` · ${lastSync.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}` : ''}
            </span>
            <span className={`status-pill px-4 py-2 text-sm font-semibold ${simulation.active ? 'border-red-500/40 bg-red-950/40 text-red-300' : 'border-emerald-500/30 bg-emerald-950/30 text-emerald-300'}`}>
              {system.system_status}
            </span>
            <button
              onClick={() => void reset()}
              disabled={busy !== null}
              className="premium-button secondary-button inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              <RefreshCw className="h-4 w-4" /> Reset Demo
            </button>
          </div>
        </header>

        <nav className={`command-nav ${navOpen ? 'is-open' : ''}`} aria-label="Command center sections">
          <div className="command-nav-inner">
            <div className="command-nav-brand"><Sparkles className="h-3.5 w-3.5" /><span>Command view</span></div>
            <div className="command-nav-links">
              {commandNav.map((item) => (
                <a key={item.href} href={item.href} onClick={() => setNavOpen(false)}>{item.label}</a>
              ))}
            </div>
            <div className="command-nav-meta">{lastSync ? `Synced ${lastSync.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Connecting…'}</div>
          </div>
        </nav>

        {error && <div className="error-banner mb-4"><div><p className="font-bold text-red-100">Connection issue</p><p className="mt-1 text-sm text-red-200/80">{error}</p></div><button onClick={() => void refresh()} className="premium-button secondary-button px-3 py-2 text-xs">Retry</button></div>}

        <section className="kpi-grid section-reveal mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <article className="kpi-card p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Active Incidents</p>
            <p className="mt-2 text-3xl font-black">{system.active_incidents}</p>
          </article>
          <article className="kpi-card p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Live Alerts</p>
            <p className="mt-2 text-3xl font-black">{alerts.length}</p>
          </article>
          <article className="kpi-card p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Services Healthy</p>
            <p className="mt-2 text-3xl font-black text-emerald-300">{system.services_healthy}/{system.services_total}</p>
          </article>
          <article className="kpi-card p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">RCA Confidence</p>
            <p className="mt-2 text-3xl font-black text-cyan-300">{incident ? `${incident.confidence}%` : '—'}</p>
          </article>
        </section>

        <section id="adaptive" className="section-reveal mb-5 grid gap-4 xl:grid-cols-[1.25fr_.75fr]">
          <article className="command-card overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70">
            <div className="border-b border-slate-800 bg-gradient-to-r from-cyan-950/30 via-slate-900/10 to-transparent p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-cyan-300">
                    <BrainCircuit className="h-5 w-5" />
                    <p className="text-xs font-bold uppercase tracking-[0.22em]">Adaptive Monitoring</p>
                  </div>
                  <h2 className="mt-2 text-xl font-black">Live operational pattern</h2>
                  <p className="mt-1 max-w-2xl text-sm text-slate-400">Learns healthy operating behavior continuously, pauses learning during incidents, and only learns incident labels after the outcome is verified.</p>
                </div>
                <span className={`rounded-full border px-3 py-1.5 text-xs font-black tracking-wide ${
                  adaptive_monitoring.pattern === 'ANOMALOUS'
                    ? 'border-red-500/40 bg-red-950/50 text-red-300'
                    : adaptive_monitoring.pattern === 'SUSPICIOUS'
                      ? 'border-amber-500/40 bg-amber-950/40 text-amber-300'
                      : 'border-emerald-500/30 bg-emerald-950/30 text-emerald-300'
                }`}>
                  {adaptive_monitoring.pattern}
                </span>
              </div>
            </div>

            <div className="p-5">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                  <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.16em] text-slate-500">
                    <span>Anomaly Score</span><Gauge className="h-4 w-4" />
                  </div>
                  <p className="mt-2 text-3xl font-black">{Math.round(adaptive_monitoring.anomaly_score * 100)}%</p>
                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div className={`h-full rounded-full transition-all ${adaptive_monitoring.anomaly_score >= 0.7 ? 'bg-red-400' : adaptive_monitoring.anomaly_score >= 0.45 ? 'bg-amber-400' : 'bg-emerald-400'}`} style={{ width: `${Math.max(3, Math.min(100, adaptive_monitoring.anomaly_score * 100))}%` }} />
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                  <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Operational Pattern</p>
                  <p className="mt-2 text-lg font-black text-cyan-200">{adaptive_monitoring.predicted_incident.replaceAll('_', ' ')}</p>
                  <p className="mt-1 text-xs text-slate-500">{Math.round(adaptive_monitoring.prediction_confidence * 100)}% confidence</p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                  <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Learning State</p>
                  <p className={`mt-2 text-lg font-black ${adaptive_monitoring.learning_enabled ? 'text-emerald-300' : 'text-amber-300'}`}>{adaptive_monitoring.learning_enabled ? 'ADAPTING' : 'PAUSED'}</p>
                  <p className="mt-1 text-xs text-slate-500">Baseline: {adaptive_monitoring.baseline_status}</p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                  <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Healthy Samples</p>
                  <p className="mt-2 text-2xl font-black">{adaptive_monitoring.observations_learned}</p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                  <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Verified Incidents Learned</p>
                  <p className="mt-2 text-2xl font-black">{adaptive_monitoring.confirmed_incidents_learned}</p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                  <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Baseline Drift</p>
                  <p className="mt-2 text-2xl font-black">{adaptive_monitoring.drift_events}</p>
                  <p className="mt-1 text-xs text-slate-500">Detected drift events</p>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                <span className="rounded-full border border-slate-800 bg-slate-950/60 px-2.5 py-1">{adaptive_monitoring.model.anomaly_detector}</span>
                <span className="rounded-full border border-slate-800 bg-slate-950/60 px-2.5 py-1">{adaptive_monitoring.model.incident_classifier}</span>
                <span className="rounded-full border border-slate-800 bg-slate-950/60 px-2.5 py-1">{adaptive_monitoring.model.drift_detector}</span>
              </div>
            </div>
          </article>

          <article className="command-card rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="flex items-center gap-2">
              <GitMerge className="h-5 w-5 text-violet-300" />
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Autonomous Resolution Loop</p>
                <h2 className="mt-1 text-lg font-black">Current decision stage</h2>
              </div>
            </div>
            <div className="mt-5 space-y-2">
              {lifecycleSteps.map((step, index) => {
                const active = index === currentStage
                const complete = index < currentStage
                return (
                  <div key={step} className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 transition ${active ? 'border-cyan-500/40 bg-cyan-950/30' : complete ? 'border-emerald-500/20 bg-emerald-950/10' : 'border-slate-800 bg-slate-950/50'}`}>
                    <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-black ${active ? 'bg-cyan-400 text-slate-950' : complete ? 'bg-emerald-400/20 text-emerald-300' : 'bg-slate-800 text-slate-500'}`}>{index + 1}</div>
                    <div className="flex-1">
                      <p className={`text-sm font-bold ${active ? 'text-cyan-200' : complete ? 'text-emerald-200' : 'text-slate-400'}`}>{step}</p>
                    </div>
                    {complete && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                    {active && <Activity className="h-4 w-4 animate-pulse text-cyan-300" />}
                  </div>
                )
              })}
            </div>
            <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs leading-5 text-slate-400">
              {adaptive_monitoring.learning_enabled
                ? 'The system is learning from verified healthy telemetry.'
                : 'Learning is paused while the incident is active so failure behavior is not absorbed into the healthy baseline.'}
            </div>
          </article>
        </section>

        <section id="incidents" className="section-reveal premium-surface mb-5 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Incident Injection</p>
              <p className="mt-1 text-sm text-slate-400">Inject a controlled failure and watch alerts become one explainable incident.</p>
            </div>
            {simulation.active && (
              <div className="min-w-64">
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span>{simulation.scenario_label}</span><span>{Math.round(simulation.progress)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full bg-cyan-400 transition-all" style={{ width: `${simulation.progress}%` }} />
                </div>
              </div>
            )}
          </div>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {scenarios.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => void inject(id)}
                disabled={busy !== null}
                className="scenario-button flex items-center justify-center gap-2 px-3 py-3 text-sm font-semibold text-slate-200 disabled:opacity-50"
              >
                <Icon className="h-4 w-4 text-cyan-300" />
                {busy === id ? 'Injecting…' : label}
              </button>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div>
              <p className="text-xs font-bold text-slate-300">Failure demonstration mode</p>
              <p className="mt-1 text-[11px] text-slate-500">Enable this before approval to intentionally fail verification and demonstrate automatic rollback.</p>
            </div>
            <button
              onClick={() => void forceFailure(!(incident?.force_remediation_failure ?? false))}
              disabled={!incident || busy !== null}
              className={`rounded-lg border px-3 py-2 text-xs font-bold transition disabled:opacity-40 ${incident?.force_remediation_failure ? 'border-red-500/40 bg-red-950/40 text-red-300' : 'border-slate-700 bg-slate-900 text-slate-300'}`}
            >
              {incident?.force_remediation_failure ? 'FORCE FAILURE: ON' : 'FORCE FAILURE: OFF'}
            </button>
          </div>
        </section>

        <section className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {metricCards(metrics).map(([label, value, baseline]) => (
            <article key={label} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
              <p className="mt-2 text-2xl font-black text-slate-100">{value}</p>
              <p className="mt-1 text-xs text-slate-500">{baseline}</p>
            </article>
          ))}
        </section>

        <section className="section-reveal mb-5 grid gap-5 xl:grid-cols-[1fr_1fr]">
          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center gap-2">
              <GitMerge className="h-5 w-5 text-violet-300" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Alert Correlation</p>
                <h2 className="mt-1 text-lg font-bold">Many alerts → one incident</h2>
              </div>
            </div>
            {!incident ? (
              <div className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-sm text-slate-500">
                Waiting for at least two related alerts…
              </div>
            ) : (
              <div>
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-violet-500/30 bg-violet-950/20 p-4">
                  <div>
                    <p className="text-sm font-black text-violet-200">{incident.alert_count} alerts correlated</p>
                    <p className="mt-1 text-xs text-slate-400">{incident.correlation.correlation_strength}% correlation strength</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-500">Incident created</p>
                    <p className="text-xl font-black text-white">{incident.id}</p>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                    <p className="text-xs font-semibold text-slate-400">Affected services</p>
                    <p className="mt-1 text-sm text-slate-200">{incident.affected_services.join(', ')}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                    <p className="text-xs font-semibold text-slate-400">Severity / Status</p>
                    <p className="mt-1 text-sm font-bold text-red-300">{incident.severity} · {incident.status}</p>
                  </div>
                </div>
                <div className="mt-4 space-y-2">
                  {incident.correlation.reasons.map((reason) => (
                    <div key={reason} className="flex gap-2 text-sm text-slate-300">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /> {reason}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </article>

          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center gap-2">
              <BrainCircuit className="h-5 w-5 text-cyan-300" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Root Cause Investigation</p>
                <h2 className="mt-1 text-lg font-bold">Weighted evidence + graph reasoning</h2>
              </div>
            </div>
            {!rca ? (
              <div className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-sm text-slate-500">
                RCA begins automatically after alert correlation.
              </div>
            ) : (
              <div>
                <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-cyan-400">Leading hypothesis</p>
                  <p className="mt-2 text-xl font-black text-white">{rca.top_hypothesis.cause}</p>
                  <p className="mt-1 text-sm font-bold text-cyan-300">Confidence: {rca.top_hypothesis.confidence}%</p>
                </div>
                <div className="mt-4 space-y-3">
                  {rca.hypotheses.map((hypothesis, index) => (
                    <div key={hypothesis.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-xs text-slate-500">H{index + 1}</p>
                          <p className="font-bold text-slate-100">{hypothesis.cause}</p>
                        </div>
                        <span className="rounded-full bg-slate-800 px-3 py-1 text-sm font-black text-cyan-300">{hypothesis.confidence}%</span>
                      </div>
                      <div className="mt-3 grid gap-2 lg:grid-cols-2">
                        <div>
                          <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-emerald-400">Evidence</p>
                          {hypothesis.evidence.slice(0, 3).map((item) => (
                            <p key={item} className="mb-1 flex gap-2 text-xs leading-5 text-slate-400"><CheckCircle2 className="mt-1 h-3 w-3 shrink-0 text-emerald-400" />{item}</p>
                          ))}
                        </div>
                        <div>
                          <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-amber-400">Evidence against</p>
                          {hypothesis.counter_evidence.slice(0, 2).map((item) => (
                            <p key={item} className="mb-1 flex gap-2 text-xs leading-5 text-slate-400"><XCircle className="mt-1 h-3 w-3 shrink-0 text-amber-400" />{item}</p>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </article>
        </section>

        <section className="section-reveal mb-5">
          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <GitMerge className="h-5 w-5 text-fuchsia-300" />
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Reasoning Debate</p>
                  <h2 className="mt-1 text-lg font-bold">Structured challenge before action</h2>
                </div>
              </div>
              {incident?.reasoning_debate && <span className="rounded-full border border-fuchsia-500/30 bg-fuchsia-950/20 px-3 py-1 text-xs font-bold text-fuchsia-200">Deterministic · Explainable</span>}
            </div>
            {!incident?.reasoning_debate ? (
              <div className="rounded-xl border border-dashed border-slate-700 p-5 text-sm text-slate-500">The reasoning debate appears after alert correlation and RCA.</div>
            ) : (
              <div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {incident.reasoning_debate.turns.map((turn) => (
                    <div key={turn.role} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                      <p className="text-[10px] font-black uppercase tracking-[0.16em] text-fuchsia-300">{turn.role}</p>
                      <p className="mt-2 text-xs leading-5 text-slate-300">{turn.statement}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[10px] leading-4 text-slate-600">{incident.reasoning_debate.disclaimer}</p>
              </div>
            )}
          </article>
        </section>

        <section className="section-reveal mb-5 grid gap-5 xl:grid-cols-3">
          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center gap-2">
              <BrainCircuit className="h-5 w-5 text-violet-300" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Counterfactual RCA</p>
                <h2 className="mt-1 text-lg font-bold">Challenge the leading hypothesis</h2>
              </div>
            </div>
            {!incident ? (
              <div className="rounded-xl border border-dashed border-slate-700 p-5 text-sm text-slate-500">Waiting for an incident and RCA…</div>
            ) : !incident.counterfactual ? (
              <div>
                <p className="text-sm leading-6 text-slate-400">Instead of trusting the highest score, AstraGuard asks whether downstream symptoms would disappear if the suspected cause were removed.</p>
                <button
                  onClick={() => void runCounterfactual()}
                  disabled={busy !== null}
                  className="mt-4 w-full rounded-xl border border-violet-500/40 bg-violet-950/30 px-4 py-3 text-sm font-bold text-violet-200 transition hover:bg-violet-900/40 disabled:opacity-50"
                >
                  {busy === 'counterfactual' ? 'Running counterfactual…' : 'Run Counterfactual Test'}
                </button>
              </div>
            ) : (
              <div>
                <div className="rounded-xl border border-violet-500/30 bg-violet-950/20 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-violet-300">Causal support</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <p className="text-2xl font-black text-white">{incident.counterfactual.causal_support}</p>
                    <p className="text-sm font-bold text-violet-200">{incident.counterfactual.explained_symptoms}/{incident.counterfactual.total_symptoms} symptoms explained</p>
                  </div>
                </div>
                <div className="mt-3 space-y-2">
                  {incident.counterfactual.symptoms.map((symptom) => (
                    <div key={symptom.name} className="flex gap-2 text-xs leading-5 text-slate-400">
                      {symptom.explained ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />}
                      <span><strong className="text-slate-200">{symptom.name}:</strong> {symptom.effect}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </article>

          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center gap-2">
              <Gauge className="h-5 w-5 text-amber-300" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Business Impact</p>
                <h2 className="mt-1 text-lg font-bold">Technical failure → business risk</h2>
              </div>
            </div>
            {!incident?.business_impact ? (
              <div className="rounded-xl border border-dashed border-slate-700 p-5 text-sm text-slate-500">Impact is calculated after incident correlation.</div>
            ) : (
              <div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-red-500/20 bg-red-950/20 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-slate-500">Severity</p>
                    <p className="mt-1 text-lg font-black text-red-300">{incident.business_impact.severity}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-slate-500">Users affected</p>
                    <p className="mt-1 text-lg font-black">{incident.business_impact.users_affected}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-slate-500">Failed transactions</p>
                    <p className="mt-1 text-lg font-black">{incident.business_impact.failed_transactions}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-slate-500">SLA violation</p>
                    <p className="mt-1 text-lg font-black text-amber-300">{incident.business_impact.sla_violation ? 'YES' : 'NO'}</p>
                  </div>
                </div>
                <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-slate-500">Estimated revenue risk</p>
                  <p className="mt-1 text-xl font-black text-amber-200">₹{incident.business_impact.estimated_revenue_risk_inr_per_hour.toLocaleString('en-IN')}/hour</p>
                  <p className="mt-2 text-[10px] leading-4 text-slate-600">Simulator estimate — not real company financial data.</p>
                </div>
              </div>
            )}
          </article>

          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-300" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Minimum Safe Remediation</p>
                <h2 className="mt-1 text-lg font-bold">Smallest effective safe action</h2>
              </div>
            </div>
            {!incident?.remediation ? (
              <div className="rounded-xl border border-dashed border-slate-700 p-5 text-sm text-slate-500">Remediation is generated after RCA.</div>
            ) : (
              <div>
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-emerald-400">Recommended action</p>
                  <p className="mt-2 text-lg font-black text-white">{incident.remediation.recommended_action.action}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-bold">
                    <span className="rounded-full bg-emerald-950 px-2 py-1 text-emerald-300">Risk {incident.remediation.recommended_action.risk}</span>
                    <span className="rounded-full bg-slate-800 px-2 py-1 text-slate-300">Cost {incident.remediation.recommended_action.cost}</span>
                    <span className="rounded-full bg-slate-800 px-2 py-1 text-slate-300">Disruption {incident.remediation.recommended_action.disruption}</span>
                  </div>
                </div>
                <div className="mt-3 rounded-xl border border-amber-500/20 bg-amber-950/20 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-black text-amber-300">{incident.remediation.autonomy.state}</p>
                      <p className="mt-1 text-[11px] text-slate-500">Autonomy level {incident.remediation.autonomy.level} · Action risk {incident.remediation.autonomy.action_risk ?? incident.remediation.recommended_action.risk}</p>
                    </div>
                    <span className="rounded-full border border-slate-700 bg-slate-950/60 px-2.5 py-1 text-[10px] font-bold text-slate-300">Incident {incident.incident_risk?.level ?? incident.severity}</span>
                  </div>
                  {incident.remediation.autonomy.policy_reason && <p className="mt-2 text-[11px] leading-4 text-slate-500">{incident.remediation.autonomy.policy_reason}</p>}
                </div>
                <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <p className="text-xs font-bold text-slate-300">Remediation contract</p>
                  <div className="mt-2 space-y-1">
                    {incident.remediation.contract.success_conditions.slice(0, 4).map((condition) => (
                      <p key={condition.metric} className="flex gap-2 text-[11px] text-slate-500"><CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-cyan-400" />{condition.label}</p>
                    ))}
                  </div>
                  <p className="mt-2 text-[11px] text-slate-500">Observe for {incident.remediation.contract.observation_period_seconds}s · Rollback: {incident.remediation.contract.rollback_action}</p>
                </div>
                <div className="mt-3 rounded-xl border border-cyan-500/20 bg-cyan-950/10 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Execution state</p>
                      <p className="mt-1 text-sm font-black text-cyan-200">{incident.remediation_state.replaceAll('_', ' ')}</p>
                    </div>
                    {incident.status === 'RESOLVED' && <CheckCircle2 className="h-7 w-7 text-emerald-400" />}
                  </div>

                  {(incident.remediation_state === 'AWAITING_APPROVAL' || incident.remediation_state === 'REJECTED' || incident.remediation_state === 'ROLLED_BACK') && (
                    <div className="mt-3 grid grid-cols-2 gap-2">
                      <button onClick={() => void approveRemediation()} disabled={busy !== null} className="rounded-lg bg-emerald-600/90 px-3 py-2 text-xs font-black text-white hover:bg-emerald-500 disabled:opacity-50">
                        {busy === 'approve' ? 'Starting…' : 'APPROVE'}
                      </button>
                      <button onClick={() => void rejectRemediation()} disabled={busy !== null} className="rounded-lg border border-red-500/40 bg-red-950/30 px-3 py-2 text-xs font-black text-red-200 hover:bg-red-900/40 disabled:opacity-50">
                        REJECT
                      </button>
                    </div>
                  )}

                  {incident.remediation_state === 'EXECUTING' && (
                    <div className="mt-3 rounded-lg border border-cyan-500/30 bg-cyan-950/30 p-3 text-xs font-bold text-cyan-200">EXECUTING REMEDIATION… metrics are recovering gradually.</div>
                  )}
                  {incident.remediation_state === 'VERIFYING' && (
                    <div className="mt-3 rounded-lg border border-violet-500/30 bg-violet-950/30 p-3 text-xs font-bold text-violet-200">VERIFYING RECOVERY… checking contract conditions.</div>
                  )}
                  {incident.remediation_state === 'RESOLVED' && (
                    <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-950/30 p-3">
                      <p className="text-sm font-black text-emerald-300">RECOVERY VERIFIED ✓</p>
                      <p className="mt-1 text-[11px] text-slate-400">Incident {incident.id} closed only after telemetry checks passed.</p>
                    </div>
                  )}
                  {(incident.remediation_state === 'ROLLBACK' || incident.remediation_state === 'ROLLED_BACK') && (
                    <div className="mt-3 rounded-lg border border-red-500/30 bg-red-950/30 p-3">
                      <p className="text-sm font-black text-red-300">{incident.remediation_state === 'ROLLBACK' ? 'ROLLBACK IN PROGRESS…' : 'ROLLBACK COMPLETED'}</p>
                      <p className="mt-1 text-[11px] text-slate-400">Recovery failed. Previous state is restored and the incident remains open.</p>
                    </div>
                  )}

                  {incident.verification && (
                    <div className="mt-3 space-y-1">
                      {incident.verification.checks.map((check) => (
                        <p key={check.metric} className="flex items-center justify-between gap-2 text-[11px] text-slate-400">
                          <span className="flex items-center gap-1">{check.passed ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : <XCircle className="h-3.5 w-3.5 text-red-400" />}{check.label}</span>
                          <span>{check.value}</span>
                        </p>
                      ))}
                    </div>
                  )}

                  {incident.remediation_state === 'VERIFYING' && (
                    <button onClick={() => void manualRollback()} disabled={busy !== null} className="mt-3 w-full rounded-lg border border-red-500/30 px-3 py-2 text-xs font-bold text-red-300 hover:bg-red-950/30 disabled:opacity-50">Manual rollback</button>
                  )}
                </div>
              </div>
            )}
          </article>

          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center gap-2">
              <Mail className="h-5 w-5 text-cyan-300" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Admin Notifications</p>
                <h2 className="mt-1 text-lg font-bold">Incident lifecycle alerts</h2>
              </div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold text-slate-200">Email channel</p>
                  <p className="mt-1 text-[11px] text-slate-500">{snapshot.notification_config.configured ? `Configured for ${snapshot.notification_config.admin_email}` : 'SMTP not configured — in-app notification log remains active'}</p>
                </div>
                <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black ${snapshot.notification_config.configured ? 'border-emerald-500/30 bg-emerald-950/30 text-emerald-300' : 'border-slate-700 bg-slate-900 text-slate-400'}`}>{snapshot.notification_config.configured ? 'EMAIL READY' : 'IN-APP ONLY'}</span>
              </div>
            </div>
            <div className="mt-3 space-y-2">
              {snapshot.notifications.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">Notifications appear when an incident is detected, approval is required, recovery succeeds, or rollback begins.</div>
              ) : snapshot.notifications.slice(-4).reverse().map((item) => (
                <div key={item.key} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-bold text-slate-200">{item.kind.replaceAll('_', ' ')}</p>
                    <span className="text-[10px] font-bold text-cyan-300">{item.status}</span>
                  </div>
                  <p className="mt-1 text-[11px] text-slate-500">{item.subject}</p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section id="topology" className="section-reveal grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
          <div className="space-y-5">
            <article className="command-card rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Enterprise Dependency Graph</p>
                  <h2 className="mt-1 text-lg font-bold">Live service health & failure propagation</h2>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />{system.services_healthy} healthy
                  <span className="ml-2 h-2 w-2 rounded-full bg-amber-400" />{system.services_warning} warning
                  <span className="ml-2 h-2 w-2 rounded-full bg-red-400" />{system.services_critical} critical
                </div>
              </div>
              <ServiceGraph services={services} incidentActive={simulation.active} />
            </article>

            <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <div className="mb-4 flex items-center gap-2">
                <Gauge className="h-5 w-5 text-cyan-300" />
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Live Telemetry</p>
                  <h2 className="mt-1 text-lg font-bold">Propagation over time</h2>
                </div>
              </div>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#020617', border: '1px solid #334155', borderRadius: 10 }} />
                    <Legend />
                    <Line type="monotone" dataKey="database_cpu" name="DB CPU %" stroke="#22d3ee" dot={false} strokeWidth={2} />
                    <Line type="monotone" dataKey="database_connections" name="DB Conn %" stroke="#a78bfa" dot={false} strokeWidth={2} />
                    <Line type="monotone" dataKey="checkout_error_rate" name="Checkout Err %" stroke="#f59e0b" dot={false} strokeWidth={2} />
                    <Line type="monotone" dataKey="api_5xx_rate" name="API 5xx %" stroke="#ef4444" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </article>
          </div>

          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Live Alerts</p>
                <h2 className="mt-1 text-lg font-bold">Raw signals before correlation</h2>
              </div>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-bold text-slate-300">{alerts.length}</span>
            </div>
            {alerts.length === 0 ? (
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-5 text-center">
                <ShieldCheck className="mx-auto h-7 w-7 text-emerald-300" />
                <p className="mt-2 font-semibold text-emerald-200">No active alerts</p>
                <p className="mt-1 text-xs text-slate-500">Inject an incident to begin the demo.</p>
              </div>
            ) : (
              <div className="max-h-[690px] space-y-3 overflow-y-auto pr-1">
                {alerts.map((alert) => (
                  <div key={alert.type} className="rounded-xl border border-red-500/20 bg-red-950/20 p-4">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-300" />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-black text-red-200">{alert.type}</p>
                          <span className="text-[10px] font-bold text-red-300">{alert.severity}</span>
                        </div>
                        <p className="mt-1 text-xs leading-5 text-slate-400">{alert.message}</p>
                        <div className="mt-2 flex justify-between text-[11px] text-slate-500">
                          <span>{alert.service}</span>
                          <span>{alert.value} / threshold {alert.threshold}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-5 rounded-xl border border-dashed border-slate-700 p-4 text-xs leading-5 text-slate-500">
              <strong className="text-slate-300">Command center:</strong> live correlation, explainable diagnosis, bounded autonomy, verification, persistence and rollback are ready for demonstration.
            </div>
          </article>
        </section>

        <section id="audit" className="section-reveal premium-surface mt-5 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Incident Audit Trail</p>
              <h2 className="mt-1 text-lg font-bold">Every decision and action is recorded</h2>
            </div>
            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-bold text-slate-300">{snapshot.audit.length} events</span>
          </div>
          {snapshot.audit.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">Audit events will appear after an incident is injected.</div>
          ) : (
            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {[...snapshot.audit].reverse().map((event, index) => (
                <div key={`${event.timestamp}-${event.event_type}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[10px] font-black uppercase tracking-wide text-cyan-300">{event.event_type.replaceAll('_', ' ')}</p>
                    <p className="text-[10px] text-slate-600">{new Date(event.timestamp).toLocaleTimeString()}</p>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-400">{event.message}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="section-reveal mt-5 grid gap-5 xl:grid-cols-2">
          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Incident Memory</p>
                <h2 className="mt-1 text-lg font-bold">Historical fingerprint match</h2>
              </div>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-bold text-slate-300">Jaccard</span>
            </div>
            {incident?.historical_match ? (
              <div className="rounded-xl border border-cyan-500/25 bg-cyan-950/20 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide text-cyan-300">Historical Match</p>
                    <p className="mt-1 text-xl font-black text-slate-100">{incident.historical_match.incident_id}</p>
                  </div>
                  <span className="rounded-full border border-cyan-400/30 bg-cyan-950/40 px-3 py-1 text-sm font-black text-cyan-200">{incident.historical_match.similarity}%</span>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg bg-slate-950/50 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-slate-500">Previous root cause</p>
                    <p className="mt-1 text-sm font-bold text-slate-200">{incident.historical_match.previous_root_cause ?? 'Unknown'}</p>
                  </div>
                  <div className="rounded-lg bg-slate-950/50 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-slate-500">Previous remediation</p>
                    <p className="mt-1 text-sm font-bold text-slate-200">{incident.historical_match.previous_successful_remediation ?? 'Unknown'}</p>
                  </div>
                </div>
                <p className="mt-3 text-xs text-slate-400">Recovery: <strong className="text-emerald-300">{incident.historical_match.recovery}</strong> · {incident.historical_match.method}</p>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">
                {incident ? 'No similar resolved incident exists yet. Resolve this incident, reset the demo, and inject the same scenario again to see memory matching.' : 'Inject an incident to compare its alert fingerprint with persistent history.'}
              </div>
            )}
          </article>

          <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">SQLite History</p>
                <h2 className="mt-1 text-lg font-bold">Persistent incidents</h2>
              </div>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-bold text-slate-300">{snapshot.historical_incidents.length} stored</span>
            </div>
            {snapshot.historical_incidents.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">No incidents stored yet.</div>
            ) : (
              <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                {snapshot.historical_incidents.slice(0, 8).map((item) => (
                  <div key={item.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-black text-slate-200">{item.id} · {item.title}</p>
                        <p className="mt-1 text-xs text-slate-500">{item.root_cause ?? 'RCA pending'} · {item.confidence}% confidence</p>
                      </div>
                      <span className={`rounded-full px-2 py-1 text-[10px] font-black ${item.status === 'RESOLVED' ? 'bg-emerald-950/50 text-emerald-300' : 'bg-amber-950/50 text-amber-300'}`}>{item.status.replaceAll('_', ' ')}</span>
                    </div>
                    {item.remediation_action && <p className="mt-2 text-xs text-slate-400">Remediation: {item.remediation_action}</p>}
                  </div>
                ))}
              </div>
            )}
          </article>
        </section>
      </div>
    </main>
  )
}
