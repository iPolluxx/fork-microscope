const {chromium}=require('playwright');const fs=require('fs'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});const errors=[];page.on('pageerror',e=>errors.push(e.message));const base=process.env.DASHBOARD_URL;if(!base)throw Error('DASHBOARD_URL required');try{
const checks=[];
for(const path of ['/','/live.html','/observatory.html','/compare.html']){
 const response=await page.goto(base+path);assert.equal(response.status(),200);
 await page.locator('.worker-strip').waitFor();if(path==='/'){assert.match(await page.locator('#set-list').innerText(),/Connect a worker/);assert.equal(await page.locator('#workspace-error').isVisible(),false);assert.equal(await page.locator('#batches-error').isVisible(),false);}assert.match(await page.locator('.worker-strip').innerText(),/not connected/);
 assert.equal(await page.evaluate(()=>window.workerConnection().connected),false);
 await page.getByRole('button',{name:'Connect worker',exact:true}).click();await page.locator('.worker-dialog').waitFor({state:'visible'});
 assert.equal(await page.locator('[data-origin]').textContent(),base);
 await page.locator('[data-close]').click();
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),path+' overflow');await page.setViewportSize({width:1440,height:1000});checks.push(path);
}
for(const path of ['/api/live/status','/.git/config','/.env','/live-runs/result.json'])assert.equal((await page.request.get(base+path)).status(),404,path);
await page.goto(base+'/');await page.locator('.worker-strip').waitFor();await page.screenshot({path:'reports/gcp-hosting/desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});await page.screenshot({path:'reports/gcp-hosting/mobile.png',fullPage:true});assert.deepEqual(errors,[]);
fs.writeFileSync('reports/gcp-hosting/browser-checks.json',JSON.stringify({passed:true,url:base,pages:checks,errors,checks:['public pages without Google login','no automatic worker or model connection','worker dialog includes actual public origin','desktop and mobile views','private paths and worker API absent']},null,2));console.log('Public Cloud Run browser QA passed');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
