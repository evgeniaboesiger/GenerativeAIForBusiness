import Link from 'next/link'

export default function RecruiterJobs() {
  return (
    <div>
      <h2 className="text-2xl font-semibold">Jobs</h2>
      <div className="mt-4 space-y-4">
        <div className="card">Your job 1 — <Link href="/recruiter/jobs/1" className="text-accent">Manage</Link></div>
        <div className="card">Your job 2 — <Link href="/recruiter/jobs/2" className="text-accent">Manage</Link></div>
      </div>
    </div>
  )
}