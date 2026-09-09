import {gpuEstimate} from './math.mjs';
import {newPass,resultPasses} from './passes.mjs';
const $=id=>document.getElementById(id),num=id=>$(id).value.trim()===''?NaN:Number($(id).value);
let resultRevision=0,baseFormDirty=false;
let state=null,result=null,budget=null,estimateTimer,estimateRevision=0,lastBaseSignature='',lastResultId='';
let passes=[newPass()],activePass=passes[0].id;
const fmt=n=>new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(n);
const fields=['cont-cap','temperature','top-k','threshold','dense','reference-samples','tuning'];
function config(){return {passes:passes.map(p=>({...p})),cont_max:num('cont-cap'),temperature:num('temperature'),top_k:num('top-k'),threshold:num('threshold'),dense:$('dense').checked,reference_samples:num('reference-samples'),tuning:$('tuning').value};}
function error(text=''){$('error').hidden=!text;$('error').textContent=text;}
async function api(path,payload){const response=await fetch('/api/live/'+path,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const value=await response.json();if(!response.ok)throw new Error(value.error||'The runtime request failed.');return value;}
function queueEstimate(){budget=null;money();clearTimeout(estimateTimer);estimateRevision++;estimateTimer=setTimeout(estimate,250);}
function renderPasses(){
  $('pass-tabs').replaceChildren();
  for(const p of passes){const b=document.createElement('button');b.type='button';b.role='tab';b.id='tab-'+p.id;b.textContent=p.label;b.setAttribute('aria-selected',String(p.id===activePass));b.setAttribute('aria-controls','pass-details');b.tabIndex=p.id===activePass?0:-1;
    b.onclick=()=>{activePass=p.id;renderPasses();$('tab-'+p.id).focus();};
    b.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();let i=passes.findIndex(x=>x.id===activePass);i=e.key==='Home'?0:e.key==='End'?passes.length-1:(i+(e.key==='ArrowRight'?1:-1)+passes.length)%passes.length;activePass=passes[i].id;renderPasses();$('tab-'+activePass).focus();}};
    $('pass-tabs').append(b);}
  const p=passes.find(x=>x.id===activePass),details=$('pass-details');details.replaceChildren();details.setAttribute('aria-labelledby','tab-'+p.id);
  for(const [key,label,min,max]of [['label','Pass name'],['samples','Total draws per checkpoint',5,512],['start','Region first token',0,4095],['end','Region last token',0,4095],['stride','Checkpoint spacing',1,128],['offset','Offset from region start',0,127],['seed','Pass random seed',0,2147483647]]){
    const wrap=document.createElement('label');wrap.textContent=label;const input=document.createElement('input');input.id='pass-'+key;input.type=key==='label'?'text':'number';if(min!==undefined){input.min=min;input.max=max;}input.value=p[key];if(key==='label')input.maxLength=80;
    input.oninput=()=>{p[key]=key==='label'?input.value:(input.value.trim()===''?NaN:Number(input.value));if(key==='label')$('tab-'+p.id).textContent=input.value||'Unnamed pass';queueEstimate();};wrap.append(input);details.append(wrap);}
  const remove=document.createElement('button');remove.textContent='Remove pass';remove.id='remove-pass';remove.className='secondary';remove.disabled=passes.length===1;remove.onclick=()=>{passes=passes.filter(x=>x.id!==p.id);activePass=passes[0].id;renderPasses();queueEstimate();};details.append(remove);actions();
}
$('add-pass').onclick=()=>{const p=newPass(passes);passes.push(p);activePass=p.id;renderPasses();queueEstimate();};
function money(){
  if(!budget){$('money').textContent='';return;}
  const throughput=$('throughput').value.trim()?num('throughput'):null,rate=$('rate').value.trim()?num('rate'):null;
  if((throughput!==null&&(!Number.isFinite(throughput)||throughput<=0))||(rate!==null&&(!Number.isFinite(rate)||rate<0))){$('money').textContent='Use positive throughput and a non-negative hourly rate.';return;}
  const v=gpuEstimate(budget.max_continuation_tokens,throughput,rate);
  $('money').textContent=v.hours===null?'Enter measured throughput to project generation time.':`At the full token allowance: ${v.hours.toFixed(2)} hours${v.dollars===null?'':` · $${v.dollars.toFixed(2)}`} for the selected passes and reference. Projection only.`;
}
async function estimate(){
  const version=++estimateRevision;$('temperature-notice').hidden=num('temperature')===1;
  if(!state?.base||state.job.status==='running')return;
  try{const v=await api('estimate',config());if(version!==estimateRevision)return;budget=v;$('budget').replaceChildren();
    const lines=v.passes.map(p=>`${p.label}: ${p.positions.length} checkpoints × ${p.samples} draws = ${fmt(p.positions.length*p.samples)} continuations.`);
    lines.push(`${v.unique_checkpoints} distinct checkpoints; ${v.sampled_checkpoint_visits} visits including overlaps.`,`Independent reference: ${fmt(v.reference_rollouts)} additional continuations.`,`Total: ${fmt(v.total_rollouts)} draws, at most ${fmt(v.max_continuation_tokens)} generated continuation tokens.`,`Fewer samples is not evidence of savings at comparable accuracy.`);
    for(const text of lines){const p=document.createElement('div');p.textContent=text;$('budget').append(p);}money();
  }catch(e){if(version!==estimateRevision)return;budget=null;$('budget').textContent=e.message;money();}
}
function actions(){const busy=state?.job.status==='running';$('load').disabled=busy;$('unload').disabled=busy||!state?.model;$('base').disabled=busy||!state?.model;$('run').disabled=busy||!state?.base||baseFormDirty;$('base-stale').hidden=!baseFormDirty||!state?.base;$('stop').disabled=!busy;
  for(const id of [...fields,'seed','model-id','revision','device','batch','question','answers','mode','base-cap'])$(id).disabled=busy;
  $('add-pass').disabled=busy||passes.length>=8;for(const el of $('pass-details').querySelectorAll('input,button'))el.disabled=busy||(el.id==='remove-pass'&&passes.length===1);
}
async function refresh(){
  const before=state;state=await api('status');actions();$('phase').textContent=state.job.phase;$('progress').max=state.job.total||1;$('progress').value=state.job.completed||0;
  $('model-status').textContent=state.model?`${state.model.model_id} · ${state.model.device.toUpperCase()} · ${state.model.dtype} · ${fmt(state.model.parameters)} parameters`:'No model attached.';
  if(state.job.status==='error')error(state.job.phase);
  const signature=state.base?JSON.stringify([state.model?.resolved_revision,state.base.config,state.base.text]):'';
  const changed=signature!==lastBaseSignature;
  if(changed){lastBaseSignature=signature;baseFormDirty=false;if(state.base){const cfg=state.base.config;if(cfg?.prompt!==undefined){$('question').value=cfg.prompt;$('answers').value=cfg.answers.join('\n');$('mode').value=cfg.mode;$('base-cap').value=cfg.max_tokens;$('seed').value=cfg.seed;}$('base-text').textContent=state.base.text;$('base-description').textContent=`${state.base.length} tokens · finished by ${state.base.finish_reason}${state.base.finish_reason!=='stop'?' — INCOMPLETE BASE':''} · ${state.base.question.question}`;
    $('base-tokens').textContent=state.base.tokens.map((token,i)=>`${i}\t${JSON.stringify(token)}\tP(top)=${state.base.top_token_probabilities?.[i]?.toFixed(6)??'not recorded'}`).join('\n');
    for(const p of passes){p.end=Math.min(state.base.length-1,31);p.start=0;p.stride=Math.min(p.stride,p.end);p.offset=Math.min(p.offset,Math.max(0,p.end-p.stride));}renderPasses();
  }else{$('base-text').textContent='No generated response yet.';$('base-tokens').textContent='No trace yet.';budget=null;$('budget').textContent='Generate a base response first.';money();}}
  if(state.job.status==='complete'&&state.job.action==='base'&&before?.job.status==='running'){baseFormDirty=false;actions();}
  if(state.job.status!=='running'&&(before?.job.status==='running'||changed))await estimate();
  if(state.job.result_id&&state.job.result_id!==lastResultId){lastResultId=state.job.result_id;await listRuns();$('runs').value=lastResultId;await loadResult(lastResultId);}return state;
}
async function start(action,payload){error();const response=await api(action,payload);
  if(action==='load')for(const [key,id]of [['model_id','model-id'],['revision','revision'],['device','device'],['batch_size','batch']])$(id).value=payload[key];
  if(action==='base'){$('question').value=payload.prompt??payload.question;$('answers').value=(payload.answers??['A','B','C','D']).join('\n');$('mode').value=payload.mode;$('base-cap').value=payload.max_tokens;$('seed').value=payload.seed;}
  if(action==='run'){for(const [key,id]of [['cont_max','cont-cap'],['temperature','temperature'],['top_k','top-k'],['threshold','threshold'],['reference_samples','reference-samples'],['tuning','tuning']])$(id).value=payload[key];$('dense').checked=payload.dense;if(payload.passes){passes=payload.passes.map(p=>({...p}));activePass=passes[0].id;renderPasses();}}
  await refresh();return response;}
