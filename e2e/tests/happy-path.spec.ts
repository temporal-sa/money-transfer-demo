import { test, expect } from '@playwright/test';
import { spawn, ChildProcess } from 'child_process';
import { promisify } from 'util';
import { killProcess } from './utils';

const sleep = promisify(setTimeout);

let workerProcess: ChildProcess | null;

const isVerbose = process.env.VERBOSE === 'true';
const stdio = isVerbose ? 'inherit' : 'pipe';

test.afterAll(async () => {
  if (workerProcess) {
    killProcess(workerProcess);
    console.log('🛑 Worker process killed');
  }
});

async function switchWorker(workerDir: string) {
  if (workerProcess) {
    killProcess(workerProcess);
    console.log('🛑 Previous worker killed');
  }
  await sleep(2000);
  
  workerProcess = spawn('./startlocalworker.sh', [], {
    cwd: workerDir,
    stdio,
    detached: true
  });
  await sleep(3000);
  console.log('✅ New worker started');
}

async function testHappyTransfer(page) {
  await page.goto('/');
  await page.click('button:has-text("Transfer")');
  await expect(page.locator('text=Transfer Complete!')).toBeVisible({ timeout: 30000 });
}

const allWorkers = [
  { name: 'go', dir: '../go' },
  { name: 'ruby', dir: '../ruby' },
  { name: 'dotnet', dir: '../dotnet' },
  { name: 'java', dir: '../java' },
  { name: 'python', dir: '../python' },
  { name: 'typeScript', dir: '../typescript' }
];

const onlyWorker = process.env.ONLY_WORKER;
const workers = onlyWorker 
  ? allWorkers.filter(w => w.name.toLowerCase() === onlyWorker.toLowerCase())
  : allWorkers;

workers.forEach(worker => {
  test(`${worker.name} worker`, async ({ page }) => {
    console.log(`🚀 Starting ${worker.name} worker test`);
    await switchWorker(worker.dir);
    await testHappyTransfer(page);
    console.log(`✅ Completed ${worker.name} worker test`);
  });
});
