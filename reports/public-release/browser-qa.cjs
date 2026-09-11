const {chromium}=require('playwright');
const fs=require('fs'), assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const errors=[],checks=[]; page.on('pageerror',e=>errors.push(e.message));
 try {
  for(const path of ['workspace.html','live.html','observatory.html?run=352516a7e5184bc6841d8eb075ecb09a','compare.html']){
   await page.goto('http://127.0.0.1:8767/'+path);await page.locator('#method-credit').waitFor();
   assert.match(await page.locator('#method-credit').innerText(),/Goodfire/);
   if(path.startsWith('observatory')){
    await page.locator('#evidence').waitFor({state:'visible'});
    assert.match(await page.locator('#method-credit').innerText(),/Recorded upstream revision:\s*d32fed8d4162/);
    await page.locator('#refinement-disclosure').click();await page.locator('#ref-reference').click();
    assert.equal(await page.locator('#ref-samples').inputValue(),'100');
    assert(await page.locator('#ref-run').isDisabled());
   }
   if(path==='live.html')assert.equal(await page.locator('#model-id').inputValue(),'');
   await page.setViewportSize({width:390,height:844});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),path+' mobile overflow');
   await page.setViewportSize({width:1440,height:1000});checks.push(path);
  }
  for(const path of ['/.git/config','/.env','/live-runs/','/workspace-data/','/README.md']){
   const r=await page.request.get('http://127.0.0.1:8767'+path);assert.equal(r.status(),404,path);
  }
  await page.goto('http://127.0.0.1:8767/workspace.html');await page.locator('#method-credit').waitFor();
  await page.screenshot({path:'reports/public-release/workspace.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'reports/public-release/workspace-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);
  fs.writeFileSync('reports/public-release/browser-checks.json',JSON.stringify({passed:true,checks,errors,notes:['Shared attribution on all four primary views','Recorded upstream revision on real saved evidence','No personal default model','Reference preset available; compute disabled without matching model','Mobile widths fit','Private filesystem paths return 404']},null,2));
  console.log('Public-facing browser checks passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
