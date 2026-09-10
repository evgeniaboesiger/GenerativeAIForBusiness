"use client"
import { useEffect, useState } from 'react'

type AgentEntry = {
  agent: string
  agent_version: string
  status: string
  start_time: string
  end_time: string
  latency_ms: number
  output_reference?: any
}

export default function WorkflowTimeline({ workflowId }: { workflowId: string | null }) {
  const [entries, setEntries] = useState<AgentEntry[]>([])
  const [state, setState] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!workflowId) return
    let cancelled = false
    fetch(`/api/workflows/${workflowId}`)
      .then(async r => {
        if (!r.ok) throw new Error(`HTTP ${r.status} fetching workflow`)
        return r.json()
      })
      .then(data => {
        if (cancelled) return
        setState(data.state)
        setEntries(data.agent_history || [])
      })
      .catch(e => { if (!cancelled) setError(String(e.message || e)) })
    return () => { cancelled = true }
  }, [workflowId])

  if (!workflowId) return <div className="card">No workflow started</div>

  return (
    <div className="card">
      {error && <div className="text-sm text-red-600 mb-2">Could not load workflow: {error}</div>}
      <h3 className="text-lg font-semibold">Workflow status — {state ?? 'loading…'}</h3>
      <ol className="mt-4 space-y-3">
        {entries.map((e, idx) => (
          <li key={idx} className="flex items-start">
            <div className="w-6">{idx + 1}.</div>
            <div>
              <div className="font-medium">{e.agent} — {e.status}</div>
              <div className="text-sm text-gray-500">{new Date(e.start_time).toLocaleString()} → {new Date(e.end_time).toLocaleString()} ({e.latency_ms} ms)</div>
              {e.output_reference && <div className="text-sm mt-1">{JSON.stringify(e.output_reference)}</div>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
