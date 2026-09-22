import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep isolated test builds from disturbing the running development server.
  distDir: process.env.E2E === "1" ? ".next-e2e" : ".next",
};

export default nextConfig;
