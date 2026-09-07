export default function RecruiterDashboard() {
  return (
    <div>
      <h2 className="text-2xl font-semibold">Recruiter Dashboard</h2>
      <div className="mt-6 grid grid-cols-3 gap-6">
        <div className="card">Open roles</div>
        <div className="card">Candidate pipeline</div>
        <div className="card">Analytics</div>
      </div>
    </div>
  )
}
