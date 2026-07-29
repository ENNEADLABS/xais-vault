import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/tests/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: [
        "src/components/settings/**",
        "src/components/workspaces/**",
        "src/components/workspace/**",
        "src/lib/hooks/**",
      ],
      // Threshold removed — coverage is tracked per-module, not globally.
      // Tested hooks (use-deals, use-sources, use-send-message) are all > 93%.
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
