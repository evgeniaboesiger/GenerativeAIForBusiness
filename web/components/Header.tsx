export default function Header() {
  return (
    <header className="border-b py-4 px-6">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="text-2xl font-semibold text-navy">FRAUMATCH</div>
        <nav className="space-x-4 text-sm text-navy">
          <a href="/" className="hover:underline">Home</a>
        </nav>
      </div>
    </header>
  )
}
