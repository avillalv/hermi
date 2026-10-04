import { defineConfig } from "@playwright/test";

// Kit projects (WF-130.2). All 390 by 844 at device scale factor 2; light and dark are looped inside the tests.
const use = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, baseURL: "http://localhost:5173" };

export default defineConfig({
  testDir: "./e2e/kit",
  outputDir: "../../test-results",
  reporter: [["list"]],
  workers: 1,
  projects: [
    { name: "kit", testMatch: "kit.spec.ts", use },
    { name: "kit-metrics", testMatch: "kit-metrics.spec.ts", use },
    { name: "kit-shell", testMatch: "shell.spec.ts", use },
    { name: "kit-parity", testMatch: "kit-parity.spec.ts", use, timeout: 180_000 },
  ],
  webServer: {
    command: "npm run dev -- --port 5173 --strictPort",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
