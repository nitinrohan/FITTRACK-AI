/** @type {import('next').NextConfig} */

/**
 * Next.js configuration.
 *
 * API rewrites:
 *   In development: Next.js proxies /api/* → FastAPI on localhost:8000.
 *   In production:  Set NEXT_PUBLIC_API_URL to your Railway backend URL.
 *                   Requests from from the browser are rewritten so the
 *                   FastAPI auth cookie (same-site) works correctly.
 *
 * INTERNAL_API_URL is used for SSR requests running inside Vercel's edge.
 */

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,

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
