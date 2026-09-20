// Run with Playwright installed: node scripts/check_house_geometry.cjs
const { chromium, webkit } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const path = require('node:path');

(async () => {
  const browser = await (process.env.HOUSE_BROWSER === 'webkit' ? webkit : chromium).launch({headless: true});
  try {
    for (const [width, height] of [[430,932], [932,430], [768,1024], [1024,768], [1440,900]]) {
      const page = await browser.newPage({viewport: {width, height}});
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.setContent('<style>html,body{margin:0;height:100%}ha-card{display:block}</style>');
      await page.evaluate(() => {
        customElements.define('ha-card', class extends HTMLElement {
          constructor() {
            super();
            this.attachShadow({mode:'open'}).innerHTML = '<style>:host{display:block}</style><slot></slot>';
          }
        });
      });
      await page.addScriptTag({content: fs.readFileSync(path.join(__dirname, '../custom_components/nikas_house/frontend/dist/nikas-house-overview.js'), 'utf8')});
      await page.evaluate(() => {
        const panel = document.createElement('nikas-house-panel');
        document.body.append(panel);
        panel.panel = {config: {hero: {entities: {}, routes: {}}, tabs: [{id:'home',label:'Дом',path:'/dashboard-house-v13/home'}]}};
        panel.hass = {states: {}};
        window.testPanel = panel;
      });
      await page.waitForTimeout(100);
      const before = await page.evaluate(() => {
        const root = window.testPanel.shadowRoot;
        const hero = root.querySelector('nikas-house-main-hero');
        const scene = hero.shadowRoot.querySelector('.hero');
        window.testScene = scene;
        const rect = el => { const r = el.getBoundingClientRect(); return {top:r.top,bottom:r.bottom,width:r.width,height:r.height}; };
        return {header:rect(root.querySelector('.header')),footer:rect(root.querySelector('.bottom')),viewport:rect(root.querySelector('.canvas-viewport')),scene:rect(scene),overflow:document.documentElement.scrollWidth > innerWidth};
      });
      console.log(width, height, before);
      assert.equal(errors.length, 0, errors.join('\n'));
      assert.ok(before.scene.height > 100, 'House scene collapsed');
      assert.ok(before.scene.top >= before.header.bottom, 'Scene overlaps header');
      assert.ok(before.scene.bottom <= before.footer.top + 1, 'Scene overlaps footer');
      assert.equal(before.overflow, false, 'Horizontal page overflow');
      const after = await page.evaluate(() => {
        const panel = window.testPanel;
        panel.hass = {states: {}};
        panel._setTransform(1.5, -20, -20);
        panel._resetTransform(false);
        const scene = panel.shadowRoot.querySelector('nikas-house-main-hero').shadowRoot.querySelector('.hero');
        return {same:scene === window.testScene, height:scene.getBoundingClientRect().height};
      });
      assert.equal(after.same, true, 'Telemetry replaced scene');
      assert.equal(after.height, before.scene.height, 'Zoom reset changed scene height');
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
