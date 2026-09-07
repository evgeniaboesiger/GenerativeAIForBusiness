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

  useEffect(() => {
    if (!workflowId) return
    fetch(`/api/workflows/${workflowId}`).then(r => r.json()).then(data => {
      setState(data.state)
      setEntries(data.agent_history || [])
    })
  }, [workflowId])

  if (!workflowId) return <div className="card">No workflow started</div>

  return (
    <div className="card">
      <h3 className="text-lg font-semibold">Workflow status — {state}</h3>
      <ol className="mt-4 space-y-3">
        {entries.map((e, idx) => (
          <li key={idx} className="flex items-start">
            <div className="w-6">{idx + 1}.</div>
            <div>
              <div className="font-medium">{e.agent} — {e.status}</div>
              <div className="text-sm text-muted-foreground">{new Date(e.start_time).toLocaleString()} → {new Date(e.end_time).toLocaleString()} ({e.latency_ms} ms)</div>
              {e.output_reference && <div className="text-sm mt-1">{JSON.stringify(e.output_reference)}</div>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
