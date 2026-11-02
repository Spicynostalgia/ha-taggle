// Run from any directory. Requires Playwright and its Chromium browser.
// Optional: PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs
//           CHROMIUM_EXECUTABLE=/absolute/path/to/chromium
import { readFile, writeFile, readdir, mkdir } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';
import { inflateSync, deflateSync } from 'node:zlib';
const base = dirname(fileURLToPath(import.meta.url));
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
// Losslessly recompress Chromium's filtered PNG bytes. Preserve alpha and all pixels.
function crc32(bytes) {
  let c = 0xffffffff;
  for (const b of bytes) { c ^= b; for (let k = 0; k < 8; k++) c = (c >>> 1) ^ ((c & 1) ? 0xedb88320 : 0); }
  return (c ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const t = Buffer.from(type), n = Buffer.alloc(4), crc = Buffer.alloc(4);
  n.writeUInt32BE(data.length); crc.writeUInt32BE(crc32(Buffer.concat([t, data])));
  return Buffer.concat([n, t, data, crc]);
}
function optimize(png) {
  const parts = [], ids = [];
  for (let i = 8; i < png.length;) {
    const n = png.readUInt32BE(i), type = png.toString('ascii', i + 4, i + 8);
    const data = png.subarray(i + 8, i + 8 + n);
    if (type === 'IDAT') ids.push(data); else parts.push({type, data});
    i += n + 12;
  }
  const raw = inflateSync(Buffer.concat(ids));
  const options = [0, 1, 2, 3].map(strategy => deflateSync(raw, {level: 9, strategy}));
  const compressed = options.sort((a,b) => a.length - b.length)[0];
  const out = Buffer.concat([png.subarray(0,8), ...parts.filter(p => p.type !== 'IEND').map(p => chunk(p.type,p.data)), chunk('IDAT',compressed), chunk('IEND',Buffer.alloc(0))]);
  if (!inflateSync(compressed).equals(raw)) throw new Error('PNG pixel data changed');
  return out.length < png.length ? out : png;
}
const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE || undefined, args: ['--no-sandbox']});
const checks = [];
try {
  for (const name of (await readdir(base)).filter(n => n.endsWith('.svg')).sort()) {
    const source = await readFile(join(base,name),'utf8');
    const [,ws,hs] = source.match(/viewBox="0 0 (\d+) (\d+)"/), w = +ws, h = +hs;
    const page = await browser.newPage({viewport:{width:w,height:h}, deviceScaleFactor:2});
    await page.setContent(`<style>html,body{margin:0;background:transparent}svg{display:block}</style>${source}`);
    await page.evaluate(() => document.fonts.ready);
    const clipped = await page.locator('svg').evaluate(svg => [...svg.querySelectorAll('text')].flatMap(t => {
      const b = t.getBBox(), v = svg.viewBox.baseVal;
      return b.x < 0 || b.y < 0 || b.x + b.width > v.width || b.y + b.height > v.height ? [t.textContent] : [];
    }));
    if (clipped.length) throw new Error(`${name}: clipped text: ${clipped.join(', ')}`);
    const png = await page.screenshot({omitBackground:true});
    const optimized = optimize(png);
    await writeFile(join(base,name.replace('.svg','.png')),optimized);
    checks.push({asset:name,width:w*2,height:h*2,bytes:optimized.length,clipped});
    if (name === 'social-preview.svg') {
      await writeFile(join(base,'..',name),source);
      await page.close();
      const social = await browser.newPage({viewport:{width:w,height:h},deviceScaleFactor:1});
      await social.setContent(`<style>html,body{margin:0}svg{display:block}</style>${source}`);
      await social.evaluate(() => document.fonts.ready);
      await writeFile(join(base,'..','social-preview.png'),optimize(await social.screenshot()));
      await social.close();
    } else await page.close();
  }
  if (process.env.REVIEW_DIR) {
    await mkdir(process.env.REVIEW_DIR,{recursive:true});
    for (const width of [880,360]) {
      const page = await browser.newPage({viewport:{width,height:1000},deviceScaleFactor:1});
      await page.goto(pathToFileURL(join(base,'preview.html')).href);
      await page.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error(`Preview overflows at ${width}px`);
      await page.screenshot({path:join(process.env.REVIEW_DIR,`preview-${width}.png`),fullPage:true});
      for (const theme of ['light','dark']) {
        await page.locator(`#${theme}`).screenshot({path:join(process.env.REVIEW_DIR,`family-${theme}-${width}.png`)});
      }
      await page.close();
      // Exact requested scaled widths, independently of preview gutters.
      for (const name of ['hero-light','hero-dark','how-it-works-light','how-it-works-dark','hero-mobile-light','hero-mobile-dark','how-it-works-mobile-light','how-it-works-mobile-dark']) {
        const p = await browser.newPage({viewport:{width,height:Math.ceil(width*(name.includes('mobile')?(name.startsWith('hero')?600/720:824/720):(name.startsWith('hero')?520/1600:300/1600)))},deviceScaleFactor:1});
        await p.goto(pathToFileURL(join(base,'preview.html')).href);
        await p.setContent(`<style>html,body{margin:0;background:transparent}img{display:block;width:100%;height:auto}</style><img src="${pathToFileURL(join(base,name+'.png')).href}">`);
        await p.evaluate(() => document.querySelector('img').decode());
        await p.screenshot({path:join(process.env.REVIEW_DIR,`${name}-${width}.png`)});
        await p.close();
      }
    }
  }
} finally { await browser.close(); }
console.log(JSON.stringify(checks,null,2));
