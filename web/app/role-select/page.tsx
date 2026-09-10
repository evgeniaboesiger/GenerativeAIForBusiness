import Link from 'next/link'

export default function RoleSelect() {
  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-semibold">Choose your role</h2>
      <div className="mt-6 grid grid-cols-2 gap-6">
        <Link href="/candidate/dashboard" className="card hover:shadow">Candidate — find jobs, apply, assessments</Link>
        <Link href="/recruiter/dashboard" className="card hover:shadow">Recruiter — post jobs, review candidates</Link>
      </div>
    </div>
  )
}