// P79: navegação do guia e verificação das versões de apresentação.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const runtime=process.env.XMQR_RUNTIME_ROOT||'C:/Users/licod/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const {chromium}=await import(pathToFileURL(path.join(runtime,'node/node_modules/playwright/index.mjs')).href);
const output=path.resolve(repo,'../docs/curso-udemy/primeiro-commit');
const qa=path.join(repo,'target/p79-apresentacao');
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[];
page.on('pageerror',e=>errors.push(e.message));
const expect=(value,message)=>{if(!value)throw new Error(message);};
try{
  await page.goto(pathToFileURL(path.join(output,'index.html')).href);
  expect((await page.title())==='Da lógica ao Broker e Clientes MQTT utilizando Rust','Título incorreto');
  const nav=page.locator('nav details[data-target="aula-inicial"]');
  const main=page.locator('main #aula-inicial');
  await nav.locator('summary').first().click();
  await page.waitForFunction(()=>document.getElementById('aula-inicial').open);
  await nav.locator('summary').first().click();
  await page.waitForFunction(()=>!document.getElementById('aula-inicial').open);
  await main.locator('summary').first().click();
  await page.waitForFunction(()=>document.querySelector('nav [data-target="aula-inicial"]').open);
  await page.screenshot({path:path.join(qa,'guia-desktop.png'),fullPage:false});
  await page.locator('main [data-toggle-all]').click();
  await page.waitForFunction(()=>[...document.querySelectorAll('main details[id],nav details[data-target]')].every(n=>n.open));
  expect((await page.locator('nav [data-toggle-all]').textContent())==='Fechar todos os tópicos','Botão não atualizou');
  await page.locator('nav [data-toggle-all]').click();
  await page.waitForFunction(()=>[...document.querySelectorAll('main details[id],nav details[data-target]')].every(n=>!n.open));
  await page.locator('main a[href="#aula-inicial"]').click();
  expect(await main.evaluate(n=>n.open),'Âncora não abriu tópico');
  await page.locator('#search').fill('src/main.rs:52');
  expect(await page.locator('tr.highlight').count()>0,'Busca por linha não destacou fonte');
  await page.locator('#search').fill('');
  await page.setViewportSize({width:390,height:844});
  await page.goto(pathToFileURL(path.join(output,'index.html')).href);
  await page.evaluate(()=>{window.scrollTo(0,0);document.querySelector('nav').scrollTop=0;});
  await page.screenshot({path:path.join(qa,'guia-mobile.png')});
  expect(await page.locator('nav [data-toggle-all]').isVisible(),'Controle mobile não visível');
  const mobileButton=await page.locator('nav [data-toggle-all]').boundingBox();
  expect(mobileButton.y>=0&&mobileButton.y+mobileButton.height<=844,'Controle mobile fora da tela');
  expect(await page.locator('.compiler-flow').count()===3,'Diagramas HTML ausentes');
  expect(errors.length===0,'Erros JavaScript: '+errors.join(', '));
  const report={titulo:true,sidebar_corpo_sincronizados:true,abrir_fechar_global:true,ancora:true,busca_linha:true,mobile:true,diagramas:3,erros_js:errors};
  await fs.writeFile(path.join(qa,'browser-qa.json'),JSON.stringify(report,null,2));
  console.log('PASS navegador: título, abrir/fechar individual/global, âncora, busca e mobile.');
}finally{await browser.close();}

// Reimporte a entrega para renderizar todos os slides do arquivo final.
const {PresentationFile,FileBlob}=await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const deck=await PresentationFile.importPptx(await FileBlob.load(path.join(output,'apresentacao/curso-alunos.pptx')));
for(const [i,slide] of deck.slides.items.entries()){
  const png=await deck.export({slide,format:'png',scale:1});
  await fs.writeFile(path.join(qa,`final-slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log('PASS renderização da entrega: '+deck.slides.items.length+' slides.');