const bind=(id,fn)=>$(id).addEventListener('click',()=>Promise.resolve().then(fn).catch(e=>error(e.message)));
bind('load',()=>start('load',{model_id:$('model-id').value.trim(),revision:$('revision').value.trim(),device:$('device').value,batch_size:num('batch')}));
bind('unload',()=>start('unload',{}));
bind('base',()=>start('base',{prompt:$('question').value,answers:$('answers').value.split('\n').filter(x=>x.trim()),mode:$('mode').value,max_tokens:num('base-cap'),seed:num('seed')}));
bind('run',()=>{if(baseFormDirty)throw new Error('Generate a new base for the changed prompt settings.');return start('run',config());});bind('stop',async()=>{await api('stop',{});$('phase').textContent='Stopping after the current operation…';});
for(const id of ['question','answers','mode','base-cap','seed'])$(id).addEventListener('input',()=>{baseFormDirty=true;actions();});
for(const id of fields)$(id).addEventListener('input',queueEstimate);
for(const id of ['throughput','rate'])$(id).addEventListener('input',money);
async function listRuns(){const list=await api('runs');const previous=$('runs').value;$('runs').replaceChildren(new Option('Select a completed run',''),...list.map(r=>new Option(`${new Date(r.created*1000).toLocaleString()} · ${r.model} · ${(r.prompt??'').slice(0,80)}`,r.id)));$('runs').value=previous;}
async function loadResult(id){if(!id)return;const revision=++resultRevision;const loaded=await api('export?id='+encodeURIComponent(id));if(revision!==resultRevision)return;result=loaded;$('outcome').replaceChildren(...result.categories.map(x=>new Option(x,x)));$('viewer-outcome').replaceChildren(new Option('All outcomes',''),...result.categories.map(x=>new Option(x,x)));$('viewer-search').value='';$('viewer-status').value='';$('export').hidden=false;$('export').href='/api/live/export?id='+id;$('export').download='fork-run-'+id+'.json';await draw();
  const ps=resultPasses(result);$('viewer-pass').replaceChildren(...ps.map(p=>new Option(p.label,p.id)),...(result.records?.dense?[new Option('Independent reference','dense')]:[]));viewerPositions();navigate('results');}
