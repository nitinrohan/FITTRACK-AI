import type { NextConfig } from "next";

/**
 * Next.js configuration.
 *
 * API rewrites:
 *   In development: Next.js proxies /api/* → FastAPI on localhost:8000.
 *   In production:  Set NEXT_PUBLIC_API_URL to your Railway backend URL.
 *                   Requests from the browser are rewritten at the edge so
 *                   the FastAPI auth cookie (same-site) works correctly.
 *
 * INTERNAL_API_URL is used for server-side rendering (SSR) requests that
 * run inside the Vercel edge network and can hit the Railway backend directly.
 */

const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Strict mode for catching subtle React issues during development.
  reactStrictMode: true,

  // Proxy /api/* to the FastAPI backend so the browser never hits a
  // different origin (avoids CORS and keeps auth cookies working).
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
