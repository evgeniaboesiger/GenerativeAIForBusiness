export default function JobDetail({ params }: { params: { id: string } }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold">Job #{params.id}</h2>
      <div className="mt-4 card">Job details, apply button, and company info</div>
    </div>
  )
}
