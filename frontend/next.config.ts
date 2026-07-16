import type {NextConfig} from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  eslint: {
    // Lint runs on every build and gates it on errors. The one opinionated
    // perf rule (react-hooks/set-state-in-effect) is downgraded to a warning
    // in eslint.config.mjs; all correctness rules remain build-breaking.
    ignoreDuringBuilds: false,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  // `output: 'standalone'` supports the self-hosted / Docker frontend path;
  // Vercel ignores it and builds natively, so it's safe for both deploy targets.
  output: 'standalone',
  devIndicators: false,
  // Pin the file-tracing root to this app so Next doesn't pick the monorepo
  // root when multiple lockfiles are present.
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
