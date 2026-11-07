// Browser-only SAMPLE owner responses; never signs in or changes a real account.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const origin=process.env.SMOKE_ORIGIN||'http://127.0.0.1:8080';
const captureOnly=process.env.ADMIN_MOBILE_CAPTURE_ONLY==='true';
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||undefined});
  const results=[];
  try {
    for(const [width,height] of [[360,640],[390,844],[760,700],[768,1024],[1440,900]]) {
      const context=await browser.newContext({viewport:{width,height},isMobile:width<=760,hasTouch:width<=760});
      const page=await context.newPage();const errors=[];
      // This tests layout/scrolling, independently of third-party font availability.
      await page.route('https://fonts.googleapis.com/**',route=>route.fulfill({contentType:'text/css',body:''}));
      await page.route('https://fonts.gstatic.com/**',route=>route.abort());
      page.on('pageerror',e=>errors.push(e.message));
      await page.route('**/api/v1/**',route=>{
        const path=new URL(route.request().url()).pathname;
        let body={};
        if(path.endsWith('/auth/session')) body={authenticated:true,username:'SAMPLE owner',csrf_token:'sample-ui-only'};
        else if(path.endsWith('/preferences')) body={theme:'dark',nav_order:[],table_density:'comfortable'};
        else if(path.endsWith('/admin/products')) body={total:30,products:Array.from({length:30},(_,i)=>({id:`sample-${i}`,title:`SAMPLE product ${i}`,slug:`sample-${i}`,status:'draft'}))};
        else if(path.endsWith('/collections')) body={collections:[]};
        else if(path.endsWith('/media')) body={assets:[],total:0};
        return route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
      });
      await page.goto(origin+'/admin/products');
      await page.locator('.catalog-card').first().waitFor({state:'attached'});
      const geometry=await page.evaluate(()=>{
        const main=document.querySelector('.admin-page main'),nav=document.querySelector('#admin-sidebar nav'),sidebar=document.querySelector('#admin-sidebar'),content=document.querySelector('#admin-tab-content');
        const box=main.getBoundingClientRect();
        return {direction:getComputedStyle(document.querySelector('.admin-page > .modal-content')).flexDirection,
          sidebarHeight:sidebar.getBoundingClientRect().height,navHeight:nav.getBoundingClientRect().height,
          contentHeight:content.clientHeight,mainTop:box.top,mainBottom:box.bottom,
          pageOverflow:document.documentElement.scrollWidth>innerWidth,
          visibleLogos:[...sidebar.querySelectorAll('[id$="logo-slot"]')].filter(el=>el.getBoundingClientRect().width>0&&el.getBoundingClientRect().height>0).length};
      });
      results.push({width,height,...geometry});
      if(process.env.ADMIN_MOBILE_ARTIFACTS) {
        fs.mkdirSync(process.env.ADMIN_MOBILE_ARTIFACTS,{recursive:true});
        await page.screenshot({path:`${process.env.ADMIN_MOBILE_ARTIFACTS}/products-${width}.png`});
      }
      if(!captureOnly) {
        assert(!geometry.pageOverflow,`page overflow at ${width}`);
        assert(geometry.contentHeight>150,`content squeezed out at ${width}: ${JSON.stringify(geometry)}`);
        assert(geometry.mainBottom<=height+1,`main clipped below viewport at ${width}`);
        if(width<=760) {
          assert.equal(geometry.direction,'column');
          assert(geometry.sidebarHeight<=200,'mobile navigation occupies the screen');
          assert(geometry.navHeight<=72,'navigation buttons stretched vertically');
          assert.equal(geometry.visibleLogos,1,'duplicate sidebar branding');
        }
        const content=page.locator('#admin-tab-content');
        await content.hover();
        if(width<=760) {
          const box=await content.boundingBox();
          const cdp=await context.newCDPSession(page);
          const x=Math.round(box.x+6),y=Math.round(box.y+box.height-24);
          await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
          for(let step=1;step<=12;step++) {
            await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:y-step*15}]});
            await page.waitForTimeout(20);
          }
          await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
          await cdp.detach();
        } else await page.mouse.wheel(0,500);
        await page.waitForTimeout(350);
        if(await content.evaluate(el=>el.scrollTop)===0) {
          console.log('Scroll diagnostic',await content.evaluate(el=>{const r=el.getBoundingClientRect();return {scrollHeight:el.scrollHeight,height:el.clientHeight,overflow:getComputedStyle(el).overflowY,hit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,180)};}));
        }
        assert(await content.evaluate(el=>el.scrollTop)>0,`content does not respond to scrolling at ${width}`);
        await content.evaluate(el=>{el.scrollTop=el.scrollHeight;});
        assert(await content.evaluate(el=>el.scrollTop+el.clientHeight>=el.scrollHeight-2),'bottom content is unreachable');
        if(width<=760) {
          await page.locator('#admin-sidebar [data-tab=settings]').scrollIntoViewIfNeeded();
          assert(await page.locator('#admin-sidebar nav').evaluate(el=>el.scrollLeft)>0,'last navigation item is unreachable');
          await page.setViewportSize({width,height:480});
          assert(await content.evaluate(el=>el.clientHeight)>100,'short viewport loses scrolling area');
          await page.setViewportSize({width,height});
          await page.evaluate(()=>{const banner=document.createElement('div');banner.style.height='72px';document.body.prepend(banner);document.documentElement.style.setProperty('--lab-notice-height','72px');});
          assert(await page.locator('.admin-page main').evaluate(el=>el.getBoundingClientRect().bottom<=innerHeight+1),'lab banner pushes content below the viewport');
        }
        assert.deepEqual(errors,[]);
      }
      await context.close();
    }
    console.log(JSON.stringify(results,null,2));
    if(!captureOnly) console.log('PASS: responsive admin shell, one logo, touch/wheel scroll, bottom reachability and horizontal navigation');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
