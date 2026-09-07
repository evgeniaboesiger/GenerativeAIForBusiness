export default function RecruiterCandidateDetail({ params }: { params: { id: string } }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold">Candidate #{params.id}</h2>
      <div className="mt-4 card">Profile, application history, and contact</div>
    </div>
  )
}
