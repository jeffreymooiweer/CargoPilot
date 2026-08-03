import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    // Playwright-specs staan in e2e/ en horen niet bij deze run.
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
