import {mountRefinement} from './refinement-panel.mjs';
import './evidence-import.mjs';
import {passEvidence,wilsonInterval,reconstructionPoints,suggestedOutcome} from './graph-evidence.mjs';
import {resultPasses} from './passes.mjs';
const $=id=>document.getElementById(id);
let result=null,passes=[],pass=null,record=null,evidence=null,index=0,drawIndex=0,view='reply',revision=0;
const refinementHost=$('refinement-host');
const refinement=mountRefinement(refinementHost,()=>({result,pass,record,evidence}));
const draftEdits=new Map();
const media=matchMedia('(prefers-reduced-motion: reduce)');let staticMotion=true;
function node(tag,value,className){const e=document.createElement(tag);e.textContent=value;if(className)e.className=className;return e;}
function svg(tag,attrs={},value){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));if(value!==undefined)e.textContent=value;return e;}
async function api(path){const response=await window.workerFetch('/api/live/'+path);const data=await response.json();if(!response.ok)throw new Error(data.error||'Could not open saved evidence.');return data;}
function showError(e){$('loading').hidden=true;$('evidence').hidden=true;$('error').hidden=false;$('error-message').textContent=e.message||String(e);}
function key(){return `${result.id}/${pass.id}/${evidence.observed[index].t}`;}
function tokens(){return result.base?.tokens??record.base?.token_texts??[];}
function draws(){const t=evidence.observed[index].t;return (record.branches??[]).filter(b=>b.t===t).flatMap(b=>(b.observations??[]).map((o,i)=>({...o,branch_token:b.tok_id,draw_index:b.draw_indices?.[i]??i}))).sort((a,b)=>a.draw_index-b.draw_index);}
const isFinished=o=>Boolean(o.stop_reason)&&o.stop_reason!=='length';
function filteredDraws(){const outcome=$('filter-outcome').value,completion=$('filter-completion').value;return draws().filter(o=>(!outcome||o.label===outcome)&&(!completion||(completion==='finished'?isFinished(o):completion==='length'?o.stop_reason==='length':!o.stop_reason)));}
function refreshDrawList(){const list=filteredDraws();$('draw').replaceChildren(...list.map((o,i)=>new Option(`Draw ${o.draw_index+1} · ${o.label}`,String(i))));if(!list.length)$('draw').add(new Option('No matching draws',''));$('draw').disabled=!list.length;renderDraw();}
function openRefinement(left,right){$('refinement-disclosure').open=true;if(left!==undefined)refinement.select(left,right);$('refinement-disclosure').scrollIntoView({block:'nearest'});}
function summarizeRun(){
  const all=(record.branches??[]).flatMap(b=>b.observations??[]),caps=all.filter(o=>o.stop_reason==='length').length,finished=all.filter(isFinished).length;
  const data=[['Checkpoints',evidence.observed.length,'Original token positions'],['Recorded draws',all.length,'Fresh continuations'],['Finished',finished,`${all.length?Math.round(100*finished/all.length):0}% of recorded draws`],['Reached token cap',caps,'Inspect separately from decisions']];
  $('run-facts').replaceChildren(...data.map(([label,value,note])=>{const el=node('div','','summary-card');el.append(node('span',label),node('strong',String(value)),node('small',note));return el;}));
  $('outcome-totals').replaceChildren(...result.categories.map((label,k)=>{const n=all.filter(o=>o.label===label).length,el=node('button','','outcome-chip');el.style.setProperty('--category-color',['#a5d7ef','#c6b7f0','#e1bd85','#9edac1','#ecabbc'][k%5]);el.append(node('span',label),node('strong',String(n)));el.title='Show '+label+' on the outcome map';el.setAttribute('aria-pressed',String($('outcome').value===label));el.onclick=()=>{$('outcome').value=label;drawChart();updateFacts();updateOutcomeSelection();};return el;}));
}
function updateOutcomeSelection(){[...$('outcome-totals').children].forEach((b,i)=>b.setAttribute('aria-pressed',String(result.categories[i]===$('outcome').value)));}
async function load(id){
  const current=++revision;$('evidence').hidden=true;$('error').hidden=true;$('loading').hidden=false;$('download').hidden=true;
  const loaded=await api('export?id='+encodeURIComponent(id));if(current!==revision)return;
  if(!loaded.base||!Array.isArray(loaded.categories)||!loaded.records)throw new Error('This file does not contain the saved trace and observation records.');
  result=loaded;window.setForkMethodCredit?.(result);passes=resultPasses(result);if(!passes.length)throw new Error('No completed checkpoint passes in this run.');
  $('import-provenance').hidden=!result.records['import-info'];$('import-provenance').textContent=result.records['import-info']?'Imported evidence · saved fit not recomputed locally.':'';
  $('runs').value=id;$('model-name').textContent=result.model.model_id;
  const prompt=result.base.question?.question??result.base_config?.prompt??'Prompt not recorded';$('prompt-text').textContent=prompt;$('prompt-preview').textContent=prompt;
  $('technical').href='/live.html?run='+encodeURIComponent(id);$('download').href='#';$('download').onclick=async event=>{event.preventDefault();try{const data=await api('export?id='+encodeURIComponent(id));const url=URL.createObjectURL(new Blob([JSON.stringify(data)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='fork-run-'+id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){showError(e);}};$('download').download='fork-run-'+id+'.json';$('download').hidden=false;
  $('new-run').href='/live.html?run='+encodeURIComponent(id)+'&view=setup';
  $('outcome').replaceChildren(...result.categories.map(c=>new Option(c,c)));$('outcome').selectedIndex=suggestedOutcome(passes,result.categories.length);
  $('filter-outcome').replaceChildren(new Option('All outcomes',''),...result.categories.map(c=>new Option(c,c)));$('filter-completion').value='';
  $('pass').replaceChildren(...passes.map(p=>new Option(p.label??p.id,p.id)));
  $('provenance').textContent=`Saved run ${result.id} · revision ${(result.model.resolved_revision??result.model.requested_revision??'unrecorded').slice(0,12)}`;
  const parentId=result.lineage?.source_run_id??result.records['replay-verification']?.source_run_id;
  if(parentId){const a=node('a','View parent run →');a.href='/observatory.html?run='+encodeURIComponent(parentId);$('provenance').prepend(a,node('span',' · '));}
  history.replaceState(null,'','?run='+encodeURIComponent(id));choosePass(passes[0].id);$('loading').hidden=true;$('evidence').hidden=false;
}
function choosePass(id){
  pass=passes.find(p=>p.id===id);record=result.records[pass.id];if(!record)throw new Error('This pass has no saved observation record.');
  evidence=passEvidence(pass,record,result.categories.length);if(!evidence.observed.length)throw new Error('No valid measured checkpoints available.');
  index=0;drawIndex=0;
  const m=result.measured?.[pass.id];$('run-summary').textContent=`${evidence.observed.length} measured checkpoints · ${m?.continuations??'Unknown number of'} continuations${m?.wall_seconds!==undefined?' · '+(m.wall_seconds/60).toFixed(1)+' minutes of collection':''}`;
  $('fit-status').textContent=pass.curve?.fit_status==='withheld'?'Fit withheld':pass.curve?.tuning==='cv'?'Cross-validated fit':pass.curve?.parameters?'Fixed-parameter fit':'No saved fit';
  $('warnings').textContent=(pass.curve?.warnings??[]).join(' ');
  const masses=(record.positions??[]).map(p=>p.retained_mass).filter(Number.isFinite);
  $('distribution-scope').textContent=masses.length?`Sampling covered ${(Math.min(...masses)*100).toFixed(1)}–${(Math.max(...masses)*100).toFixed(1)}% of next-token probability across these checkpoints. The plotted distribution is conditional on those retained branches; omitted branches were not sampled.`:'Retained branch coverage was not recorded for this pass. The full next-token distribution has not been verified.';
  $('checkpoint-pages').replaceChildren(...evidence.observed.map((p,i)=>{const b=node('button',String(p.t));b.dataset.index=i;b.setAttribute('aria-label',`Checkpoint at token ${p.t}`);b.onclick=()=>showCheckpoint(i);return b;}));
  const bounds=evidence.segmentationEnabled?(pass.curve?.boundaries??[]):[];$('candidate-links').replaceChildren(...bounds.map(b=>{const el=node('button',`${b.left}–${b.right}`,'candidate-chip');el.title='Configure denser sampling in this interval';el.onclick=()=>openRefinement(b.left,b.right);return el;}));if(!bounds.length)$('candidate-links').append(node('span','No fitted boundaries in this pass.','micro'));
  summarizeRun();drawChart();showCheckpoint(0);refinement.refresh();
}
function drawChart(){
  const points=evidence.observed,k=result.categories.indexOf($('outcome').value),start=points[0].t,end=points.at(-1).t;
  const x=t=>60+(t-start)/Math.max(1,end-start)*950,y=v=>174-v*150;
  for(const id of ['chart-grid','change-regions','error-bars','observations','axes'])$(id).replaceChildren();
  for(const v of [0,.5,1]){$('chart-grid').append(svg('path',{d:`M60 ${y(v)} H1010`,class:'gridline'}));$('axes').append(svg('text',{x:5,y:y(v)+4,class:'axis-text'},`${v*100}%`));}
  for(const t of [start,end])$('axes').append(svg('text',{x:x(t),y:204,class:'axis-text','text-anchor':t===start?'start':'end'},String(t)));
  $('axes').append(svg('text',{x:535,y:204,class:'axis-text','text-anchor':'middle'},'Original response token position'));
  for(const b of pass.curve?.boundaries??[])if(evidence.segmentationEnabled&&b.left>=start&&b.right<=end&&b.left<b.right){const region=svg('rect',{x:x(b.left),y:20,width:x(b.right)-x(b.left),height:160,class:'candidate'});region.style.cursor='pointer';region.onclick=()=>openRefinement(b.left,b.right);region.append(svg('title',{},`Configure refinement at ${b.left}–${b.right}`));$('change-regions').append(region);}
  const fitted=reconstructionPoints(pass.curve,k);let d='',penDown=false;
  for(const p of fitted){if(p.value===null){penDown=false;continue;}d+=`${penDown?'L':'M'}${x(p.t)} ${y(p.value)} `;penDown=true;}
  $('fitted').setAttribute('d',d);$('fitted').style.display=$('smooth').checked?'':'none';
  points.forEach((p,i)=>{
    if($('intervals').checked&&p.counts){const band=wilsonInterval(p.counts[k],p.samples);if(band)$('error-bars').append(svg('path',{d:`M${x(p.t)} ${y(band[0])}V${y(band[1])} M${x(p.t)-3} ${y(band[0])}h6 M${x(p.t)-3} ${y(band[1])}h6`,class:'point-bar'}));}
    const label=`Token ${p.t}: ${(p.values[k]*100).toFixed(1)}% ${result.categories[k]}${p.counts?' ('+p.counts[k]+'/'+p.samples+')':''}`;
    const circle=svg('circle',{cx:x(p.t),cy:y(p.values[k]),r:5,class:'graph-dot'+(i===index?' active':''),'data-index':i,role:'button',tabindex:0,'aria-label':label});circle.append(svg('title',{},label));circle.onclick=()=>showCheckpoint(i);circle.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();showCheckpoint(i);}};$('observations').append(circle);
  });
  const same=evidence.constant?'No sampled outcome differences.':`${evidence.intervals.length} adjacent intervals with observed differences or fitted boundaries.`;
  const changes=(pass.curve?.boundaries??[]).length;
  $('graph-summary').textContent=evidence.constant?'All sampled checkpoints have the same outcome proportions.':`${evidence.segmentationEnabled?`${changes} candidate change ${changes===1?'interval':'intervals'} in the saved fit.`:'No fitted change intervals available.'} A highlighted interval suggests where to inspect; it does not establish a statistically significant or causal fork.`;
  $('chart-title').textContent=`${$('outcome').value} outcome proportions at ${points.length} measured checkpoints. ${same}`;
}
function showCheckpoint(next){
  index=Math.max(0,Math.min(evidence.observed.length-1,next));drawIndex=0;
  const p=evidence.observed[index],source=tokens(),end=Math.min(p.t+32,source.length);
  $('position').textContent=p.t;$('page-number').textContent=`${String(index+1).padStart(2,'0')} / ${String(evidence.observed.length).padStart(2,'0')}`;
  $('previous').disabled=index===0;$('next').disabled=index===evidence.observed.length-1;
  $('context-line').textContent=p.t?source.slice(Math.max(0,p.t-32),p.t).join(''):'Beginning of the generated response. The prompt is the only earlier context.';
  $('anchor-text').textContent=source.slice(p.t,end).join('');
  $('prefix-history').textContent=source.slice(0,p.t).join('')||'No original response tokens precede this checkpoint.';
  $('span-label').textContent=`Original tokens ${p.t}–${end-1} · ${source.length} tokens in the full trace`;
  for(const b of $('checkpoint-pages').children)b.setAttribute('aria-pressed',String(Number(b.dataset.index)===index));
  for(const c of $('observations').children)c.classList.toggle('active',Number(c.dataset.index)===index);
  $('replacement').value=draftEdits.get(key())??source.slice(p.t,end).join('');
  $('draft-boundary').textContent=`Source token span [${p.t}, ${end}). Preserve ${p.t} response tokens before it. The replacement has not been tokenized.`;
  $('draft-status').textContent='Draft only. Tokenization, a connected worker, and fresh control/edit continuations are required before execution.';
  updateFacts();refreshDrawList();
}
function updateFacts(){
  const p=evidence.observed[index],k=result.categories.indexOf($('outcome').value),meta=record.positions?.find(r=>r.t===p.t),list=draws();
  $('match-stat').textContent=p.counts?`${p.counts[k]} / ${p.samples} ${$('outcome').value}`:`${(p.values[k]*100).toFixed(1)}% ${$('outcome').value}`;
  $('mass-stat').textContent=Number.isFinite(meta?.retained_mass)?`${(meta.retained_mass*100).toFixed(2)}%`:'Not recorded';
  $('completion-stat').textContent=list.length?`${list.filter(isFinished).length} / ${list.length}`:'Not recorded';
}
function renderDraw(){
  const all=draws(),list=filteredDraws();drawIndex=Math.max(0,Math.min(Math.max(0,list.length-1),drawIndex));const o=list[drawIndex];
  $('draw').value=String(drawIndex);$('draw-prev').disabled=!list.length||drawIndex===0;$('draw-next').disabled=!list.length||drawIndex>=list.length-1;
  $('recorded-view').hidden=view==='edit';$('draft-view').hidden=view!=='edit';
  for(const b of document.querySelectorAll('[data-view]'))b.setAttribute('aria-pressed',String(b.dataset.view===view));
  $('draw-meta').textContent=o?`${o.label} · ${o.generated_tokens} new tokens · ${o.stop_reason==='length'?'Token cap reached':isFinished(o)?'Finished':'Completion not recorded'} · branch ${o.branch_token}`:all.length?'No draws match these filters at this checkpoint.':'This historical record contains no saved continuation text.';
  $('draw-meta').classList.toggle('capped',o?.stop_reason==='length');
  $('view-note').textContent=view==='reply'?'Reply text extracted by the saved readout rule.':view==='continuation'?'Newly generated text after the forced branch token.':'Full saved response: earlier source prefix, forced branch token, and generated continuation.';
  const text=o?.[view==='reply'?'reply_text':view==='continuation'?'continuation_text':'full_response_text'];
  $('reply').textContent=text??(list.length?'No text recorded for this view.':'Choose another checkpoint or clear the filters to see recorded text.');$('reply').scrollTop=0;
  $('filter-summary').textContent=`${list.length} of ${all.length} draws at token ${evidence.observed[index].t}`;$('reset-filters').hidden=!$('filter-outcome').value&&!$('filter-completion').value;$('copy-reply').disabled=view==='edit'||!text;$('reader-status').textContent='';
}
function exportDraft(){
  const p=evidence.observed[index],end=Math.min(p.t+32,tokens().length),replacement=$('replacement').value;
  if(!replacement.trim()){$('draft-status').textContent='Enter replacement text. Deletion needs a separate explicit action.';return;}
  const base=record.base,draft={schema:'fork-observatory-edit-draft-v1',status:'pending-unexecuted',synthetic:false,source:{run_id:result.id,pass_id:pass.id,checkpoint:p.t,model:result.model,span_start:p.t,span_end:end},prompt_ids:base.prompt_ids,preserved_response_ids:base.gen_ids.slice(0,p.t),original_span_ids:base.gen_ids.slice(p.t,end),replacement_text:replacement,replacement_ids:null,discard_original_suffix:true,token_boundary_validation:'source span uses saved IDs; replacement requires tokenizer preview',sampler_contract:null,results:null};
  const blob=new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`edit-${result.id}-token-${p.t}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('draft-status').textContent='Edit draft downloaded. No continuation was generated and the original evidence is unchanged.';
}
function motion(){const off=staticMotion||media.matches;document.body.classList.toggle('motion-static',off);$('motion').textContent=off?'Atmosphere off':'Atmosphere on';$('motion').setAttribute('aria-pressed',String(!off));$('motion').disabled=media.matches;}
$('motion').onclick=()=>{staticMotion=!staticMotion;motion();};media.addEventListener('change',motion);
for(const e of ['focusin','focusout','selectionchange','visibilitychange','pointerover','pointerout'])document.addEventListener(e,()=>{document.body.classList.toggle('motion-paused',Boolean(document.hidden||document.activeElement?.closest('.editor,.reasoning-column')||document.querySelector('.editor:hover,.reasoning-column:hover')||getSelection()?.toString()));});
$('runs').onchange=()=>load($('runs').value).catch(showError);$('pass').onchange=()=>{try{choosePass($('pass').value);}catch(e){showError(e);}};
$('outcome').onchange=()=>{drawChart();updateFacts();updateOutcomeSelection();};$('smooth').onchange=drawChart;$('intervals').onchange=drawChart;
$('previous').onclick=()=>showCheckpoint(index-1);$('next').onclick=()=>showCheckpoint(index+1);
$('checkpoint-pages').onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();showCheckpoint(e.key==='Home'?0:e.key==='End'?evidence.observed.length-1:index+(e.key==='ArrowRight'?1:-1));$('checkpoint-pages').children[index].focus();}};
$('history-toggle').onclick=()=>{const open=$('prefix-history').hidden;$('prefix-history').hidden=!open;$('history-toggle').setAttribute('aria-expanded',String(open));$('history-toggle').textContent=open?'Hide earlier text ↑':'Read earlier text ↑';};
$('draw').onchange=()=>{drawIndex=Number($('draw').value);renderDraw();};$('draw-prev').onclick=()=>{drawIndex--;renderDraw();};$('draw-next').onclick=()=>{drawIndex++;renderDraw();};
for(const id of ['filter-outcome','filter-completion'])$(id).onchange=()=>{drawIndex=0;refreshDrawList();};
$('reset-filters').onclick=()=>{$('filter-outcome').value='';$('filter-completion').value='';drawIndex=0;refreshDrawList();};
$('open-refinement').onclick=()=>openRefinement();
$('copy-reply').onclick=async()=>{try{await navigator.clipboard.writeText($('reply').textContent);$('reader-status').textContent='Displayed text copied.';}catch{$('reader-status').textContent='Copy is unavailable in this browser. Select the text to copy it.';}};
$('back-to-records').onclick=()=>{view='reply';renderDraw();};
$('retry').onclick=()=>location.reload();
for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>{view=b.dataset.view;renderDraw();};
$('edit-here').onclick=()=>{view='edit';renderDraw();$('replacement').focus();};$('replacement').oninput=()=>{draftEdits.set(key(),$('replacement').value);$('draft-status').textContent='Local draft changed. Download it to preserve this version; no inference is running.';};$('save-draft').onclick=exportDraft;
motion();
try{const runs=await api('runs');$('runs').replaceChildren(...runs.map(r=>new Option(`${new Date(r.created*1000).toLocaleDateString()} · ${r.model.split('/').at(-1)} · ${(r.prompt??'').slice(0,55)} · ${r.id.slice(0,6)}`,r.id)));if(!runs.length)throw new Error('No completed runs are saved on this device yet. Import an evidence file or connect a model to collect your first run.');const requested=new URLSearchParams(location.search).get('run');await load(requested||runs[0].id);}catch(e){showError(e);$('model-name').textContent='Saved evidence unavailable';}

addEventListener('worker-connection-change', () => location.reload());
