import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "",
    NEXT_PUBLIC_BACKEND_PORT: process.env.NEXT_PUBLIC_BACKEND_PORT ?? "18033",
    NEXT_PUBLIC_OLLAMA_URL: process.env.NEXT_PUBLIC_OLLAMA_URL ?? "",
    NEXT_PUBLIC_ENV: process.env.NEXT_PUBLIC_ENV ?? "development",
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.INTERNAL_API_URL ?? "http://backend:8000"}/:path*`,
      },
    ];
  },
  httpAgentOptions: {
    keepAlive: true,
  },
};

export default nextConfig;
