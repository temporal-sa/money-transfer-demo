import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 60000,
  expect: {
    timeout: 10000
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:7070',
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: './starttemporalserver.sh',
      cwd: '../ui',
      port: 7233,
      timeout: 30000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: './startlocalwebui.sh',
      cwd: '../ui', 
      port: 7070,
      timeout: 60000,
      reuseExistingServer: !process.env.CI,
    }
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
