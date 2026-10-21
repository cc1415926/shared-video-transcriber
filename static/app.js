'use strict';
const $ = id => document.getElementById(id);
const terminal = new Set(['done','error','cancelled','interrupted']);
const requestedJob=new URLSearchParams(location.search).get('job')||'';
const state = {token:'',health:null,jobs:[],selected:/^[a-f0-9]{32}$/.test(requestedJob)?requestedJob:localStorage.getItem('video.selected'),job:null,tab:'overview',lastRender:'',historyKey:'',page:'home',filter:'all',verificationOpened:new Set(),clipPreviewEnd:null};
const fmt = sec => {const n=Math.max(0,Math.floor(sec||0));return (n>=3600?Math.floor(n/3600)+':':'')+String(Math.floor(n/60)%60).padStart(2,'0')+':'+String(n%60).padStart(2,'0');};
const mb = n => ((n||0)/1048576).toFixed(1)+' MB';
const labels = {done:'已完成',running:'处理中',queued:'排队中',cancelling:'正在停止',cancelled:'已取消',error:'失败',interrupted:'已中断'};
const platformLabel = value => ({douyin:'抖音',bilibili:'Bilibili',youtube:'YouTube',tiktok:'TikTok',local:'本地文件'}[value]||value);
function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
function visible(id,show){$(id).hidden=!show;}
function showPage(page){state.page=page;visible('home',page==='home');document.querySelector('.composer').hidden=page!=='workspace';visible('result',page==='workspace'&&!!state.job);document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===page));if(page==='workspace')$('composer-title').scrollIntoView({block:'start',behavior:'smooth'});}
function startNewTask(){state.selected=null;state.job=null;state.lastRender='';localStorage.removeItem('video.selected');showPage('workspace');visible('result',false);$('url').value='';$('url').focus();window.scrollTo({top:0,behavior:'smooth'});}
function toast(text){$('toast').textContent=text;visible('toast',true);clearTimeout(toast.timer);toast.timer=setTimeout(()=>visible('toast',false),3200);}
async function api(path,body){
  let response;
  try{
    response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json','X-Video-Token':state.token},body:body===undefined?undefined:JSON.stringify(body)});
  }catch{
    // fetch 在网络层就失败时只会抛 TypeError「Failed to fetch」，对用户没有意义。
    throw new Error('连不上本地服务：服务可能已经停止（启动窗口被关掉）。请双击「视频收件箱」重新启动，再刷新本页。');
  }
  let data;
  try{data=await response.json();}
  catch{throw new Error('本地服务返回了无法识别的内容，请重启服务后重试。');}
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'输入不符合要求，请检查链接和选项。');
  return data;
}
function assetUrl(name){return '/api/jobs/'+state.job.id+'/assets/'+encodeURIComponent(name);}
function activate(tab){
  state.tab=tab;
  document.querySelectorAll('[data-tab]').forEach(button=>{const active=button.dataset.tab===tab;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});
  ['overview','transcript','visual','rewrite'].forEach(id=>visible(id,id===tab));
}
async function selectJob(id){
  state.selected=id;localStorage.setItem('video.selected',id);state.lastRender='';state.historyKey='';
  const job=await api('/jobs/'+id);
  if(state.selected!==id)return;
  state.job=job;render();renderHistory();
}
function renderHistory(){
  const query=$('history-search').value.toLowerCase();
  const key=JSON.stringify([state.jobs,state.selected,query]);
  if(key===state.historyKey)return;state.historyKey=key;
  const list=$('history');list.replaceChildren();$('history-count').textContent=state.jobs.length;
  const matches=j=>state.filter==='all'||(state.filter==='running'&&!terminal.has(j.status))||(state.filter==='done'&&j.status==='done')||(state.filter==='visual'&&['visual','download'].includes(j.mode))||(state.filter==='rewrite'&&j.rewrite_status==='done')||(state.filter==='failed'&&['error','cancelled','interrupted'].includes(j.status));
  const jobs=state.jobs.filter(j=>matches(j)&&(j.title+' '+j.platform).toLowerCase().includes(query));
  if(!jobs.length)list.append(node('p',query?'没有匹配的记录':'处理过的视频会留在这里。','history-empty'));
  for(const job of jobs){
    const row=node('div',undefined,'history-row');
    const button=node('button',undefined,'history-item'+(job.id===state.selected?' active':''));
    button.append(node('strong',job.title));button.title=job.title;
    const meta=node('small');meta.append(node('span',platformLabel(job.platform)+(job.profile?' / '+({fast:'快速',balanced:'细致',accurate:'精细'}[job.profile]||job.profile):'')),node('span',labels[job.status]||job.status));button.append(meta);
    if(job.id===state.selected)button.setAttribute('aria-current','true');
    button.onclick=()=>{showPage('workspace');selectJob(job.id).then(()=>$('result').scrollIntoView({block:'start',behavior:'smooth'})).catch(e=>toast(e.message));};
    const remove=node('button','×','history-delete');remove.type='button';remove.title='删除这条记录';remove.setAttribute('aria-label','删除：'+job.title);
    remove.onclick=event=>{event.stopPropagation();if(typeof openDeleteJob==='function')openDeleteJob(job.id);};
    row.append(button,remove);list.append(row);
  }
  const counts={all:state.jobs.length,running:state.jobs.filter(j=>!terminal.has(j.status)).length,done:state.jobs.filter(j=>j.status==='done').length,visual:state.jobs.filter(j=>['visual','download'].includes(j.mode)).length,rewrite:state.jobs.filter(j=>j.rewrite_status==='done').length,failed:state.jobs.filter(j=>['error','cancelled','interrupted'].includes(j.status)).length};
  for(const key of Object.keys(counts)){const el=$('count-'+key);if(el)el.textContent=counts[key];}
  $('stat-total').textContent=counts.all;$('stat-done').textContent=counts.done;$('stat-rewrite').textContent=counts.rewrite;
}
function jump(seconds){
  if(state.job.video_file||state.job.local_video_available){
    activate('visual');const player=$('player');player.currentTime=seconds;player.scrollIntoView({block:'center',behavior:'smooth'});
  }else{
    activate('transcript');$('transcript-search').value='';renderSegments();
    const rows=[...document.querySelectorAll('.segment')];
    const row=rows.find(el=>Number(el.dataset.end)>=seconds);
    if(row){document.querySelectorAll('.highlight').forEach(el=>el.classList.remove('highlight'));row.classList.add('highlight');row.scrollIntoView({block:'center',behavior:'smooth'});}
  }
}
function timeButton(seconds){const b=node('button',fmt(seconds),'timestamp');b.title=(state.job.video_file||state.job.local_video_available)?'回看这个时间点':'定位到这段文字';b.onclick=()=>jump(seconds);return b;}
function renderSegments(){
  const q=$('transcript-search').value.trim().toLowerCase();const parent=$('segments');parent.replaceChildren();
  const segments=state.job.segments.filter(s=>(!q||s.text.toLowerCase().includes(q))&&(!$('review-only').checked||s.needs_review));
  // Keep the source index while rendering. `state.job` is refreshed in the
  // background, so deriving it later with `indexOf(s)` can return -1 when the
  // visible row belongs to the previous response object.
  for(const [index,s] of state.job.segments.entries()){
    if((q&&!s.text.toLowerCase().includes(q))||($('review-only').checked&&!s.needs_review))continue;
    const row=node('div',undefined,'segment');row.dataset.end=s.end;row.append(timeButton(s.start));
    const text=node('p');
    if(q){const idx=s.text.toLowerCase().indexOf(q);text.append(document.createTextNode(s.text.slice(0,idx)),node('mark',s.text.slice(idx,idx+q.length)),document.createTextNode(s.text.slice(idx+q.length)));}
    else text.textContent=s.text;
    row.append(text);
    if(s.needs_review){row.classList.add('needs-review');const badge=node('small','需复核','review-badge');badge.title=(s.review_reasons||[]).join('；');text.append(badge);}
    if(s.edited)text.append(node('small','已人工修正','edited-badge'));
    const edit=node('button','核对 / 修正','text-button edit-segment');edit.disabled=state.job.status!=='done'||state.job.summary_status==='running';edit.onclick=()=>beginInlineEditor(index,row,text);row.append(edit);parent.append(row);
  }
  visible('transcript-empty',!segments.length);
  $('transcript-empty').textContent=q?'没有找到匹配的文字。':$('review-only').checked?'当前没有标记为需复核的片段；未标记不代表一定正确。':terminal.has(state.job.status)?'此任务没有可用的文字稿。':'识别出第一段语音后，会逐段显示在这里。';
}
function renderContent(){
  const job=state.job;
  $('segment-count').textContent=job.segments.length||'';$('frame-count').textContent=job.frames.length||'';
  renderSegments();
  const snippets=$('snippets');snippets.replaceChildren();
  const indexes=[...new Set([0,Math.floor(job.segments.length/3),Math.floor(job.segments.length*2/3),Math.max(0,job.segments.length-1)])];
  if(!job.segments.length)snippets.append(node('p',job.mode==='download'?'下载完成后，可保存原视频。需要文字时，用同一个链接选择「只读文字」。':'文字还没准备好。你可以留在这里，也可以稍后从历史记录回来。','reader-note'));
  for(const index of indexes){const segment=job.segments[index];if(!segment)continue;const item=node('div',undefined,'snippet');item.append(timeButton(segment.start),node('p',segment.text));snippets.append(item);}
  visible('summary-text',!!job.summary);$('summary-text').textContent=job.summary||'';
  visible('snippets',!job.summary);$('overview-title').textContent=job.summary?'爆款结构分析':'先读这几处';
  $('overview-subtitle').textContent=job.summary?'分析仅依据本次口播文字与可选抽样画面，不代表平台数据或外部事实。':'从不同时间位置摘取原话，不是 AI 摘要。';
  visible('summary-progress',job.summary_status==='running');visible('summary-error',!!job.summary_error);$('summary-error').textContent=job.summary_error||'';
  $('summarize').disabled=job.status!=='done'||job.summary_status==='running'||(!job.transcript&&!job.frames.length);
  $('summarize').textContent=job.summary?'重新生成结构分析':'生成爆款结构分析';
  visible('player',!!(job.video_file||job.local_video_available));
  if(job.video_file||job.local_video_available){const src=job.local_video_available?'/api/jobs/'+job.id+'/original':assetUrl(job.video_file);if($('player').getAttribute('src')!==src)$('player').src=src;}else{$('player').removeAttribute('src');}
  const frames=$('frames');frames.replaceChildren();
  for(const frame of job.frames){const button=node('button',undefined,'frame');const image=node('img');image.src=assetUrl(frame.file);image.loading='lazy';image.alt='视频 '+fmt(frame.time)+' 的抽样画面';button.append(image,node('span',fmt(frame.time)+' · 点击回看'));button.onclick=()=>jump(frame.time);frames.append(button);}
  $('visual-note').textContent=job.mode==='visual'?'视频仅临时保留在应用缓存，用于预览和转录；点击“保存视频”后再选择正式保存位置。':job.video_file?'视频仅临时保留在应用缓存。':'此任务只提取声音。选择「文字 + 视频」重新处理，就能查看和回看视频。';
  visible('export',job.status==='done');$('export').href='/api/jobs/'+job.id+'/bundle';
  visible('srt-link',job.assets.includes('transcript.srt'));$('srt-link').href=assetUrl('transcript.srt');
  const spoken=job.spoken_script||job.transcript;
  $('copy-spoken-script').disabled=!spoken;
  visible('spoken-script-link',job.status==='done'&&job.assets.includes('spoken-script.txt'));
  $('spoken-script-link').href=assetUrl('spoken-script.txt');$('spoken-script-link').download='口播稿.txt';
  visible('save-video',!!job.video_file);$('save-video').disabled=job.status!=='done';
  visible('clip-video',job.status==='done'&&!!(job.video_file||job.local_video_available));
  $('copy').disabled=!job.transcript;
  if(typeof renderEnhancements==='function')renderEnhancements();
}
function render(){
  const job=state.job;if(!job)return;
  visible('empty',false);visible('result',state.page==='workspace');
  $('result-title').textContent=job.title;
  $('result-meta').textContent=[platformLabel(job.platform),job.author,job.duration?fmt(job.duration):null,job.model?('本地 '+job.model):null,labels[job.status]].filter(Boolean).join(' / ');
  $('source-link').href=job.url;
  visible('source-link',!!job.url);
  $('stage').textContent=job.stage;
  const progress=$('progress');
  if(job.progress===null||job.progress===undefined)progress.removeAttribute('value');else progress.value=job.progress;
  $('progress-number').textContent=job.progress===null||job.progress===undefined?'':Math.floor(job.progress*100)+'%';
  let detail='已用 '+fmt(job.elapsed);
  if(job.stage==='识别语音'&&job.duration){detail+=' · 已识别 '+fmt(job.transcribed_seconds)+' / '+fmt(job.duration);if(job.progress>.06&&job.progress<.99){const spent=Date.now()/1000-job.stage_started;detail+=' · 估计还需 '+fmt(spent*(1-job.progress)/job.progress);}}
  else if(job.downloaded){detail+=' · 当前文件 '+mb(job.downloaded)+(job.total_bytes?' / '+mb(job.total_bytes):'（总大小未知）');if(job.speed>0)detail+=' · '+mb(job.speed)+'/s';}
  if(job.status==='done')detail='总耗时 '+fmt(job.elapsed)+(job.media_bytes?' · 媒体 '+mb(job.media_bytes):'')+(job.video_file?' · 视频已临时缓存，点击“保存视频”选择位置':' · 文字已保存到本地');
  if(job.status==='done'&&job.local_source)detail='总耗时 '+fmt(job.elapsed)+' · 原文件 '+(job.local_source.bytes/1073741824).toFixed(2)+' GB（只读引用） · 笔记已保存';
  $('progress-detail').textContent=detail;
  visible('cancel',!terminal.has(job.status));$('cancel').disabled=job.status==='cancelling';
  visible('retry',['error','cancelled','interrupted'].includes(job.status));
  const needsVerification=job.status==='error'&&['douyin','youtube','tiktok'].includes(job.platform)&&/登录|验证|可播放|可读取/.test(job.error||'');
  visible('verify-source',needsVerification);$('verify-source').disabled=false;
  if(needsVerification&&!state.verificationOpened.has(job.id)){
    state.verificationOpened.add(job.id);
    api('/jobs/'+job.id+'/open-source',{}).then(result=>toast(result.message)).catch(e=>toast(e.message));
  }
  visible('job-error',!!job.error);$('job-error').textContent=job.error||'';
  $('warnings').replaceChildren(...job.warnings.map(w=>node('p',w)));
  const key=JSON.stringify([job.id,job.status,job.segments,job.frames,job.summary,job.summary_status,job.summary_error,job.rewrite_script,job.rewrite_status,job.assets,job.clips,job.revision,job.media_cleaned,job.cache_cleaned,job.media_available,job.local_video_available]);
  if(key!==state.lastRender){state.lastRender=key;renderContent();}
  renderClips();
}
function clipSeconds(id){return Number($(id).value)||0;}
function setClipValues(start,end,focus='start'){
  const duration=Number(state.job?.duration)||0;start=Math.max(0,Math.min(start,duration));end=Math.max(0,Math.min(end,duration));
  if(end<=start)end=Math.min(duration,start+.05);if(end<=start)start=Math.max(0,end-.05);
  for(const [id,value] of [['clip-start',start],['clip-end',end],['clip-start-input',start],['clip-end-input',end]])$(id).value=value.toFixed(2);
  $('clip-duration').textContent='片段时长：'+fmt(Math.max(0,end-start));
  seekClipPreviewFrame(focus.startsWith('end')?end:start);
}
function seekClipPreviewFrame(seconds){
  const video=$('clip-preview-player');
  const duration=Number(state.job?.duration)||0;
  // Seeking exactly to EOF often renders black; show the nearest displayable frame.
  const target=Math.max(0,Math.min(seconds,Math.max(0,duration-.04)));
  video.dataset.frameSeek=String(target);
  state.clipPreviewEnd=null;
  if(video.readyState>=1){video.pause();video.currentTime=target;}
}
function syncClipValues(changed){
  let start=clipSeconds(changed==='start-input'?'clip-start-input':'clip-start');
  let end=clipSeconds(changed==='end-input'?'clip-end-input':'clip-end');
  if(changed.startsWith('start')&&start>=end)end=start+.05;
  if(changed.startsWith('end')&&end<=start)start=Math.max(0,end-.05);
  setClipValues(start,end,changed);
}
function renderClips(){
  const parent=$('clip-results');if(!parent||!state.job)return;parent.replaceChildren();
  for(const clip of state.job.clips||[]){
    const row=node('div',undefined,'clip-result');row.append(node('strong',clip.name),node('small',fmt(clip.start)+' – '+fmt(clip.end)+' · '+(clip.mode==='copy'?'极速无损':'精准导出')+' · '+({queued:'排队中',running:'正在导出',done:'已完成',error:'失败'}[clip.status]||clip.status)));
    if(clip.status==='done'){
      const download=node('a','下载 MP4','button-link');download.href=assetUrl(clip.name);download.download=clip.name;
      const locate=node('button','打开文件位置','text-button');locate.onclick=async()=>{try{await api('/jobs/'+state.job.id+'/clips/'+clip.id+'/open-location',{});}catch(e){toast(e.message);}};
      row.append(download,locate);
    }else if(clip.status==='error')row.append(node('p',clip.error||'导出失败','error'));
    parent.append(row);
  }
}
function openClipDialog(){
  const duration=Number(state.job?.duration)||0;
  if(!duration)return toast('无法读取视频时长，暂不能截取。');
  for(const id of ['clip-start','clip-end']){$(id).max=duration;}
  const preview=$('clip-preview-player');const source=state.job.local_video_available?'/api/jobs/'+state.job.id+'/original':assetUrl(state.job.video_file);
  if(preview.getAttribute('src')!==source){preview.pause();preview.src=source;preview.load();}
  setClipValues(Math.max(0,Math.min($('player').currentTime||0,Math.max(0,duration-.05))),Math.min(duration,($('player').currentTime||0)+10));
  $('clip-dialog').querySelector('.muted').textContent='拖动起点或终点时，下面的视频播放器会直接定位并暂停在对应画面。原视频不会被改写；精准导出会重新编码 MP4，极速无损导出会受关键帧影响。';
  visible('clip-error',false);renderClips();$('clip-dialog').showModal();
}
async function submit(body,endpoint='/jobs'){
  $('submit').disabled=true;visible('form-error',false);
  try{const job=await api(endpoint,body);if(job.reused)toast('已找到相同任务，直接打开已有结果。');await selectJob(job.id);state.jobs=await api('/jobs');renderHistory();$('result').scrollIntoView({block:'start',behavior:'smooth'});}
  catch(e){$('form-error').textContent=e.message;visible('form-error',true);}
  finally{$('submit').disabled=false;}
}
$('job-form').onsubmit=event=>{event.preventDefault();submit({url:$('url').value,profile:$('profile').value,mode:document.querySelector('[name=mode]:checked').value,language:$('language').value||null,hotwords:$('hotwords').value,force:$('force').checked,cleanup_after:$('cleanup-after').checked});};
$('paste').onclick=async()=>{try{$('url').value=await navigator.clipboard.readText();$('url').dispatchEvent(new Event('input'));$('url').focus();}catch{toast('浏览器未允许读取剪贴板，请在输入框按 Ctrl+V。');$('url').focus();}};
$('url').oninput=()=>{const value=$('url').value;$('link-hint').textContent=/bilibili\.com|b23\.tv/i.test(value)?'已识别 Bilibili 链接':/douyin\.com/i.test(value)?'已识别抖音分享':'不用清理分享文字，直接粘贴即可';};
$('url').onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){$('job-form').requestSubmit();}};
document.querySelectorAll('[name=mode]').forEach(el=>el.onchange=()=>{$('mode-hint').textContent={transcript:'优先下载音频，本地识别，不需要 AI 密钥。',visual:'临时缓存视频以便预览和识别；完成后点击“保存视频”选择正式保存位置。',download:'仅缓存当前可访问画质的视频；完成后点击“保存视频”选择正式保存位置。'}[el.value];});
document.querySelectorAll('[data-tab]').forEach(el=>{el.onclick=()=>activate(el.dataset.tab);el.onkeydown=e=>{if(!['ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;e.preventDefault();const tabs=[...document.querySelectorAll('[data-tab]')];let n=tabs.indexOf(el);n=e.key==='Home'?0:e.key==='End'?2:(n+(e.key==='ArrowRight'?1:2))%3;activate(tabs[n].dataset.tab);tabs[n].focus();};});
$('history-search').oninput=renderHistory;$('transcript-search').oninput=()=>{if(state.job)renderSegments();};
$('new-task').onclick=startNewTask;
$('home-create').onclick=startNewTask;
document.querySelectorAll('.nav-item').forEach(button=>button.onclick=()=>button.dataset.page==='workspace'?startNewTask():showPage(button.dataset.page));
document.querySelectorAll('.category').forEach(button=>button.onclick=()=>{state.filter=button.dataset.filter;document.querySelectorAll('.category').forEach(b=>b.classList.toggle('active',b===button));renderHistory();});
$('category-toggle').onclick=()=>{const collapsed=$('category-items').hidden;visible('category-items',collapsed);$('category-toggle').setAttribute('aria-expanded',String(collapsed));$('category-toggle').querySelector('span').textContent=collapsed?'⌃':'⌄';localStorage.setItem('video.categories-collapsed',String(!collapsed));};
if(localStorage.getItem('video.categories-collapsed')==='true')$('category-toggle').click();
$('cancel').onclick=async()=>{try{state.job=await api('/jobs/'+state.job.id+'/cancel',{});render();}catch(e){toast(e.message);}};
$('retry').onclick=()=>submit({url:state.job.url,profile:state.job.profile,mode:state.job.mode,language:state.job.language||null,hotwords:state.job.hotwords||'',force:true});
$('verify-source').onclick=async()=>{
  const button=$('verify-source');button.disabled=true;
  try{const result=await api('/jobs/'+state.job.id+'/open-source',{});toast(result.message);}
  catch(e){toast(e.message);}
  finally{button.disabled=false;}
};
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText(state.job.transcript);toast('文字稿已复制。');}catch{toast('复制失败，请下载笔记或手动选中文字。');}};
$('save-video').onclick=async()=>{
  const button=$('save-video');
  if(!state.job?.video_file)return toast('此任务没有可保存的视频。');
  button.disabled=true;const original=button.textContent;button.textContent='正在打开保存窗口…';
  try{
    const result=await api('/jobs/'+state.job.id+'/save-video',{});
    toast(result.saved?'视频已保存为：'+result.name:'已取消保存，视频仍保留在应用缓存。');
  }catch(e){toast(e.message||'保存视频失败，请稍后重试。');}
  finally{button.disabled=false;button.textContent=original;}
};
$('clip-video').onclick=openClipDialog;
$('clip-start').oninput=()=>syncClipValues('start');
$('clip-end').oninput=()=>syncClipValues('end');
$('clip-start-input').onchange=()=>syncClipValues('start-input');
$('clip-end-input').onchange=()=>syncClipValues('end-input');
$('clip-set-start').onclick=()=>setClipValues($('clip-preview-player').currentTime,clipSeconds('clip-end'));
$('clip-set-end').onclick=()=>setClipValues(clipSeconds('clip-start'),$('clip-preview-player').currentTime);
$('clip-preview').onclick=async()=>{
  const start=clipSeconds('clip-start'),end=clipSeconds('clip-end');
  if(end<=start)return toast('请选择有效的起止时间。');
  const preview=$('clip-preview-player');state.clipPreviewEnd=end;preview.currentTime=start;
  try{await preview.play();}catch{toast('浏览器未能播放此视频编码，请下载后使用本地播放器预览。');}
};
$('clip-preview-player').ontimeupdate=()=>{const preview=$('clip-preview-player');if(state.clipPreviewEnd!==null&&preview.currentTime>=state.clipPreviewEnd){preview.pause();state.clipPreviewEnd=null;}};
$('clip-preview-player').onerror=()=>toast('浏览器无法预览此视频编码；仍可导出 MP4 后用本地播放器打开。');
$('clip-preview-player').onloadedmetadata=()=>seekClipPreviewFrame(Number($('clip-preview-player').dataset.frameSeek||clipSeconds('clip-start')));
$('player').onerror=()=>toast('浏览器无法播放此视频编码；可下载原视频后使用本地播放器，或尝试截取后再播放。');
$('clip-export').onclick=async()=>{
  const start=clipSeconds('clip-start'),end=clipSeconds('clip-end'),button=$('clip-export');
  visible('clip-error',false);
  if(end<=start){$('clip-error').textContent='结束时间必须大于开始时间。';visible('clip-error',true);return;}
  button.disabled=true;button.textContent='正在创建导出任务…';
  try{state.job=await api('/jobs/'+state.job.id+'/clips',{start,end,mode:$('clip-mode').value});render();toast('片段已加入导出队列。');}
  catch(e){$('clip-error').textContent=e.message;visible('clip-error',true);}
  finally{button.disabled=false;button.textContent='导出片段';}
};
$('settings-button').onclick=()=>{const h=state.health;$('health-info').replaceChildren(node('p',h?'语音识别：'+h.device+'；ffmpeg：'+(h.ffmpeg?'可用':'未安装')+'；AI：'+(h.ai_configured?h.ai_host:'未配置'):'本地服务未连接'),node('p',h?'结果目录：'+h.data_dir:''));$('settings-dialog').showModal();};
document.querySelectorAll('.close-dialog').forEach(button=>button.onclick=()=>button.closest('dialog').close());
$('summarize').onclick=()=>{if(!state.health.ai_configured){$('settings-button').click();return;}$('ai-destination').textContent='将发送到：'+state.health.ai_host;$('ai-vision').disabled=!state.job.frames.length;$('ai-vision').checked=false;$('ai-dialog').showModal();};
$('confirm-ai').onclick=async()=>{$('ai-dialog').close();try{state.job=await api('/jobs/'+state.job.id+'/summary',{vision:$('ai-vision').checked});render();}catch(e){toast(e.message);}};
async function poll(){
  try{
    if(!state.health){state.health=await api('/health');state.token=state.health.token;}
    state.jobs=await api('/jobs');renderHistory();
    const id=state.selected;
    if(id){try{const job=await api('/jobs/'+id);if(state.selected===id){state.job=job;render();}}catch(e){state.selected=null;localStorage.removeItem('video.selected');toast(e.message);}}
    $('connection').textContent='本地服务已连接';
  }catch{$('connection').textContent='连接中断，正在重连';state.health=null;}
  finally{setTimeout(poll,1400);}
}
activate('overview');showPage('home');poll();
