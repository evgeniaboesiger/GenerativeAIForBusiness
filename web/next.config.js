/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Proxy frontend /api/* calls to the FastAPI backend. Override with
    // API_BASE_URL if the backend is not on localhost:8000.
    const base = process.env.API_BASE_URL || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${base}/api/:path*` }];
  },
}

module.exports = nextConfig
