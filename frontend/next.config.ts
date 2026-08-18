import type {NextConfig} from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  // Emits a minimal server bundle so the runtime image does not ship node_modules.
  output: 'standalone',
  // Pin the workspace root; without it Turbopack walks up past the repo and
  // picks up unrelated lockfiles in the developer's home directory.
  turbopack: {root: import.meta.dirname},
  poweredByHeader: false,
  images: {
    // Product images are served from S3/MinIO (Cloudflare R2 in production).
    remotePatterns: [
      {protocol: 'http', hostname: 'localhost', port: '9100', pathname: '/**'},
      {protocol: 'http', hostname: 'minio', port: '9000', pathname: '/**'},
      {protocol: 'https', hostname: '**.r2.dev', pathname: '/**'}
    ],
    formats: ['image/webp']
  }
};

export default withNextIntl(nextConfig);
