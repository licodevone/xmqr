// SPDX-License-Identifier: MIT
// P238: checks the actual file URL; no HTTP server or external assets.
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const {chromium}=createRequire(import.meta.url)('playwright');
const [html,output]=process.argv.slice(2);
if(!html||!output||fs.existsSync(output)) throw Error('Use HTML e pasta de evidência nova.');
fs.mkdirSync(output,{recursive:true});
const rows=[],errors=[],remote=[];
const browser=await chromium.launch({headless:true});
let current='inicialização';
try {
 const context=await browser.newContext({viewport:{width:1440,height:1000},colorScheme:'light',reducedMotion:'reduce'});
 const page=await context.newPage();
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url());});
 await page.goto(pathToFileURL(path.resolve(html)).href);await page.waitForLoadState('networkidle');
 const input=page.locator('#search'),button=page.locator('#guide-theme-toggle');
 const visible=()=>page.locator('main .filter:not([hidden])').count();
 const all=await visible();
 async function search(q) {await input.fill(q);return visible();}
 current='ícone lua sem texto, nome acessível e alvo44px';
 assert.equal((await button.textContent()).trim(),'');
 assert.equal(await button.getAttribute('aria-label'),'Ativar modo escuro');
 assert(await button.locator('.theme-moon').isVisible());
 assert.equal(await button.locator('.theme-sun').isVisible(),false);
 assert((await button.boundingBox()).width>=44);rows.push(current);

 current='teclado ativa escuro com sol e volta ao claro; preferência persiste';
 await button.focus();await page.keyboard.press('Enter');
 await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
 assert(await button.locator('.theme-sun').isVisible());
 assert.equal(await button.getAttribute('aria-label'),'Ativar modo claro');
 await page.screenshot({path:path.join(output,'dark.png')});
 await page.reload();await page.waitForLoadState('networkidle');
 assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
 await button.focus();await page.keyboard.press('Space');
 await page.waitForFunction(()=>document.documentElement.dataset.theme==='light');rows.push(current);

 current='termo inexistente oculta cartões e seções e mostra estado vazio';
 assert.equal(await search('termo-inexistente-p238'),0);
 assert.match(await page.locator('#guide-search-status').textContent(),/Nenhum resultado/);
 assert.equal(await page.locator('main section:not([hidden]) .filter:not([hidden])').count(),0);
 rows.push(current);

 current='nome de arquivo filtra de verdade e mantém resultados visíveis';
 const files=await search('configuration.rs');assert(files>0&&files<all);
 assert(await page.locator('main .filter:not([hidden])').first().isVisible());
 assert.match(await page.locator('#guide-search-status').textContent(),new RegExp('^'+files+' resultado'));
 rows.push(current);

 current='busca ignora caixa/acentos e combina termos';
 const plain=await search('configuracao');assert(plain>0&&plain<all);
 assert.equal(await search('CONFIGURAÇÃO'),plain);
 const combined=await search('configuration.rs TLS');assert(combined>0&&combined<=files);
 rows.push(current);

 current='prompts e texto incorporado respondem por seu conteúdo';
 const argon=await search('Argon2id');assert(argon>0&&argon<all);
 assert.equal(await search('ARGON2ID'),argon);rows.push(current);

 current='fontes fechadas são reveladas e limpar restaura aberturas anteriores';
 await page.locator('#guide-search-clear').click();
 await page.evaluate(()=>document.querySelectorAll('main details').forEach(n=>n.open=false));
 const openedBefore=await page.locator('main details').evaluateAll(nodes=>nodes.map(n=>n.open));
 assert(await search('load_with')>0);
 assert(await page.locator('main .filter:not([hidden]) .source:visible').count()>0);
 await page.locator('#guide-search-clear').click();
 assert.equal(await visible(),all);
 assert.deepEqual(await page.locator('main details').evaluateAll(nodes=>nodes.map(n=>n.open)),openedBefore);
 assert.equal(await page.locator('#guide-search-clear').isDisabled(),true);rows.push(current);

 current='consulta HTML é somente texto e Escape limpa sem requisição';
 await search('<img src=x onerror="window.p238Injected=1">');
 assert.equal(await page.evaluate(()=>window.p238Injected),undefined);
 assert((await page.locator('#guide-search-status').textContent()).includes('<img'));
 assert.equal(await page.locator('#guide-search-status img').count(),0);
 await input.press('Escape');assert.equal(await input.inputValue(),'');assert.equal(await visible(),all);rows.push(current);

 current='mobile preserva busca e controle com ícone sem overflow';
 await page.setViewportSize({width:390,height:844});
 await search('Argon2id');await input.scrollIntoViewIfNeeded();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:path.join(output,'mobile-search.png')});
 await page.locator('#guide-search-clear').click();rows.push(current);

 current='personalizações e checklists do aluno preservados';
 assert.equal(await page.locator('#collapse').count(),0);
 assert.equal(await page.locator('#admin-web-checklist input:checked').count(),0);
 assert.equal(await page.locator('#admin-web-checklist input[type=checkbox]').count(),34);
 await page.setViewportSize({width:1440,height:1000});await input.scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(output,'light-search.png')});rows.push(current);
 assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
 fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify({status:'PASS',mode:'file://',steps:rows,errors,remote,
   html_sha256:createHash('sha256').update(fs.readFileSync(html)).digest('hex')},null,2),{flag:'wx'});
 console.log(JSON.stringify({status:'PASS',checks:rows.length}));
} catch(e) {
 fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify({status:'FAIL',current,steps:rows,error:String(e),errors,remote},null,2),{flag:'wx'});
 throw e;
} finally {await browser.close();}
