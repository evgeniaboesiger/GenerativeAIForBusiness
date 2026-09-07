export default function RegisterPage() {
  return (
    <div className="max-w-md mx-auto card">
      <h2 className="text-2xl font-semibold">Create an account</h2>
      <form className="mt-4 space-y-4">
        <input placeholder="Full name" className="w-full p-2 border rounded" />
        <input placeholder="Email" className="w-full p-2 border rounded" />
        <input placeholder="Password" type="password" className="w-full p-2 border rounded" />
        <div className="flex justify-end">
          <button className="px-4 py-2 bg-accent text-white rounded-lg">Register</button>
        </div>
      </form>
    </div>
  )
}
