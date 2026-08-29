import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // The browser calls /api/* (same origin, no CORS needed).
    // The Next.js server proxies to the backend over the internal Docker network.
    // API_URL is a server-side var — it never touches the client bundle.
    const backendUrl = process.env.API_URL ?? "http://api:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
