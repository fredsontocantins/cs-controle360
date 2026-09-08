import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: false,
  typescript: {
    // Ignore build errors caused by legacy non-Next.js code in frontend-legacy directory
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
