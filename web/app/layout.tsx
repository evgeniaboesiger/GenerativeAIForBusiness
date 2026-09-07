import './styles/globals.css'

export const metadata = {
  title: 'FRAUMATCH',
  description: 'Swiss employment matching for women — proof of concept',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b py-4 px-6">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              <div className="text-2xl font-semibold text-navy">FRAUMATCH</div>
              <nav className="space-x-4 text-sm text-navy">
                <a href="/" className="hover:underline">Home</a>
                <a href="/login" className="hover:underline">Login</a>
                <a href="/register" className="hover:underline">Register</a>
              </nav>
            </div>
          </header>
          <main className="max-w-7xl mx-auto p-6">{children}</main>
        </div>
      </body>
    </html>
  )
}
