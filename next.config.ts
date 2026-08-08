import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable reactCompiler since babel-plugin-react-compiler is not installed
  reactCompiler: false,
  // Ignore TypeScript build errors for legacy directories (e.g., frontend-legacy)
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
