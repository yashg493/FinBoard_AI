/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow WebSocket rewrites in dev — in prod these hit Cloud Run directly
  async rewrites() {
    return process.env.NODE_ENV === "development"
      ? [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }]
      : [];
  },
};

module.exports = nextConfig;
