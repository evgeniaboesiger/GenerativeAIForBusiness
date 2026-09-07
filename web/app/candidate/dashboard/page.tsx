export default function CandidateDashboard() {
  const workflowId = null
  return (
    <div>
      <h2 className="text-2xl font-semibold">Candidate Dashboard</h2>
      <div className="mt-6 grid grid-cols-3 gap-6">
        <div className="card">Applications</div>
        <div className="card">Recommended jobs</div>
        <div className="card">Assessment status</div>
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
