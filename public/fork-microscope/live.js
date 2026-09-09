import {gpuEstimate} from './math.mjs';
const $=id=>document.getElementById(id),num=id=>$(id).value.trim()===''?NaN:Number($(id).value);
let state=null,result=null,budget=null,estimateTimer,estimateRevision=0,lastBaseSignature='',lastResultId='';
const fmt=n=>new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(n);
const fields=['samples','stride','shift','start','end','cont-cap','temperature','top-k','threshold','seed','dense','reference-samples','tuning'];
function config(){return {samples:num('samples'),stride:num('stride'),shift:num('shift'),start:num('start'),end:num('end'),cont_max:num('cont-cap'),temperature:num('temperature'),top_k:num('top-k'),threshold:num('threshold'),seed:num('seed'),dense:$('dense').checked,reference_samples:num('reference-samples'),tuning:$('tuning').value};}
function error(text=''){$('error').hidden=!text;$('error').textContent=text;}
async function api(path,payload){const response=await fetch('/api/live/'+path,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const value=await response.json();if(!response.ok)throw new Error(value.error||'The runtime request failed.');return value;}
function money(){
  if(!budget){$('money').textContent='';return;}
  const throughput=$('throughput').value.trim()?num('throughput'):null,rate=$('rate').value.trim()?num('rate'):null;
  if((throughput!==null&&(!Number.isFinite(throughput)||throughput<=0))||(rate!==null&&(!Number.isFinite(rate)||rate<0))){$('money').textContent='Use positive throughput and a non-negative hourly rate.';return;}
  const v=gpuEstimate(budget.max_continuation_tokens,throughput,rate);
  $('money').textContent=v.hours===null?'Enter measured throughput to project generation time.':`At the full token allowance: ${v.hours.toFixed(2)} hours${v.dollars===null?'':` · $${v.dollars.toFixed(2)}`} for both passes${config().dense?' plus the reference':''}. Projection only.`;
}
async function estimate(){
  const version=++estimateRevision;if(!state?.base||state.job.status==='running')return;
  try{const v=await api('estimate',config());if(version!==estimateRevision)return;budget=v;
    $('budget').replaceChildren();
    for(const text of [`Both passes: ${fmt(v.combined_rollouts)} continuations across ${v.branches.first+v.branches.second} retained branches.`,`Every token, same samples per branch: ${fmt(v.dense_same_samples_rollouts)} continuations.`,`Reduction at equal token caps: ${(100*v.reduction_at_equal_caps).toFixed(1)}%.`,`Optional separate reference: ${fmt(v.reference_rollouts)} additional continuations.`,`Total selected run: at most ${fmt(v.max_continuation_tokens)} continuation tokens.`]){const p=document.createElement('div');p.textContent=text;$('budget').append(p);}money();
  }catch(e){if(version!==estimateRevision)return;budget=null;$('budget').textContent=e.message;money();}
}
function actions(){const busy=state?.job.status==='running';$('load').disabled=busy;$('unload').disabled=busy||!state?.model;$('base').disabled=busy||!state?.model;$('run').disabled=busy||!state?.base;$('stop').disabled=!busy;for(const id of [...fields,'model-id','revision','device','batch','question','choice-a','choice-b','choice-c','choice-d','mode','base-cap'])$(id).disabled=busy;}
async function refresh(){
  const before=state;state=await api('status');actions();
  $('phase').textContent=state.job.phase;$('progress').max=state.job.total||1;$('progress').value=state.job.completed||0;
  $('model-status').textContent=state.model?`${state.model.model_id} · ${state.model.device.toUpperCase()} · ${state.model.dtype} · ${fmt(state.model.parameters)} parameters`:'No model attached.';
  if(state.job.status==='error')error(state.job.phase);
  const signature=state.base?JSON.stringify([state.model?.resolved_revision,state.base.config,state.base.text]):'';
  if(signature!==lastBaseSignature){lastBaseSignature=signature;if(state.base){$('base-text').textContent=state.base.text;$('base-description').textContent=`${state.base.length} tokens · finished by ${state.base.finish_reason} · ${state.base.question.question}`;$('end').value=Math.min(state.base.length-1,31);$('start').value=0;}else{$('base-text').textContent='No generated response yet.';budget=null;$('budget').textContent='Generate a base response first.';money();}}
  if(state.job.status!=='running'&&(before?.job.status==='running'||signature&&signature!== (before?.base?JSON.stringify([before.model?.resolved_revision,before.base.config,before.base.text]):'')))await estimate();
  if(state.job.result_id&&state.job.result_id!==lastResultId){lastResultId=state.job.result_id;await listRuns();$('runs').value=lastResultId;await loadResult(lastResultId);}
  return state;
}
async function start(action,payload){error();const response=await api(action,payload);
  // Apply accepted tool/API settings to the same controls used by the person.
  if(action==='load'){for(const [key,id]of [['model_id','model-id'],['revision','revision'],['device','device'],['batch_size','batch']])$(id).value=payload[key];}
  if(action==='base'){$('question').value=payload.question;['a','b','c','d'].forEach((x,i)=>$('choice-'+x).value=payload.choices[i]);$('mode').value=payload.mode;$('base-cap').value=payload.max_tokens;$('seed').value=payload.seed;}
  if(action==='run'){for(const [key,id]of [['samples','samples'],['stride','stride'],['shift','shift'],['start','start'],['end','end'],['cont_max','cont-cap'],['temperature','temperature'],['top_k','top-k'],['threshold','threshold'],['seed','seed'],['reference_samples','reference-samples'],['tuning','tuning']])$(id).value=payload[key];$('dense').checked=payload.dense;}
  await refresh();return response;}
const bind=(id,fn)=>$(id).addEventListener('click',()=>fn().catch(e=>error(e.message)));
bind('load',()=>start('load',{model_id:$('model-id').value.trim(),revision:$('revision').value.trim(),device:$('device').value,batch_size:num('batch')}));
bind('unload',()=>start('unload',{}));
bind('base',()=>start('base',{question:$('question').value,choices:['a','b','c','d'].map(c=>$('choice-'+c).value),mode:$('mode').value,max_tokens:num('base-cap'),seed:num('seed')}));
bind('run',()=>start('run',config()));bind('stop',async()=>{await api('stop',{});$('phase').textContent='Stopping after the current load, decode or sample batch…';});
for(const id of fields)$(id).addEventListener('input',()=>{clearTimeout(estimateTimer);estimateRevision++;estimateTimer=setTimeout(estimate,250);});
for(const id of ['throughput','rate'])$(id).addEventListener('input',money);
async function listRuns(){const list=await api('runs');const previous=$('runs').value;$('runs').replaceChildren(new Option('Select a completed run',''),...list.map(r=>new Option(`${new Date(r.created*1000).toLocaleString()} · ${r.model}`,r.id)));$('runs').value=previous;}
async function loadResult(id){if(!id)return;result=await api('result?id='+encodeURIComponent(id));$('export').hidden=false;$('export').href='/api/live/export?id='+id;$('export').download='fork-run-'+id+'.json';await draw();}
$('runs').addEventListener('change',()=>loadResult($('runs').value).catch(e=>error(e.message)));
for(const id of ['outcome','bands'])$(id).addEventListener('change',()=>draw().catch(e=>error(e.message)));
async function draw(){
  if(!result)return;const k=result.categories.indexOf($('outcome').value),traces=[];
  if(result.reference)traces.push({x:result.reference.positions,y:result.reference.values.map(v=>v[k]),name:'Independent dense reference',mode:'lines',line:{color:'#8793a5',width:1.5}});
  for(const [key,label,color,fill]of [['first','Pass 1','#2563eb','rgba(37,99,235,.10)'],['second','Pass 2','#c87816','rgba(200,120,22,.10)']]){const c=result[key];
    if($('bands').checked){traces.push({x:c.support,y:c.low.map(v=>v[k]),mode:'lines',line:{width:0},showlegend:false,hoverinfo:'skip'});traces.push({x:c.support,y:c.high.map(v=>v[k]),mode:'lines',line:{width:0},fill:'tonexty',fillcolor:fill,showlegend:false,hoverinfo:'skip'});}
    traces.push({x:c.support,y:c.smoothed.map(v=>v[k]),name:label+' · reconstructed',mode:'lines',line:{color,width:2,dash:key==='second'?'dash':'solid'}});
    traces.push({x:c.positions,y:c.weighted.map(v=>v[k]),name:label+' · weighted outcomes',mode:'markers',marker:{color,size:7,symbol:key==='first'?'circle':'diamond'},customdata:c.positions.map(t=>JSON.stringify(result.base.tokens[t])),hovertemplate:'Token %{x}: %{customdata}<br>P=%{y:.3f}<extra>'+label+'</extra>'});
  }
  await Plotly.react('live-plot',traces,{height:450,margin:{l:55,r:20,t:20,b:95},xaxis:{title:{text:'Response-token position'}},yaxis:{title:{text:`P(${$('outcome').value})`},range:[-.02,1.02]},legend:{orientation:'h',y:-.22},paper_bgcolor:'#fff',plot_bgcolor:'#fff'},{responsive:true,displaylogo:false});
  $('result-label').textContent=`${result.model.model_id} · ${result.settings.samples} continuations/branch · ${result.settings.tuning==='cv'?'cross-validated':'fixed'} reconstruction · ${result.base.question.question}`;
  $('statistics').replaceChildren();for(const [key,label]of [['first','Pass 1'],['second','Pass 2']]){const c=result[key],m=result.measured[key],box=document.createElement('div');box.className='stat-card';const title=document.createElement('strong');title.textContent=label;box.append(title);
    const lines=[`${fmt(m.continuations)} continuations · ${fmt(m.continuation_tokens)} generated tokens`,`${m.wall_seconds.toFixed(1)} seconds collection + extraction`,`Fit: ${c.parameters.variant}, penalty ${c.parameters.pen}, bandwidth ${c.parameters.h}`,`Candidate change intervals: ${c.boundaries.map(b=>`${b.left}–${b.right}`).join(', ')||'none'}`];
    if(m.logit_fallback!==undefined)lines.push(`${m.logit_fallback}/${m.continuations} answers required logit fallback; ${m.at_continuation_cap} reached the continuation cap.`);
    if(c.comparison)lines.push(`Mean TV to reference: ${c.comparison.mean_tv.toFixed(4)}`,`Held-out log likelihood: ${c.comparison.mean_log_likelihood.toFixed(4)}`,`Empirical band coverage: ${(100*c.comparison.empirical_band_coverage).toFixed(1)}%`);else lines.push('No independent reference collected; error and coverage unmeasured.');
    for(const text of lines){const p=document.createElement('div');p.textContent=text;box.append(p);}$('statistics').append(box);}
}
function register(){const context=document.modelContext;if(!context?.registerTool)return;const lifecycle=new AbortController();window.addEventListener('pagehide',()=>lifecycle.abort(),{once:true});
  for(const tool of [
    {name:'read_live_fork',description:'Read the attached open-weight model, generated base and current collection job. Does not start computation.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:true},execute:refresh},
    {name:'start_live_fork_action',description:'Start local computation; model loading may download weights. Returns a job ID; read_live_fork reports completion. Exact settings for load: model_id, revision, device (auto/cpu/cuda), batch_size. For base: question, choices (four strings A–D), mode (chat/base), max_tokens, seed. For run: samples (5–512 per branch), stride, shift (less than stride), start, end (inclusive token indices), cont_max, temperature, top_k, threshold, seed, dense (boolean), reference_samples (5–512), tuning (cv/fixed). For unload: empty settings. Run requires a generated base; base requires an attached model.',inputSchema:{type:'object',properties:{action:{type:'string',enum:['load','base','run','unload']},settings:{type:'object'}},required:['action','settings'],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:true},execute:async input=>{if(!input||Object.keys(input).some(k=>!['action','settings'].includes(k))||!['load','base','run','unload'].includes(input.action))throw new Error('Choose a supported action.');return start(input.action,input.settings);}}
  ]){try{Promise.resolve(context.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch{}}
}
async function poll(){try{await refresh();}catch(e){error(e.message);}setTimeout(poll,1500);}
await listRuns().catch(e=>error(e.message));await refresh().catch(e=>error(e.message));
const requestedRun=new URLSearchParams(location.search).get('run');
if(requestedRun){$('runs').value=requestedRun;await loadResult(requestedRun).catch(e=>error(e.message));}
register();poll();
