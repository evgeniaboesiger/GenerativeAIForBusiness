import Link from 'next/link'

export default function Sidebar() {
  return (
    <aside className="w-64 pr-6">
      <div className="space-y-2">
        <Link href="/candidate/dashboard" className="block p-2 rounded hover:bg-gray-50">Candidate</Link>
        <Link href="/recruiter/dashboard" className="block p-2 rounded hover:bg-gray-50">Recruiter</Link>
        <Link href="/admin/impact" className="block p-2 rounded hover:bg-gray-50">Impact</Link>
      </div>
    </aside>
  )
}