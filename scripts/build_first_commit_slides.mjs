// P79: apresentação editável, diagramas nativos e notas separadas da projeção.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const runtime = process.env.XMQR_RUNTIME_ROOT || 'C:/Users/licod/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const skill = process.env.XMQR_PRESENTATION_SKILL || 'C:/Users/licod/.codex/plugins/cache/openai-primary-runtime/presentations/26.1011.11113/skills/presentations';
process.env.RUNTIME_NODE_MODULES = path.join(runtime,'node/node_modules');
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(runtime, 'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const { finalizePresentation } = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);
const build = path.join(repo, 'target/p79-apresentacao');
const validatedDir = path.join(repo, 'target/p79-entrega');
const deliver = path.resolve(repo, '../docs/curso-udemy/primeiro-commit/apresentacao');
const trackedDeliver = path.join(repo,'curso/reconstrucao-primeiro-commit/apresentacao');
const specs = JSON.parse(await fs.readFile(path.join(repo, 'curso/reconstrucao-primeiro-commit/slides.json'), 'utf8'));
await fs.mkdir(build, { recursive: true });
await fs.mkdir(validatedDir, { recursive: true });
await fs.mkdir(deliver, { recursive: true });
await fs.mkdir(trackedDeliver,{recursive:true});
const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
presentation.theme.defaultFont = 'Arial';
const colors = { ink: '#102B43', rust: '#B84F29', blue: '#226A9D', paper: '#F5F7FA', gray: '#476078', line: '#CCD7E2' };
let serial = 0;
function shape(slide, geometry, x, y, w, h, fill, line = 'none') {
  return slide.shapes.add({ name: 'p79-' + (++serial), geometry, position: { left:x, top:y, width:w, height:h }, fill, line: { fill:line, width:line==='none'?0:1, style:'solid' } });
}
function text(slide, value, x, y, w, h, size=28, color=colors.ink, bold=false, font='Arial') {
  const s = shape(slide,'textbox',x,y,w,h,'none');
  s.text = value;
  s.text.style = { typeface:font, fontSize:size, color, bold };
  s.text.insets = 0;
  return s;
}
function line(slide, a, b, vertical=false) {
  slide.shapes.connect(a,b,{kind:'straight',fromSide:vertical?'bottom':'right',toSide:vertical?'top':'left',line:{fill:colors.gray,width:2},tail:{type:'triangle',width:'med',length:'med'}});
}
function flow(slide, item) {
  const labels = item.nodes;
  // Alvos são alternativas. Estado reúne componentes. Não desenhar sequência falsa.
  if (item.title==='O alvo define o código gerado' || item.title==='Sessões e mensagens mantêm estado') {
    const center = item.title.startsWith('O alvo') ? labels[0] : 'Estado MQTT';
    const others = item.title.startsWith('O alvo') ? labels.slice(1) : labels;
    const root=shape(slide,'roundRect',440,205,400,90,colors.ink);
    text(slide,center,460,229,360,60,26,'#FFFFFF',true);
    const width=(1136-(others.length-1)*22)/others.length;
    others.forEach((label,i)=>{const x=72+i*(width+22);const box=shape(slide,'roundRect',x,370,width,140,'#E4EDF5');text(slide,label,x+14,398,width-28,98,24,colors.ink,true);line(slide,root,box,true);});
  } else {
    const gap=24, width=(1136-(labels.length-1)*gap)/labels.length;
    const boxes=labels.map((label,i)=>{
      const x=72+i*(width+gap);
      const box=shape(slide,'roundRect',x,280,width,165,i%2?'#E1ECF4':'#F5E5DB');
      text(slide,String(i+1).padStart(2,'0'),x+14,300,width-28,28,18,colors.rust,true);
      const short = label==='Pré-processador'?'Macros e\ninclusões':label==='MIR\nEmpréstimos'?'MIR\nBorrow\nchecker':label;
      text(slide,short,x+14,344,width-28,94,labels.length>5?23:26,colors.ink,true);
      return box;
    });
    boxes.slice(1).forEach((b,i)=>line(slide,boxes[i],b));
  }
  text(slide,item.caption||'',72,550,1136,72,25,colors.gray);
}

for (const [i,item] of specs.entries()) {
  const slide=presentation.slides.add();
  const cover=item.kind==='cover', section=item.kind==='section';
  slide.background.fill=cover||section?colors.ink:colors.paper;
  const fg=cover||section?'#FFFFFF':colors.ink;
  shape(slide,'rect',0,0,1280,9,colors.rust);
  text(slide,item.section,72,35,1136,42,19,cover||section?'#C6DDEE':colors.blue,true);
  text(slide,item.lesson,72,83,1136,45,21,cover||section?'#C6DDEE':colors.gray);
  text(slide,item.title,72,146,1136,cover?165:95,cover?46:38,fg,true);
  if (item.kind==='flow') flow(slide,item);
  else if(item.kind==='compare') {
    [[item.leftTitle,item.left,72,colors.rust],[item.rightTitle,item.right,660,colors.blue]].forEach(([title,rows,x,color])=>{
      text(slide,title,x,264,548,45,29,color,true);
      rows.forEach((row,k)=>text(slide,row,x,325+k*59,536,55,25));
    });
    shape(slide,'rect',622,265,2,345,colors.line);
  } else if(item.kind==='code') {
    shape(slide,'rect',72,264,650,340,colors.ink);
    text(slide,item.code,94,291,604,294,23,'#E9F2F8',false,'Consolas');
    item.body.forEach((row,k)=>text(slide,row,758,270+k*83,450,76,25));
  } else {
    const y=cover?363:280;
    item.body.forEach((row,k)=>{
      text(slide,String(k+1).padStart(2,'0'),72,y+k*61,40,42,21,cover||section?'#EFB492':colors.rust,true);
      text(slide,row,134,y+k*61,1050,55,28,fg);
    });
  }
  shape(slide,'rect',72,655,1136,1,cover||section?'#476078':colors.line);
  text(slide,'XMQR 0.3.0 · reconstrução do primeiro commit',72,675,1000,25,15,cover||section?'#C6DDEE':colors.gray);
  text(slide,String(i+1).padStart(2,'0'),1150,673,58,26,18,cover||section?'#FFFFFF':colors.ink,true);
  if(!item.say||!item.private)throw new Error('Slide sem notas completas: '+(i+1));
  slide.speakerNotes.text='FALA SUGERIDA AOS ALUNOS\n'+item.say+'\n\nORIENTAÇÕES PRIVADAS AO APRESENTADOR\n'+item.private+'\n\nFONTES\n'+(item.sources||['Guia P77, ROTEIRO.md e BIBLIOTECAS.md, snapshot f7efe357']).join('\n');
  const png=await presentation.export({slide,format:'png',scale:1});
  await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
  console.log('Slide '+(i+1)+' renderizado');
}

async function finalize(name) {
  const candidate=path.join(build,name+'-draft.pptx');
  const final=path.join(validatedDir,name+'-validado.pptx');
  // O finalizador preserva arquivos anteriores. Cada execução usa nome privado único.
  const unique=final.replace('.pptx','-'+Date.now()+'.pptx');
  await (await PresentationFile.exportPptx(presentation)).save(candidate);
  await finalizePresentation({workspaceDir:repo,candidatePath:candidate,finalPath:unique,pythonExecutable:path.join(runtime,'python/python.exe'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:specs.length,fontPolicy:{basis:'design',families:['Arial','Consolas']},verifyArtifactToolImport:true,receiptPath:path.join(build,name+'.validation.json')});
  await fs.copyFile(unique,path.join(deliver,name+'.pptx'));
  await fs.copyFile(unique,path.join(trackedDeliver,name+'.pptx'));
}
await finalize('curso-professor');
presentation.slides.items.forEach(slide=>slide.speakerNotes.clear());
await finalize('curso-alunos');
const escape=value=>value.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const notes=specs.map((s,i)=>`<article><h2>Slide ${i+1} — ${escape(s.title)}</h2><p class="meta">${escape(s.section)}<br>${escape(s.lesson)}</p><h3>Fala sugerida aos alunos</h3><p>${escape(s.say)}</p><h3>Orientações privadas ao apresentador</h3><p>${escape(s.private)}</p><h3>Fontes</h3><ul>${(s.sources||['Guia P77 e primeiro commit f7efe357']).map(x=>`<li>${x.startsWith('https://')?`<a href="${escape(x)}">${escape(x)}</a>`:escape(x)}</li>`).join('')}</ul></article>`).join('');
await fs.writeFile(path.join(deliver,'roteiro-professor.html'),'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Roteiro privado do apresentador</title><style>body{font:18px/1.7 system-ui;max-width:980px;margin:40px auto;padding:20px;color:#102b43;background:#f5f7fa}article{background:white;padding:24px;margin:22px 0;border-left:5px solid #b84f29}h2{line-height:1.3}.meta{color:#476078}a{overflow-wrap:anywhere;color:#226a9d}@media print{article{break-inside:avoid}}</style><h1>Da lógica ao Broker e Clientes MQTT utilizando Rust</h1><p>Roteiro privado. Cada slide tem fala sugerida e orientações de apresentação. Estes textos não aparecem na projeção. Compartilhe curso-alunos.pptx com os alunos.</p>'+notes+'</html>','utf8');
await fs.copyFile(path.join(deliver,'roteiro-professor.html'),path.join(trackedDeliver,'roteiro-professor.html'));
await fs.writeFile(path.join(build,'resumo.json'),JSON.stringify({slides:specs.length,professor:'curso-professor.pptx',alunos:'curso-alunos.pptx',renderizados:specs.length,notas_privadas_nos_slides:false},null,2));
console.log('Apresentações exportadas: '+specs.length+' slides, duas versões.');
