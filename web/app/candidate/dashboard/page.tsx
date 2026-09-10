import Link from 'next/link'

export default function CandidateDashboard() {
  return (
    <div>
      <h2 className="text-2xl font-semibold">Candidate Dashboard</h2>
      <div className="mt-6 grid grid-cols-3 gap-6">
        <div className="card">
          <div className="text-slate-500 text-sm">Applications</div>
          <Link href="/candidate/applications" className="mt-2 inline-block text-accent hover:underline">View</Link>
        </div>
        <div className="card">
          <div className="text-slate-500 text-sm">Recommended jobs</div>
          <Link href="/candidate/jobs" className="mt-2 inline-block text-accent hover:underline">Browse</Link>
        </div>
        <div className="card">
          <div className="text-slate-500 text-sm">Assessment status</div>
          <Link href="/candidate/assessment" className="mt-2 inline-block text-accent hover:underline">Take assessment</Link>
        </div>
      </div>
    </div>
  )
}