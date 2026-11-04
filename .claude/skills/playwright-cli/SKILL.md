---
name: playwright-cli
description: Browser automation and testing with Playwright CLI. Use when Claude needs to automate browser interactions, run end-to-end tests, capture screenshots, generate test code, set up Playwright in a project, or control browsers programmatically. Triggers include requests for browser automation, web testing, screenshot capture, test generation, UI testing, form filling, web scraping with browser rendering, or Playwright installation/setup.
---

# Playwright CLI

Playwright is a browser automation framework supporting Chromium, Firefox, and WebKit across Windows, macOS, and Linux.

## Installation

### Quick Setup (New or Existing Project)

```bash
npm init playwright@latest
```

Prompts for: TypeScript/JavaScript, test folder name, GitHub Actions workflow, browser installation.

### Manual Installation

```bash
npm install -D @playwright/test
npx playwright install              # All browsers
npx playwright install chromium     # Specific browser
npx playwright install --with-deps  # Include system dependencies (Linux)
```

### System Requirements

- Node.js 20.x, 22.x, or 24.x
- Windows 11+, macOS 14+, or Debian 12+/Ubuntu 22.04+

### Linux Dependencies

```bash
npx playwright install-deps         # Install system dependencies
```

## CLI Commands

### Run Tests

```bash
npx playwright test                           # All tests
npx playwright test tests/example.spec.ts     # Single file
npx playwright test -g "test name"            # By title pattern
npx playwright test --project=chromium        # Specific browser
npx playwright test --headed                  # Show browser
npx playwright test --debug                   # Debug mode with Inspector
npx playwright test --ui                      # Interactive UI mode
npx playwright test --workers=1               # Single worker (no parallelism)
npx playwright test --retries=2               # Retry flaky tests
npx playwright test --trace=on                # Enable tracing
npx playwright test --reporter=html           # HTML report
```

### Code Generation

```bash
npx playwright codegen                        # Start recorder
npx playwright codegen https://example.com    # Record on URL
npx playwright codegen --target=python        # Generate Python code
```

### Reports and Traces

```bash
npx playwright show-report                    # Open HTML report
npx playwright show-trace trace.zip           # View trace file
```

### Browser Management

```bash
npx playwright install                        # Install all browsers
npx playwright install chromium webkit        # Specific browsers
npx playwright install --force                # Force reinstall
npx playwright uninstall                      # Remove browsers
npx playwright clear-cache                    # Clear caches
```

## Writing Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';

test('example test', async ({ page }) => {
  await page.goto('https://example.com');
  await expect(page).toHaveTitle(/Example/);
});
```

### Configuration (playwright.config.ts)

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  retries: 2,
  use: {
    baseURL: 'https://example.com',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit' } },
  ],
});
```

## Browser Automation

### Navigation

```typescript
await page.goto('https://example.com');
await page.goBack();
await page.goForward();
await page.reload();
```

### Locators (Recommended)

```typescript
// By role (preferred)
page.getByRole('button', { name: 'Submit' })
page.getByRole('textbox', { name: 'Email' })
page.getByRole('link', { name: 'Home' })
page.getByRole('checkbox', { name: 'Accept' })

// By text/label
page.getByText('Welcome')
page.getByLabel('Username')
page.getByPlaceholder('Enter email')
page.getByTitle('Close')
page.getByAltText('Logo')

// By test ID
page.getByTestId('submit-button')

// CSS/XPath (fallback)
page.locator('#id')
page.locator('.class')
page.locator('[data-attr="value"]')
page.locator('xpath=//button')
```

### Actions

```typescript
// Click
await page.getByRole('button').click();
await page.getByRole('link').click({ button: 'right' });
await page.getByRole('button').dblclick();

// Text input
await page.getByRole('textbox').fill('text');
await page.getByRole('textbox').clear();
await page.getByRole('textbox').pressSequentially('slow typing');

// Checkboxes/Radio
await page.getByRole('checkbox').check();
await page.getByRole('checkbox').uncheck();
await page.getByRole('checkbox').setChecked(true);

// Select dropdown
await page.getByRole('combobox').selectOption('value');
await page.getByRole('combobox').selectOption({ label: 'Option' });

// File upload
await page.getByLabel('Upload').setInputFiles('file.pdf');
await page.getByLabel('Upload').setInputFiles(['file1.pdf', 'file2.pdf']);

// Keyboard
await page.keyboard.press('Enter');
await page.keyboard.press('Control+A');
await page.keyboard.type('Hello');

// Mouse
await page.mouse.click(100, 200);
await page.mouse.dblclick(100, 200);
await page.getByRole('button').hover();

// Drag and drop
await page.locator('#source').dragTo(page.locator('#target'));
```

