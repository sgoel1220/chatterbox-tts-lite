import type { NextConfig } from "next";

// Proxy all /api/* requests to the creepy-brain backend to avoid CORS issues.
// Set NEXT_PUBLIC_API_URL in .env.local to point at your deployed backend.
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8006";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
