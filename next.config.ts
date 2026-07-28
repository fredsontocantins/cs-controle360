import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disabling reactCompiler as the required peer dependency babel-plugin-react-compiler is not installed
  reactCompiler: false,
};

export default nextConfig;
