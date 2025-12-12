import type { NextConfig } from 'next'
import path from 'path'

const nextConfig: NextConfig = {
  turbopack: {
    // Explicitly set workspace root to portal directory to avoid parent lockfile detection
    root: path.resolve(__dirname),
  },
}

export default nextConfig
