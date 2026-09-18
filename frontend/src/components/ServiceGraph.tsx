import { Background, Controls, MarkerType, ReactFlow, type Edge, type Node } from '@xyflow/react'
import { Database, Network, Server, ShieldCheck, ShoppingCart, Siren, Users, Zap } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { Service } from '../types'

type Props = {
  services: Service[]
  incidentActive: boolean
}

const positions: Record<string, { x: number; y: number }> = {
  users: { x: 20, y: 145 },
  'api-gateway': { x: 210, y: 145 },
  checkout: { x: 430, y: 145 },
  payment: { x: 650, y: 145 },
  database: { x: 890, y: 80 },
  notification: { x: 890, y: 225 },
  auth: { x: 430, y: 320 },
}

const iconMap = {
  'api-gateway': Network,
  checkout: ShoppingCart,
  payment: Zap,
  database: Database,
  notification: Siren,
  auth: ShieldCheck,
} as const

function visual(status: string) {
  if (status === 'CRITICAL') return { border: '#ef4444', bg: '#2b0b12', text: '#fecaca', glow: '0 0 24px rgba(239,68,68,.18)' }
  if (status === 'WARNING') return { border: '#f59e0b', bg: '#2a1808', text: '#fde68a', glow: '0 0 22px rgba(245,158,11,.14)' }
  return { border: '#10b981', bg: '#07231d', text: '#a7f3d0', glow: '0 0 18px rgba(16,185,129,.10)' }
}

function metricText(service: Service) {
  const entries = Object.entries(service.metrics)
  if (!entries.length) return 'Nominal telemetry'
  return entries
    .slice(0, 2)
    .map(([key, value]) => `${key.replaceAll('_', ' ')} ${value}`)
    .join(' · ')
}

export default function ServiceGraph({ services, incidentActive }: Props) {
  const [selectedId, setSelectedId] = useState<string>('database')
  const serviceMap = useMemo(() => new Map(services.map((service) => [service.id, service])), [services])
  const selected = serviceMap.get(selectedId) ?? services[0]

  const nodes = useMemo<Node[]>(() => {
    const userNode: Node = {
      id: 'users',
      position: positions.users,
      data: {
        label: (
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-slate-300" />
            <div><div className="font-bold">Users</div><div className="text-[10px] text-slate-500">External traffic</div></div>
          </div>
        ),
      },
      style: { width: 150, border: '1px solid #334155', borderRadius: 14, background: '#0f172a', color: '#e2e8f0', padding: 12 },
      selectable: true,
    }

    const serviceNodes = services.map<Node>((service) => {
      const Icon = iconMap[service.id as keyof typeof iconMap] ?? Server
      const v = visual(service.status)
      return {
        id: service.id,
        position: positions[service.id] ?? { x: 0, y: 0 },
        data: {
          label: (
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 shrink-0" />
                <span className="truncate font-bold">{service.name}</span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-2 text-[9px] font-black tracking-wide">
                <span>{service.status}</span><span className="opacity-60">{service.criticality}</span>
              </div>
            </div>
          ),
        },
        style: {
          width: 175,
          border: `1px solid ${v.border}`,
          borderRadius: 14,
          background: v.bg,
          color: v.text,
          padding: 12,
          boxShadow: v.glow,
        },
        selectable: true,
      }
    })
    return [userNode, ...serviceNodes]
  }, [services])

  const edges = useMemo<Edge[]>(() => {
    const pairs: Array<[string, string]> = [
      ['users', 'api-gateway'],
      ['api-gateway', 'checkout'],
      ['checkout', 'payment'],
      ['payment', 'database'],
      ['checkout', 'auth'],
      ['payment', 'notification'],
    ]
    return pairs.map(([source, target], index) => {
      const targetStatus = serviceMap.get(target)?.status ?? 'HEALTHY'
      const stroke = targetStatus === 'CRITICAL' ? '#ef4444' : targetStatus === 'WARNING' ? '#f59e0b' : '#475569'
      return {
        id: `edge-${index}`,
        source,
        target,
        type: 'smoothstep',
        animated: incidentActive && targetStatus !== 'HEALTHY',
        markerEnd: { type: MarkerType.ArrowClosed, color: stroke },
        style: { stroke, strokeWidth: targetStatus === 'HEALTHY' ? 1.5 : 2.4 },
      }
    })
  }, [incidentActive, serviceMap])

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_250px]">
      <div className="h-[430px] overflow-hidden rounded-xl border border-slate-800 bg-slate-950/70">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          fitViewOptions={{ padding: 0.14 }}
          minZoom={0.55}
          maxZoom={1.4}
          nodesDraggable={false}
          nodesConnectable={false}
          onNodeClick={(_, node) => node.id !== 'users' && setSelectedId(node.id)}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1e293b" gap={24} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      <aside className="rounded-xl border border-slate-800 bg-slate-950/55 p-4">
        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Selected Service</p>
        {selected ? (
          <>
            <div className="mt-3 flex items-start justify-between gap-2">
              <div><p className="font-black text-slate-100">{selected.name}</p><p className="mt-1 text-xs text-slate-500">Criticality {selected.criticality}</p></div>
              <span className={`rounded-full border px-2 py-1 text-[9px] font-black ${selected.status === 'CRITICAL' ? 'border-red-500/30 text-red-300' : selected.status === 'WARNING' ? 'border-amber-500/30 text-amber-300' : 'border-emerald-500/30 text-emerald-300'}`}>{selected.status}</span>
            </div>
            <div className="mt-4 border-t border-slate-800 pt-4">
              <p className="text-[10px] uppercase tracking-wide text-slate-600">Current telemetry</p>
              <p className="mt-2 text-xs capitalize leading-5 text-slate-300">{metricText(selected)}</p>
            </div>
            <div className="mt-4 border-t border-slate-800 pt-4">
              <p className="text-[10px] uppercase tracking-wide text-slate-600">Dependencies</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {selected.dependencies.length ? selected.dependencies.map((dep) => <span key={dep} className="rounded-md bg-slate-800 px-2 py-1 text-[10px] text-slate-300">{dep}</span>) : <span className="text-xs text-slate-500">No downstream dependency</span>}
              </div>
            </div>
            <p className="mt-5 text-[10px] leading-4 text-slate-600">Click another service node to inspect its live state. Animated red/amber paths show incident propagation.</p>
          </>
        ) : <p className="mt-3 text-xs text-slate-500">Select a service node.</p>}
      </aside>
    </div>
  )
}
