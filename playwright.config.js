import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./ui-tests",
  timeout: 30000,
  use: { baseURL: "http://127.0.0.1:8877", headless: true },
  webServer: {
    command: `${process.env.PYTHON || "python"} -m imagespec_designer.demo --port 8877`,
    url: "http://127.0.0.1:8877",
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
