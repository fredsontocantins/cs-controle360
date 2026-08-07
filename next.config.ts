import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disabled reactCompiler to prevent build failures when babel-plugin-react-compiler is not installed.
  reactCompiler: false,
};

export default nextConfig;
