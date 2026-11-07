// Production static image, synthetic browser-only API responses; no production DB.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const origin = process.env.SMOKE_ORIGIN || 'http://127.0.0.1:8080';
const product = {id:'sample-ci',slug:'sample-ci',title:'SAMPLE CI tee',description:'SAMPLE only',
  image_url:'/images/storefront-empty.svg',availability:'available',min_price_minor:100000,
  variants:[{id:901,sku:'SAMPLE-CI-M',size:'M',color:'Ink',price_minor:100000,availability:'available',is_active:true}],media:[]};
(async()=>{
  const browser = await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined});
  try {
    for (const viewport of [{width:1440,height:900},{width:390,height:844}]) {
      const page = await browser.newPage({viewport});
      const errors=[];
      page.on('pageerror', error=>errors.push(error.message));
      await page.route('**/api/v1/**', async route=>{
        const path = new URL(route.request().url()).pathname;
        let body, status=200;
        if (path.includes('/auth/')) {body={detail:'Not signed in'};status=401;}
        else if (path.endsWith('/storefront/capabilities')) body={checkout_enabled:false,test_mode:false,bank_transfer_enabled:false};
        else if (path.endsWith('/products/sample-ci')) body=product;
        else if (path.endsWith('/products')) body={products:[product],total:1};
        else if (path.endsWith('/collections')) body={collections:[]};
        else if (path.endsWith('/hero/slides')) body={slides:[]};
        else if (path.endsWith('/products/hero')) body=[];
        else if (path.includes('/settings')) body={};
        else {body={detail:'Unexpected CI request'};status=404;}
        await route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
      });
      await page.goto(origin+'/');
      await page.locator('a.product-card-title-link').waitFor();
      await page.locator('a.product-card-title-link').click();
      await page.waitForURL('**/products/sample-ci');
      await page.getByRole('heading',{name:product.title,exact:true}).waitFor();
      await page.reload();
      await page.getByRole('heading',{name:product.title,exact:true}).waitFor();
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Horizontal overflow');
      await page.locator('#btn-add-to-cart').click();
      await page.locator('#cart-drawer.is-open').waitFor();
      assert((await page.locator('#cart-items-container').textContent()).includes(product.title));
      assert(await page.locator('#btn-checkout').isDisabled(),'Closed sample checkout must stay closed');
      await page.locator('#cart-close-btn').click();
      await page.goto(origin+'/vendor');
      await page.locator('#vp-login-form').waitFor();
      await page.goto(origin+'/admin');
      await page.locator('input[type=password]').waitFor();
      assert.deepEqual(errors,[]);
      await page.close();
    }
    console.log('PASS: desktop/mobile catalog → product, deep reload, vendor/admin login');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