### Waiting

```typescript
// Auto-waiting is built-in for most actions
// Explicit waits when needed:
await page.waitForURL('**/dashboard');
await page.waitForLoadState('networkidle');
await page.waitForSelector('.element');
await page.waitForTimeout(1000);  // Avoid if possible
await expect(page.locator('.item')).toBeVisible();
```

### Assertions

```typescript
// Page assertions
await expect(page).toHaveTitle(/Title/);
await expect(page).toHaveURL(/dashboard/);

// Element assertions
await expect(page.locator('.item')).toBeVisible();
await expect(page.locator('.item')).toBeHidden();
await expect(page.locator('.item')).toBeEnabled();
await expect(page.locator('.item')).toBeDisabled();
await expect(page.locator('.item')).toHaveText('text');
await expect(page.locator('.item')).toHaveValue('value');
await expect(page.locator('.item')).toHaveCount(5);
await expect(page.locator('.item')).toHaveAttribute('href', '/link');
```

## Screenshots

### Capture to File

```typescript
// Full viewport
await page.screenshot({ path: 'screenshot.png' });

// Full page (scrollable)
await page.screenshot({ path: 'full.png', fullPage: true });

// Element only
await page.locator('.header').screenshot({ path: 'header.png' });

// With options
await page.screenshot({
  path: 'screenshot.jpg',
  type: 'jpeg',
  quality: 80,
  fullPage: true,
  clip: { x: 0, y: 0, width: 800, height: 600 },
  omitBackground: true,  // Transparent PNG
});
```

### Capture to Buffer

```typescript
const buffer = await page.screenshot();
// Use buffer for further processing
```

### Screenshot Script for Workspace

```typescript
import { chromium } from 'playwright';
import path from 'path';

async function captureScreenshot(url: string, filename: string) {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(url);
  await page.screenshot({ path: path.join(process.cwd(), filename) });
  await browser.close();
}

captureScreenshot('https://example.com', 'screenshot.png');
```

## Standalone Scripts (No Test Framework)

```typescript
import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto('https://example.com');
  await page.getByRole('textbox', { name: 'Search' }).fill('query');
  await page.getByRole('button', { name: 'Search' }).click();
  await page.screenshot({ path: 'result.png' });

  await browser.close();
})();
```

Run with: `npx ts-node script.ts` or `node script.js`

## Common Patterns

### Login and Auth State

```typescript
// Save auth state
await page.context().storageState({ path: 'auth.json' });

// Reuse auth state
const context = await browser.newContext({ storageState: 'auth.json' });
```

### Handle Dialogs

```typescript
page.on('dialog', async dialog => {
  console.log(dialog.message());
  await dialog.accept();  // or dialog.dismiss()
});
```

### Multiple Tabs

```typescript
const [newPage] = await Promise.all([
  context.waitForEvent('page'),
  page.click('a[target="_blank"]'),
]);
await newPage.waitForLoadState();
```

### Frames

```typescript
const frame = page.frameLocator('#iframe');
await frame.getByRole('button').click();
```

### Network Interception

```typescript
await page.route('**/api/*', route => {
  route.fulfill({ body: JSON.stringify({ data: 'mocked' }) });
});
```

## Quick Reference

| Task | Command/Code |
|------|--------------|
| Install | `npm init playwright@latest` |
| Run tests | `npx playwright test` |
| Headed mode | `npx playwright test --headed` |
| Debug | `npx playwright test --debug` |
| UI mode | `npx playwright test --ui` |
| Generate code | `npx playwright codegen URL` |
| Screenshot | `await page.screenshot({ path: 'shot.png' })` |
| Full page shot | `await page.screenshot({ path: 'shot.png', fullPage: true })` |
| Click | `await page.getByRole('button').click()` |
| Fill input | `await page.getByRole('textbox').fill('text')` |
| Navigate | `await page.goto('https://url.com')` |
| Assert visible | `await expect(locator).toBeVisible()` |
