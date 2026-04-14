import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    formats: ["image/avif", "image/webp"],
  },
  // Ensure the generative-art HTML files (read at runtime by the /admin/systems/art/[slug]
  // route handler via fs.readFile) are bundled into the serverless deployment. Without
  // this, Vercel's file-tracing misses them because the path is computed dynamically.
  outputFileTracingIncludes: {
    "/admin/systems/art/[slug]": [
      "./src/app/admin/systems/_art/*.html",
    ],
  },
};

export default nextConfig;
