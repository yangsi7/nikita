import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    formats: ["image/avif", "image/webp"],
  },
  async headers() {
    return [
      {
        // Defence-in-depth for the generative-art assets served from
        // portal/public/art/. When embedded as iframes on /admin/systems
        // they get sandbox="allow-scripts" via the iframe attribute, but
        // if opened standalone in a new tab (via "Open standalone") the
        // HTML runs in the full browser context — so we apply an equivalent
        // CSP sandbox header at the response level too.
        source: "/art/:path*",
        headers: [
          { key: "Content-Security-Policy", value: "sandbox allow-scripts" },
          { key: "X-Content-Type-Options", value: "nosniff" },
        ],
      },
    ];
  },
};

export default nextConfig;
