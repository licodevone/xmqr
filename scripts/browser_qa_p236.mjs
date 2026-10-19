// SPDX-License-Identifier: MIT
// P236: existing local Chromium, historical guide + new lessons, no remote assets.
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const {chromium}=createRequire(import.meta.url)('playwright');
const [htmlFile,output]=process.argv.slice(2);
if(!htmlFile||!output) throw new Error('uso: browser_qa_p236.mjs ARQUIVO_HTML PASTA_NOVA');
if(fs.existsSync(output)) throw new Error('use pasta de evidencia nova');
fs.mkdirSync(output,{recursive:true});
const htmlPath=path.resolve(htmlFile),url=pathToFileURL(htmlPath).href;
const rows=[],errors=[],remoteRequests=[];
let browser,current='inicializacao';
const sha=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');
try {
  browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});
  const context=await browser.newContext({viewport:{width:1440,height:1000},colorScheme:'light',reducedMotion:'reduce'});
  const observe=page=>{
    page.on('pageerror',()=>errors.push('excecao JS'));
    page.on('dialog',async dialog=>{errors.push('dialogo inesperado');await dialog.dismiss();});
    page.on('request',request=>{if(/^https?:/.test(request.url())) remoteRequests.push('recurso HTTP remoto');});
  };
  const page=await context.newPage();observe(page);
  const theme=async(target,value)=>target.waitForFunction(value=>document.documentElement.dataset.theme===value,value);
  const noOverflow=async target=>assert.equal(await target.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  current='tema inicial segue preferencia clara do sistema sem escolha salva';
  await page.goto(url);await page.waitForLoadState('networkidle');
  await theme(page,'light');
  assert.equal(await page.locator('#guide-theme-toggle').getAttribute('aria-pressed'),'false');
  rows.push(current);

  current='sidebar aponta para aulas existentes com os mesmos titulos do corpo';
  const mapping=await page.evaluate(()=>[...document.querySelectorAll('#course-nav .nav-link')].map(link=>{
    const target=document.getElementById(decodeURIComponent(link.hash.slice(1)));
    const heading=target?.matches('section')?target.querySelector(':scope > details > summary > h2'):target?.querySelector(':scope > summary > h3,:scope > summary > h2');
    return {label:link.textContent.trim().replace(/\s+/g,' '),heading:heading?.textContent.trim().replace(/\s+/g,' '),target:!!target};
  }));
  assert(mapping.length>10);
  assert(mapping.every(item=>item.target&&item.label===item.heading),'titulo/ancora da sidebar divergiu');
  rows.push(current);

  current='itens sem filhos sao links sem seta nem aria-expanded e abrem a aula sempre';
  const leaf=page.locator('#course-nav a.nav-leaf').first();
  const leafId=(await leaf.getAttribute('href')).slice(1);
  assert.equal(await leaf.evaluate(link=>link.closest('summary')!==null),false);
  assert.equal(await leaf.getAttribute('aria-expanded'),null);
  assert.equal(await leaf.evaluate(link=>getComputedStyle(link,'::before').content),'none');
  await leaf.click();
  const opened=()=>page.evaluate(id=>{
    const target=document.getElementById(id);
    const detail=target.matches('section')?target.querySelector(':scope > details'):target.closest('details');
    return detail.open;
  },leafId);
  assert.equal(await opened(),true);
  await leaf.click();assert.equal(await opened(),true);
  await page.evaluate(()=>{if(typeof window.sync==='function')window.sync();});
  assert.equal(await page.locator('#course-nav .nav-leaf[aria-expanded]').count(),0);
  rows.push(current);

  current='pais com filhos preservam expansao e sincronizacao com o corpo';
  const parent=page.locator('#course-nav details.nav-topic').first();
  await parent.evaluate(item=>{
    const target=document.getElementById(item.dataset.topic);
    if(target)target.querySelector(':scope > details').open=false;
    item.open=false;if(typeof window.sync==='function')window.sync();
  });
  await parent.locator(':scope > summary').click({position:{x:4,y:10}});
  await page.waitForFunction(()=>document.querySelector('#course-nav details.nav-topic').open);
  await parent.locator(':scope > summary').click({position:{x:4,y:10}});
  await page.waitForFunction(()=>!document.querySelector('#course-nav details.nav-topic').open);
  rows.push(current);

  current='novas aulas de operacao aparecem na sidebar e a busca revela seu conteudo';
  const lessons=['contexto','ambiente','monitor','acesso','mqtt','operacao','reset','checklist'];
  for(const name of lessons) {
    const id='admin-web-'+name;
    const link=page.locator(`#course-nav .nav-link[href="#${id}"]`);
    assert.equal(await link.count(),1);
    await link.click();
    assert.equal(await page.locator(`#${id} > details`).getAttribute('open'),'');
  }
  await page.locator('#search').fill('Argon2id');
  assert(await page.locator('#admin-web-acesso .filter:not([hidden])').count()>0);
  await page.locator('#search').fill('');rows.push(current);

  current='checklist novo inicia pendente e cada confirmacao depende de clique manual';
  const checks=page.locator('#admin-web-checklist input[type="checkbox"]');
  assert(await checks.count()>=8);
  assert.equal(await checks.evaluateAll(nodes=>nodes.some(node=>node.checked)),false);
  const first=checks.first();
  const owner=await first.evaluate(input=>input.closest('details[id]')?.id);
  await page.locator(`#course-nav .nav-link[href="#${owner||'admin-web-checklist'}"]`).click();
  await first.check();assert.equal(await first.isChecked(),true);
  assert.equal(await checks.evaluateAll(nodes=>nodes.filter(node=>node.checked).length),1);
  await first.uncheck();rows.push(current);

  current='tema escuro e claro persistem sem alterar conteudo ou navegacao';
  await page.locator('#course-nav .nav-link[href="#admin-web-acesso"]').click();
  await page.locator('#guide-theme-toggle').click();await theme(page,'dark');
  assert.equal(await page.evaluate(()=>localStorage.getItem('xmqr-code-guide-theme')),'dark');
  assert.equal(await page.locator('#guide-theme-toggle').getAttribute('aria-pressed'),'true');
  await page.screenshot({path:path.join(output,'guide-dark-desktop.png')});
  await page.reload();await page.waitForLoadState('networkidle');await theme(page,'dark');
  await page.locator('#guide-theme-toggle').click();await theme(page,'light');
  assert.equal(await page.evaluate(()=>localStorage.getItem('xmqr-code-guide-theme')),'light');
  await page.screenshot({path:path.join(output,'guide-light-desktop.png')});
  await noOverflow(page);rows.push(current);

  current='preferencia escura do sistema e mudancas do sistema funcionam sem escolha manual';
  const osContext=await browser.newContext({viewport:{width:1280,height:900},colorScheme:'dark',reducedMotion:'reduce'});
  const osPage=await osContext.newPage();observe(osPage);
  await osPage.goto(url);await theme(osPage,'dark');
  await osPage.emulateMedia({colorScheme:'light'});await theme(osPage,'light');
  await osContext.close();rows.push(current);

  current='localStorage bloqueado preserva troca de tema e navegacao';
  const blocked=await browser.newContext({viewport:{width:1280,height:900},colorScheme:'dark',reducedMotion:'reduce'});
  await blocked.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage indisponivel','SecurityError');}}));
  const blockedPage=await blocked.newPage();observe(blockedPage);
  await blockedPage.goto(url);await theme(blockedPage,'dark');
  await blockedPage.locator('#guide-theme-toggle').click();await theme(blockedPage,'light');
  await blockedPage.locator('#course-nav a.nav-leaf').first().click();
  assert.equal(await blockedPage.locator('#course-nav .nav-leaf[aria-expanded]').count(),0);
  await blocked.close();rows.push(current);

  current='mobile oferece tema e menu funcionais sem overflow horizontal';
  await page.setViewportSize({width:390,height:844});
  await page.locator('#guide-theme-toggle').click();await theme(page,'dark');
  await page.locator('#menu-toggle').click();
  await page.locator('#course-nav .nav-link[href="#admin-web-mqtt"]').click();
  await noOverflow(page);await page.screenshot({path:path.join(output,'guide-dark-mobile.png')});
  await page.locator('#guide-theme-toggle').click();await theme(page,'light');
  await page.screenshot({path:path.join(output,'guide-light-mobile.png')});rows.push(current);

  current='impressao conserva fundo claro texto legivel e controles ocultos';
  await page.setViewportSize({width:1280,height:900});
  await page.emulateMedia({media:'print'});
  assert.equal(await page.locator('#guide-theme-controls').isVisible(),false);
  assert.equal(await page.locator('#course-nav').isVisible(),false);
  const printed=await page.evaluate(()=>({background:getComputedStyle(document.body).backgroundColor,color:getComputedStyle(document.body).color}));
  assert.equal(printed.background,'rgb(255, 255, 255)');
  assert.match(printed.color,/rgb\((0, 0, 0|17, 17, 17)\)/);
  await page.screenshot({path:path.join(output,'guide-print.png')});rows.push(current);
  assert.deepEqual(errors,[]);assert.deepEqual(remoteRequests,[]);
  fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify({status:'PASS',steps:rows,
    hashes:{html_sha256:sha(htmlPath),browser_fixture_sha256:sha(new URL(import.meta.url))},
    scope:'Arquivo HTML local, Chromium real e contas/servicos externos nao utilizados',browser:'Chromium/Playwright'},null,2),{flag:'wx'});
  console.log('P236_BROWSER_PASS',rows.length);
} catch(error) {
  fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify({status:'FAIL',steps:rows,failed_step:current,error_type:error.name,
    reason:error.name==='AssertionError'?error.message.slice(0,200):undefined,
    hashes:{html_sha256:sha(htmlPath),browser_fixture_sha256:sha(new URL(import.meta.url))}},null,2),{flag:'wx'});
  console.error('P236_BROWSER_FAIL',current,error.name);process.exitCode=1;
} finally {if(browser)await browser.close();}
