import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable reactCompiler since babel-plugin-react-compiler is missing and causing build failure
  reactCompiler: false,
};

export default nextConfig;
