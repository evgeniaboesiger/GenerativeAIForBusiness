export default function RecruiterJobDetail({ params }: { params: { id: string } }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold">Manage Job #{params.id}</h2>
      <div className="mt-4 card">Applicants, screening, and post controls</div>
    </div>
  )
}
