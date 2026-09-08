export default function CandidateDashboard() {
  const workflowId = null
  return (
    <div>
      <h2 className="text-2xl font-semibold">Candidate Dashboard</h2>
      <div className="mt-6 grid grid-cols-3 gap-6">
        <div className="card">
          <div className="text-slate-500 text-sm">Applications</div>
          <a href="/candidate/applications" className="mt-2 inline-block text-accent hover:underline">View</a>
        </div>
        <div className="card">
          <div className="text-slate-500 text-sm">Recommended jobs</div>
          <a href="/candidate/jobs" className="mt-2 inline-block text-accent hover:underline">Browse</a>
        </div>
        <div className="card">
          <div className="text-slate-500 text-sm">Assessment status</div>
          <a href="/candidate/assessment" className="mt-2 inline-block text-accent hover:underline">Take assessment</a>
        </div>
      </div>
      <div className="mt-6">
        {/* Workflow timeline placeholder: pass workflowId when created */}
        <div className="max-w-2xl">
          {/* @ts-ignore */}
          <script></script>
        </div>
      </div>
    </div>
  )
}
