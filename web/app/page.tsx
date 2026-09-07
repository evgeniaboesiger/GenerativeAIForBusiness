export default function Home() {
  return (
    <section>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-navy">FRAUMATCH</h1>
          <p className="mt-2 text-muted-foreground max-w-xl">A Swiss-focused employment matching platform for women — university proof of concept.</p>
        </div>
        <div>
          <a href="/role-select" className="px-4 py-2 bg-accent text-white rounded-lg">Get started</a>
        </div>
      </div>

      <section className="mt-8 grid grid-cols-3 gap-6">
        <div className="card">Dashboard mockups and metrics</div>
        <div className="card">Candidate flows and profiles</div>
        <div className="card">Recruiter workflows</div>
      </section>
    </section>
  )
}
