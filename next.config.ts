import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* reactCompiler requires babel-plugin-react-compiler which is not installed */
};

export default nextConfig;

import('@opennextjs/cloudflare').then(m => m.initOpenNextCloudflareForDev());