$('runs').addEventListener('change',()=>loadResult($('runs').value).catch(e=>error(e.message)));
for(const id of ['outcome','bands'])$(id).addEventListener('change',()=>draw().catch(e=>error(e.message)));
async function draw(){
  if(!result)return;$('match-rule').textContent=result.base.question.matching==='answer_text_anywhere_v1'?'Readout: one distinct answer-text match anywhere in a completed reply. These curves measure matching text, not semantic correctness. Multiple matches, no match and unfinished replies count as Other.':'Historical A–D readout: labels retain the parser used when this run was collected.';const k=result.categories.indexOf($('outcome').value),traces=[],ps=resultPasses(result);
  if(result.reference?.valid!==false&&result.reference)traces.push({x:result.reference.positions,y:result.reference.values.map(v=>v[k]),name:'Independent dense reference',mode:'lines',line:{color:'#8793a5',width:1.5}});
  const colors=['#2563eb','#c87816','#17815c','#963dcc','#c02e52','#367783','#6d641f','#48516f'];
  for(const [i,p]of ps.entries()){const c=p.curve,color=colors[i%colors.length];
    if(c.support.length){if($('bands').checked){traces.push({x:c.support,y:c.low.map(v=>v[k]),mode:'lines',line:{width:0},showlegend:false,hoverinfo:'skip'});traces.push({x:c.support,y:c.high.map(v=>v[k]),mode:'lines',line:{width:0},fill:'tonexty',fillcolor:color+'18',showlegend:false,hoverinfo:'skip'});}
      traces.push({x:c.support,y:c.smoothed.map(v=>v[k]),name:p.label+' · reconstructed',mode:'lines',line:{color,width:2}});}
    traces.push({x:c.positions,y:c.weighted.map(v=>v[k]),name:p.label+(result.schema_version===2?' · observed outcomes':' · legacy weighted outcomes'),mode:'markers',marker:{color,size:8},customdata:c.positions.map(t=>[p.id,JSON.stringify(result.base.tokens[t])]),hovertemplate:'Token %{x}: %{customdata[1]}<br>P=%{y:.3f}<extra></extra>'});
  }
  await Plotly.react('live-plot',traces,{height:450,margin:{l:55,r:20,t:20,b:95},xaxis:{title:{text:'Response-token position'}},yaxis:{title:{text:`P(${$('outcome').value})`},range:[-.02,1.02]},legend:{orientation:'h',y:-.22},paper_bgcolor:'#fff',plot_bgcolor:'#fff'},{responsive:true,displaylogo:false});
  const plot=$('live-plot');plot.removeAllListeners?.('plotly_click');plot.on?.('plotly_click',event=>{const point=event.points[0];if(!point.customdata)return;$('viewer-pass').value=point.customdata[0];$('viewer-search').value='';$('viewer-status').value='';$('viewer-outcome').value='';viewerPositions(point.x);navigate('evidence');$('continuations').scrollIntoView({behavior:'smooth',block:'nearest'});});
  $('result-label').textContent=`${result.model.model_id} · ${result.schema_version===2?'all collected draws enter each fit':'legacy per-branch sampling'} · ${result.base.question.question}`;
  $('result-warnings').replaceChildren();
  const warnings=result.schema_version===2?[]:['Legacy run: fitted lines use a subsample of the collected outcomes; per-draw completion metadata may be unavailable.'];
  if(result.reference?.warning)warnings.push(result.reference.warning);
  $('statistics').replaceChildren();
  for(const p of ps){const c=p.curve,m=result.measured[p.id],box=document.createElement('div');box.className='stat-card';const title=document.createElement('strong');title.textContent=p.label;box.append(title);
    const lines=[`${fmt(m.continuations)} continuations · ${fmt(m.continuation_tokens)} generated tokens`,`${m.wall_seconds.toFixed(1)} seconds collection`,`${m.at_continuation_cap}/${m.continuations} reached the token cap.`];
    if(c.parameters)lines.push(`Fit: ${c.parameters.variant}, penalty ${c.parameters.pen}, bandwidth ${c.parameters.h}`,c.positions.length<4?'Too few checkpoints to detect change intervals.':`Candidate intervals: ${c.boundaries.map(b=>`${b.left}–${b.right}`).join(', ')||'none detected'}`);else lines.push('Reconstruction withheld. Inspect the outcomes below.');
    if(c.comparison)lines.push(`Mean TV to reference: ${c.comparison.mean_tv.toFixed(4)}`,`Held-out log likelihood: ${c.comparison.mean_log_likelihood.toFixed(4)}`,`Band coverage: ${(100*c.comparison.empirical_band_coverage).toFixed(1)}% (model-based bands exclude exact 0/1).`);else lines.push('No valid independent-reference comparison.');
    for(const text of lines){const d=document.createElement('div');d.textContent=text;box.append(d);}$('statistics').append(box);
    warnings.push(...(c.warnings||[]).map(w=>`${p.label}: ${w}`));
    if(result.schema_version!==2&&m.at_continuation_cap/m.continuations>.1)warnings.push(`${p.label}: excessive cap hits in this historical run. Do not interpret its fitted curve as completed-answer behavior.`);
  }
  for(const w of warnings){const el=document.createElement('p');el.className='warning';el.textContent=w;$('result-warnings').append(el);}
}
function navigate(view){
  document.querySelector('.live-workspace').dataset.view=view;
  for(const el of document.querySelectorAll('.workspace-nav button')){
    if(el.dataset.view===view)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');
  }
  if(view==='results'&&result)Plotly.Plots?.resize('live-plot');
}
for(const el of document.querySelectorAll('.workspace-nav button'))el.onclick=()=>navigate(el.dataset.view);
$('browse-evidence').onclick=()=>navigate('evidence');$('back-results').onclick=()=>navigate('results');
let evidencePage=0,selectedDraw=null;
const pageSize=30;
function viewerPositions(selected){
  const rec=result?.records?.[$('viewer-pass').value];const ts=[...new Set((rec?.branches||[]).map(b=>b.t))].sort((a,b)=>a-b);
  $('viewer-position').replaceChildren(new Option('All checkpoints',''),...ts.map(t=>new Option('Token '+t,t)));if(ts.includes(selected))$('viewer-position').value=selected;viewer();
}
function viewer(reset=true){
  if(reset){evidencePage=0;selectedDraw=null;}
  const rec=result?.records?.[$('viewer-pass').value],position=$('viewer-position').value;
  $('continuations').replaceChildren();
  $('viewer-note').textContent=rec?'Run '+result.id+' · '+result.base.question.question:'Select a saved run. No attached model is needed to browse.';
  const pos=rec?.positions?.find(p=>String(p.t)===position);
  $('checkpoint-info').textContent=pos?`${pos.samples} total draws · ${pos.candidates.length} retained branches · ${(100*pos.retained_mass).toFixed(3)}% next-token probability mass retained.`:'Browse all checkpoints or choose one. Each row is an actual saved draw; completed does not mean correct.';
  const rows=[];let total=0;
  const query=$('viewer-search').value.toLocaleLowerCase(),outcome=$('viewer-outcome').value,status=$('viewer-status').value;
  for(const b of rec?.branches||[]){
    if(position!==''&&String(b.t)!==position)continue;
    b.answers.forEach((answer,i)=>{total++;const obs=b.observations?.[i];
      if(outcome&&outcome!==answer)return;
      if(status==='ambiguous'?obs?.label_source!=='ambiguous':status&&obs?.stop_reason!==status)return;
      if(query&&!(obs?.full_response_text??'').toLocaleLowerCase().includes(query))return;
      rows.push({b,i,answer,obs,key:`${b.t}:${b.tok_id}:${i}`});
    });
  }
  rows.sort((a,b)=>a.b.t-b.b.t||(a.b.draw_indices?.[a.i]??a.i)-(b.b.draw_indices?.[b.i]??b.i));
  evidencePage=Math.min(evidencePage,Math.max(0,Math.ceil(rows.length/pageSize)-1));
  const page=rows.slice(evidencePage*pageSize,(evidencePage+1)*pageSize);
  $('viewer-count').textContent=`${rows.length} of ${total} continuations match · Page ${evidencePage+1} of ${Math.max(1,Math.ceil(rows.length/pageSize))}`;
  $('draw-prev').disabled=evidencePage===0;$('draw-next').disabled=(evidencePage+1)*pageSize>=rows.length;
  if(!page.some(r=>r.key===selectedDraw))selectedDraw=page[0]?.key??null;
  for(const row of page){const b=document.createElement('button');b.className='draw-row';b.setAttribute('aria-pressed',String(row.key===selectedDraw));
    const title=document.createElement('strong');title.textContent=`Token ${row.b.t} · Draw ${(row.b.draw_indices?.[row.i]??row.i)+1} · ${row.answer}`;
    const meta=document.createElement('span');meta.textContent=`${row.obs?.stop_reason==='length'?'Reached cap':row.obs?.stop_reason==='eos'?'Completed':'Historical'} · ${row.obs?.generated_tokens??row.b.cont_lens?.[row.i]??'?'} new tokens`;
    b.append(title,meta);b.onclick=()=>{selectedDraw=row.key;viewer(false);};$('continuations').append(b);
  }
  showDraw(page.find(r=>r.key===selectedDraw));
}
function showDraw(row){
  const target=$('draw-detail');target.replaceChildren();
  if(!row){const p=document.createElement('p');p.textContent='No continuations match these filters.';target.append(p);return;}
  const {b,i,answer,obs}=row;
  const title=document.createElement('h3');title.textContent=`Checkpoint ${b.t} / Draw ${(b.draw_indices?.[i]??i)+1}`;target.append(title);
  const meta=document.createElement('p');meta.className='help';meta.textContent=`Outcome: ${answer} · branch token ID ${b.tok_id} · next-token P=${b.tok_p.toFixed(6)} · ${obs?.label_source??'historical extraction'} · ${obs?.channel_reached??'channel unknown'}`;target.append(meta);
  if(obs?.matched_answers?.length){const p=document.createElement('p');p.textContent='Matched answer texts: '+obs.matched_answers.join(' / ');target.append(p);}
  const mode=document.createElement('select');mode.setAttribute('aria-label','Displayed text');mode.append(new Option('Newly generated continuation','continuation'),new Option('Full response: preserved prefix + branch + continuation','full'),new Option('Reply used for matching','reply'),new Option('Continuation token IDs','ids'));target.append(mode);
  const note=document.createElement('p');note.className='help';target.append(note);const pre=document.createElement('pre');target.append(pre);
  const show=()=>{const value=mode.value;
    note.textContent=value==='continuation'?'Only the new text after the selected branch token. The preserved prefix is excluded.':value==='full'?'The response prefix and branch token are included; the original question is excluded.':value==='reply'?'Completed reply text supplied to the matcher. Untagged reasoning in generic models can be included.':'Raw generated continuation IDs, excluding the forced branch token and stripped terminal EOS.';
    pre.textContent=value==='ids'?JSON.stringify(b.continuation_ids?.[i]??[]):value==='full'?(obs?.full_response_text??'Full text was not saved in this historical run.'):value==='reply'?(obs?.reply_text??'No completed reply was saved for matching.'):(obs?.continuation_text??'Decoded text was not saved in this historical run. Choose token IDs.');
  };mode.onchange=show;show();
}
$('viewer-pass').onchange=()=>viewerPositions();
for(const id of ['viewer-position','viewer-outcome','viewer-status'])$(id).onchange=()=>viewer();
$('viewer-search').oninput=()=>viewer();
$('draw-prev').onclick=()=>{evidencePage--;viewer(false);};$('draw-next').onclick=()=>{evidencePage++;viewer(false);};
function register(){const context=document.modelContext;if(!context?.registerTool)return;const lifecycle=new AbortController();window.addEventListener('pagehide',()=>lifecycle.abort(),{once:true});
  for(const tool of [{name:'read_live_fork',description:'Read attached model, fixed trace and current job. Does not start computation.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:true},execute:refresh},
    {name:'start_live_fork_action',description:'Start load, base, run or unload. Loading may download weights. Load settings: model_id, revision, device (auto/cpu/cuda), batch_size. Base settings: prompt (text), answers (1–32 unique strings to match anywhere in completed replies), mode (chat/base), max_tokens, seed. Unload takes {}. Run settings: passes array (id,label,start,end,stride,offset,samples 5-512 draws per checkpoint,seed), cont_max,temperature,top_k,threshold,dense,reference_samples,tuning. Maximum 8 passes. Read status to track completion.',inputSchema:{type:'object',properties:{action:{type:'string',enum:['load','base','run','unload']},settings:{type:'object'}},required:['action','settings'],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:true},execute:async input=>{const response=await start(input.action,input.settings);if(input.action==='run'&&input.settings.passes){passes=input.settings.passes.map(p=>({...p}));activePass=passes[0].id;renderPasses();}return response;}}]){try{Promise.resolve(context.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch{}}
}
async function poll(){try{await refresh();}catch(e){error(e.message);}setTimeout(poll,1500);}
renderPasses();await listRuns().catch(e=>error(e.message));await refresh().catch(e=>error(e.message));
const requestedRun=new URLSearchParams(location.search).get('run');if(requestedRun){$('runs').value=requestedRun;await loadResult(requestedRun).catch(e=>error(e.message));}register();poll();
