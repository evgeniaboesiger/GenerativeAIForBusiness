export default function CandidateJobs() {
  return (
    <div>
      <h2 className="text-2xl font-semibold">Jobs</h2>
      <div className="mt-4 space-y-4">
        <div className="card">Job listing 1 — <a href="/candidate/jobs/1" className="text-accent">View</a></div>
        <div className="card">Job listing 2 — <a href="/candidate/jobs/2" className="text-accent">View</a></div>
      </div>
    </div>
  )
}
