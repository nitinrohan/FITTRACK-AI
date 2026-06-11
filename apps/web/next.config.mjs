/** @type {import('next').NextConfig} */
const nextConfig = {
  // Strict mode catches common mistakes during development.
  reactStrictMode: true,

  // Standalone output mode for optimal Docker deployment.
  output: "standalone",

  // Environment variables available at build time.
  env: {},

  // API rewrites: proxy /api/v1/* to the FastAPI backend in development.
  async rewrites() {
    const apiUrl =
      process.env.INTERNAL_API_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://localhost:8000";

    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },

  // Disable the X-Powered-By header.
  poweredByHeader: false,
};

export default nextConfig;
