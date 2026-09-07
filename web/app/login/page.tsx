export default function LoginPage() {
  return (
    <div className="max-w-md mx-auto card">
      <h2 className="text-2xl font-semibold">Login</h2>
      <form className="mt-4 space-y-4">
        <input placeholder="Email" className="w-full p-2 border rounded" />
        <input placeholder="Password" type="password" className="w-full p-2 border rounded" />
        <div className="flex justify-end">
          <button className="px-4 py-2 bg-accent text-white rounded-lg">Sign in</button>
        </div>
      </form>
    </div>
  )
}
