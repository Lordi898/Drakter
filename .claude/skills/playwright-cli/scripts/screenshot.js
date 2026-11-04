#!/usr/bin/env node
/**
 * Playwright Screenshot Capture Script
 * 
 * Usage:
 *   node screenshot.js <url> [output-path] [--full-page] [--width=1280] [--height=720]
 * 
 * Examples:
 *   node screenshot.js https://example.com
 *   node screenshot.js https://example.com screenshot.png
 *   node screenshot.js https://example.com full.png --full-page
 *   node screenshot.js https://example.com --width=1920 --height=1080
 */

const { chromium } = require('playwright');
const path = require('path');

async function captureScreenshot(options) {
  const {
    url,
    outputPath = 'screenshot.png',
    fullPage = false,
    width = 1280,
    height = 720,
    timeout = 30000,
  } = options;

  const browser = await chromium.launch();
  
  try {
    const context = await browser.newContext({
      viewport: { width, height },
    });
    
    const page = await context.newPage();
    await page.goto(url, { timeout, waitUntil: 'networkidle' });
    
    const screenshotPath = path.isAbsolute(outputPath) 
      ? outputPath 
      : path.join(process.cwd(), outputPath);
    
    await page.screenshot({
      path: screenshotPath,
      fullPage,
    });
    
    console.log(`Screenshot saved: ${screenshotPath}`);
    return screenshotPath;
  } finally {
    await browser.close();
  }
}

// CLI handling
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`
Usage: node screenshot.js <url> [output-path] [options]

Options:
  --full-page       Capture full scrollable page
  --width=<n>       Viewport width (default: 1280)
  --height=<n>      Viewport height (default: 720)
  --timeout=<ms>    Navigation timeout (default: 30000)
  -h, --help        Show this help

Examples:
  node screenshot.js https://example.com
  node screenshot.js https://example.com output.png
  node screenshot.js https://example.com --full-page
  node screenshot.js https://example.com shot.png --width=1920 --height=1080
`);
    process.exit(0);
  }

  const options = {
    url: args.find(a => a.startsWith('http')),
    outputPath: args.find(a => !a.startsWith('http') && !a.startsWith('--')) || 'screenshot.png',
    fullPage: args.includes('--full-page'),
    width: parseInt(args.find(a => a.startsWith('--width='))?.split('=')[1]) || 1280,
    height: parseInt(args.find(a => a.startsWith('--height='))?.split('=')[1]) || 720,
    timeout: parseInt(args.find(a => a.startsWith('--timeout='))?.split('=')[1]) || 30000,
  };

  if (!options.url) {
    console.error('Error: URL is required');
    process.exit(1);
  }

  captureScreenshot(options).catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
  });
}

module.exports = { captureScreenshot };
