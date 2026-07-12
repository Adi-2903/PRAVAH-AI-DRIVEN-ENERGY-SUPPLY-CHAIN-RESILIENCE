import type {NextConfig} from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  eslint: {
    // TODO: set to false once the remaining lint findings are cleared.
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  output: 'standalone',
  // Pin the file-tracing root to this app so Next doesn't pick the monorepo
  // root when multiple lockfiles are present.
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
