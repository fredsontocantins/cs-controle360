import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: false,
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
