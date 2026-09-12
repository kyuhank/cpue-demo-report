const API='https://tgusnkwvfzwdeufzevhk.supabase.co/functions/v1/workshop-api',family=document.body.dataset.module,$=id=>document.getElementById(id);
const names={extract:'Extract',cpue_vessel:'CPUE A',cpue_year:'CPUE B',prepare_vessel:'Input preparation A',prepare_year:'Input preparation B',assessment_vessel_ref:'Assessment A · 1',assessment_vessel_high_m:'Assessment A · 2',assessment_year_ref:'Assessment B · 1',assessment_year_high_m:'Assessment B · 2',synthesis:'Results synthesis',report:'Report'};
const allowed=Object.keys(names).filter(k=>(k.startsWith('prepare_')?'inputs':k.split('_')[0])===family);
let current=new URL(location.href).searchParams.get('job')||'',ticket=0,download='';
function stage(source){const m=source.match(/^(\d+)-(\d+)-([a-z_]+)$/);return m&&allowed.includes(m[3])?m:null;}
async function read(path){const r=await fetch(API+path,{cache:'no-store'});if(!r.ok)throw Error('This output is not available yet, or the demonstration has reset.');return r;}
async function load(){const id=++ticket;$('download').hidden=true;$('result').srcdoc='';$('status').textContent='Loading recorded job outputs…';try{
 const info=await (await read('/api/status')).json();if(id!==ticket)return;
 if(!current&&info.has_run)current=info.stages.find(s=>allowed.includes(s.key)&&s.status==='completed')?.source_id||info.stages.find(s=>allowed.includes(s.key))?.source_id||'';
 const match=stage(current);if(!match)throw Error('Start a job in the shared workspace, then open its HTML output.');
 $('job').replaceChildren();const jobs=(info.has_run?info.stages.filter(s=>allowed.includes(s.key)).map(s=>[s.source_id,names[s.key]]):[]);if(!jobs.some(([source])=>source===current))jobs.unshift([current,names[match[3]]+' · saved run']);
 for(const [value,label] of jobs){const o=document.createElement('option');o.value=value;o.textContent=label;$('job').append(o);}$('job').value=current;
 const file=family==='report'?'report.html':'results.html';
 const [html,record]=await Promise.all([read('/api/output?job='+current+'&file='+file).then(r=>r.text()),read('/api/output?job='+current+'&file=record.json').then(r=>r.json())]);if(id!==ticket)return;
 if(record.stage!==match[3]||record.code_source?.repository!=='kyuhank/cpue-demo-'+family)throw Error('The result does not match this module.');
 $('status').textContent=names[match[3]]+' · run '+match[1]+(String(record.run_id)!==match[1]?' · verified result reused':'');
 $('source').href='https://github.com/'+record.code_source.repository+'/commit/'+record.code_source.commit;$('source').textContent='Code '+record.code_source.commit.slice(0,8)+' ↗';$('run').href='https://github.com/kyuhank/cpue-toy-data/actions/runs/'+match[1];
 $('result').srcdoc=html;if(download)URL.revokeObjectURL(download);download=URL.createObjectURL(new Blob([html],{type:'text/html'}));$('download').href=download;$('download').download=match[3]+'-'+match[1]+'.html';$('download').hidden=false;
 }catch(e){if(id===ticket)$('status').textContent=e.message;}}
$('job').onchange=()=>{current=$('job').value;history.replaceState(null,'','?job='+encodeURIComponent(current));load();};$('retry').onclick=load;load();
