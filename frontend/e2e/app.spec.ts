import { expect, test } from '@playwright/test';

const BACKEND_URL = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

test.beforeAll(async ({ request }) => {
  const response = await request.get(`${BACKEND_URL}/health`, { timeout: 5_000 }).catch(() => null);
  if (!response || !response.ok()) {
    throw new Error(
      `ReviewBot backend is not available at ${BACKEND_URL}. Start it with: uvicorn api_server:app --reload --host 127.0.0.1 --port 8000`
    );
  }
});

test('loads the main application shell @smoke', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /ReviewBot Web UI/i })).toBeVisible();
  await expect(page.getByText(/Backend/i)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Single Code Review' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Multi-file Review' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reports' })).toBeVisible();
});

test('opens report history and can display an empty or detail state @smoke', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Reports' }).click();

  await expect(page.getByRole('heading', { name: 'Report History' })).toBeVisible();

  const historyItems = page.locator('.history-item');
  if ((await historyItems.count()) === 0) {
    await expect(page.getByText('No saved reports yet.')).toBeVisible();
  } else {
    await historyItems.first().click();
    await expect(page.getByRole('heading', { name: 'Report Metadata' })).toBeVisible();
  }
});

test('runs the single-code review flow without requiring a real LLM key', async ({ page }) => {
  await page.goto('/');

  await page.locator('textarea').fill("API_KEY = 'abc123'\nprint(API_KEY)\n");
  await page.getByRole('button', { name: 'Start Review' }).click();

  await expect(page.getByRole('heading', { name: 'Realtime Events' })).toBeVisible();
  await expect(page.locator('.timeline-item, .alert, .markdown-body, .report-body').first()).toBeVisible({
    timeout: 90_000
  });
});

test('supports multi-file selection, preview, remove, and clear actions @smoke', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Multi-file Review' }).click();

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles([
    {
      name: 'main.py',
      mimeType: 'text/x-python',
      buffer: Buffer.from('def main():\n    print("hello")\n')
    },
    {
      name: 'utils.py',
      mimeType: 'text/x-python',
      buffer: Buffer.from('def add(a, b):\n    return a + b\n')
    }
  ]);

  await expect(page.locator('.selected-file-row').filter({ hasText: 'main.py' })).toBeVisible();
  await expect(page.locator('.selected-file-row').filter({ hasText: 'utils.py' })).toBeVisible();

  await page.getByRole('button', { name: 'Preview' }).first().click();
  await expect(page.getByText(/def main/)).toBeVisible();

  await page.getByRole('button', { name: 'Remove' }).first().click();
  await expect(page.locator('.selected-file-row').filter({ hasText: 'utils.py' })).toBeVisible();

  await page.getByRole('button', { name: 'Clear Files' }).click();
  await expect(page.getByText('0 files selected | 0 characters')).toBeVisible();
});
