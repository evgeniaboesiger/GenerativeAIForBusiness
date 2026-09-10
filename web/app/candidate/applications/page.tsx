"use client"
import { useEffect, useState } from 'react'
import WorkflowTimeline from '../../../components/WorkflowTimeline'

export default function ApplicationsPage() {
  const [workflowId, setWorkflowId] = useState<string | null>(null)
  const [starting, setStarting] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetch('/api/workflows/start/1/1', { method: 'POST' })
      .then(r => r.json())
      .then(d => { if (!cancelled) setWorkflowId(d.workflow_id) })
      .catch(() => { /* offline demo: leave timeline unstarted */ })
      .finally(() => { if (!cancelled) setStarting(false) })
    return () => { cancelled = true }
  }, [])

  return (
    <div>
      <h2 className="text-2xl font-semibold">Applications</h2>
      <div className="mt-4">
        {starting && <div className="card text-sm text-gray-500">Starting workflow…</div>}
        {!starting && <WorkflowTimeline workflowId={workflowId} />}
      </div>
    </div>
  )
}