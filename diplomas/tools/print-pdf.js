// Print an ERPIE document (diploma, transcript) to PDF with Chromium.
// Usage: node print-pdf.js input.html output.pdf [preview.png]
// The page size comes from the document's own @page rule.
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const [, , input, output, png] = process.argv;
  if (!input || !output) {
    console.error('Usage: node print-pdf.js input.html output.pdf [preview.png]');
    process.exit(1);
  }
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const page = await browser.newPage({ deviceScaleFactor: 2 });
  await page.goto('file://' + path.resolve(input), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.emulateMedia({ media: 'print' });
  await page.pdf({ path: output, preferCSSPageSize: true, printBackground: true, pageRanges: '1' });
  if (png) {
    await page.emulateMedia({ media: 'screen' });
    await (await page.$('article')).screenshot({ path: png });
  }
  await browser.close();
})();
