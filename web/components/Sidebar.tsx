export default function Sidebar({ children }: { children?: React.ReactNode }) {
  return (
    <aside className="w-64 pr-6">
      <div className="space-y-2">
        <a href="/candidate/dashboard" className="block p-2 rounded hover:bg-gray-50">Candidate</a>
        <a href="/recruiter/dashboard" className="block p-2 rounded hover:bg-gray-50">Recruiter</a>
        <a href="/admin/impact" className="block p-2 rounded hover:bg-gray-50">Impact</a>
      </div>
    </aside>
  )
}
