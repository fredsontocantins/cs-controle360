import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: false,
  typescript: {
    // Ignore legacy frontend directory type check during Next.js app build
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
