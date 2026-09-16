import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Produces a minimal self-contained server bundle (node_modules pruned to
  // only what's traced as actually used) so the Docker image doesn't need a
  // full `npm install` at runtime.
  output: "standalone",
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
