import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disabled as a workaround for missing build-time dependencies in CI.
  // Re-enable after adding 'babel-plugin-react-compiler' to package.json.
  reactCompiler: false,
};

export default nextConfig;
