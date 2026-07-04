import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disabling reactCompiler as a workaround for CI build failures
  // where babel-plugin-react-compiler is missing in the environment.
  reactCompiler: false,
};

export default nextConfig;
