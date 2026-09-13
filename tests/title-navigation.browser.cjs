const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

const production = fs.readFileSync(path.join(__dirname, '../custom_components/nikas_house/frontend/dist/nikas-house-overview.js'), 'utf8');
const baseline = process.env.BASELINE_HOUSE_BUNDLE && fs.readFileSync(process.env.BASELINE_HOUSE_BUNDLE, 'utf8');
const evidence = [];

(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE || undefined});
  try {
    for (const viewport of [{width:430,height:932},{width:1440,height:900}]) {
      const context = await browser.newContext({viewport, hasTouch:true});
      async function fixture(source) {
        const page = await context.newPage();
        await page.route('https://ha.test/**', route => route.fulfill({contentType:'text/html', body:'<!doctype html><style>html,body{margin:0;height:100%;font-family:Arial}</style>'}));
        await page.goto('https://ha.test/dashboard-house-v13/home?return_to=/dashboard-actions/home');
        await page.evaluate(() => {
          window.navigationTargets = [];
          window.NikasHouseNavigation = {navigate: target => window.navigationTargets.push(target)};
          localStorage.setItem('nikas.house.return_route.v1', '/dashboard-actions/home');
          sessionStorage.setItem('nikas.specialized.source_route.v1', '/dashboard-infrastructure/overview');
        });
        await page.addScriptTag({content:source});
        await page.evaluate(() => document.body.append(document.createElement('nikas-house-panel')));
        return page;
      }
      const page = await fixture(production);
      const title = page.locator('nikas-house-panel').locator('#heading');
      await title.focus();
      await page.keyboard.press('Enter');
      await page.keyboard.press('Space');
      await title.tap();
      assert.deepEqual(await page.evaluate(() => window.navigationTargets), Array(3).fill('/home/overview'));
      const geometry = await title.boundingBox();
      if (baseline) {
        const before = await fixture(baseline);
        const oldGeometry = await before.locator('nikas-house-panel').locator('.heading').boundingBox();
        assert.deepEqual(geometry, oldGeometry, 'semantic title change must preserve its exact bounding box');
        await before.close();
      }
      evidence.push({viewport,geometry,actions:['Enter','Space','touch'],target:'/home/overview'});
      if (process.env.NIKAS_SCREENSHOT_DIR) {
        fs.mkdirSync(process.env.NIKAS_SCREENSHOT_DIR,{recursive:true});
        await page.screenshot({path:path.join(process.env.NIKAS_SCREENSHOT_DIR,`house-title-${viewport.width}.png`)});
      }
      await context.close();
    }
    console.log(JSON.stringify(evidence,null,2));
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error);process.exit(1);});
