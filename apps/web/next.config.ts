import path from "node:path";
import type { NextConfig } from "next";

// Where this server reaches the API (ADR-0014). Rewrites are fixed when the app is built, so the
// Docker image sets API_INTERNAL_URL at build time; `pnpm dev` uses the API on localhost.
const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Self-contained server bundle for the Docker image; trace files from the monorepo root.
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../../"),
  cacheComponents: true,
  partialPrefetching: true,
  // The generated API client is TypeScript source from the workspace.
  transpilePackages: ["@qbank/api-client"],
  // The browser only ever talks to this origin: API calls are forwarded, so the session cookie is
  // first-party, no CORS is needed and the API's Origin check sees the web app's address.
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${apiUrl}/api/v1/:path*` },
      { source: "/health/:path*", destination: `${apiUrl}/health/:path*` },
    ];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
