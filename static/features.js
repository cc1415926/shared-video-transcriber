'use strict';
const feature={packet:null,part:0,copyJob:null,edit:null,cleanup:null,storage:[],storageJob:null,deleteJob:null};
async function clipboard(text){
  try{await navigator.clipboard.writeText(text);return true;}catch{}
  // Legacy clipboard fallback; only runs on an explicit user action.
  const field=node('textarea');field.value=text;field.className='clipboard-fallback';document.body.append(field);
  const focus=document.activeElement;field.select();let ok=false;try{ok=document.execCommand('copy');}catch{}field.remove();focus?.focus();return ok;
}
function renderEnhancements(){
  const j=state.job;const count=j.segments.filter(s=>s.needs_review).length;
  visible('reference-note-panel',!!j.context_notes);$('reference-note-text').textContent=j.context_notes||'';
  $('review-status').textContent=(j.recognition_version?count+' 段建议复核（不是准确率）':'旧版结果未评估疑似错词')+(j.revision?' / 已修订 '+j.revision+' 次':'')+(j.media_cleaned?' / 音视频已清理':'');
  $('recognize-again').disabled=j.status!=='done'||j.summary_status==='running';
  $('clean-job').disabled=!terminal.has(j.status)||j.summary_status==='running';
  $('delete-job').disabled=!terminal.has(j.status)||j.summary_status==='running';
  $('copy-options').disabled=!j.transcript&&!j.summary;
  const audio=$('audio-player');visible('audio-player',!!j.media_available);
  if(j.media_available){const src='/api/jobs/'+j.id+'/source';if(audio.getAttribute('src')!==src)audio.src=src;}else{audio.pause();audio.removeAttribute('src');}
  if(j.summary_stale){$('overview-title').textContent='这份摘要需要更新';$('overview-subtitle').textContent='文字稿已经修正，下面仍是旧摘要。请重新生成后再使用。';}
  if(j.media_cleaned)$('visual-note').textContent='音视频已清理，已保留的截图仍可阅读；需要回看时请从来源重新下载。';
  if(j.local_source){
    $('visual-note').textContent=j.local_video_available?'直接回看本地原视频；抽样截图可能遗漏内容。清理只影响应用缓存，不删除原文件。':'本地原文件已移动、删除或修改。已有文字、截图和保留的音轨仍可使用。';
    if(j.cache_cleaned)$('review-status').textContent+=' / 应用缓存已清理，原文件未改动';
  }
  $('rewrite-script').value=j.rewrite_script||'';
  const request=j.rewrite_request||{};
  for(const [id,key] of [['rewrite-product','product'],['rewrite-audience','audience'],['rewrite-point','core_point'],['rewrite-duration','duration'],['rewrite-requirements','requirements']]){
    if(document.activeElement!==$(id))$(id).value=request[key]||'';
  }
  $('rewrite-status').textContent=j.rewrite_status==='running'?'AI 正在生成原创口播稿…':j.rewrite_error||'';
  $('generate-rewrite').disabled=j.status!=='done'||j.rewrite_status==='running';
  $('copy-rewrite').disabled=!(j.rewrite_script||'').trim();
  visible('rewrite-download',!!j.rewrite_script);$('rewrite-download').href=assetUrl('rewrite-script.txt');$('rewrite-download').download='AI原创口播稿.txt';
}
$('review-only').onchange=renderSegments;
$('generate-rewrite').onclick=async()=>{
  if(!state.health?.ai_configured){$('settings-button').click();return;}
  $('generate-rewrite').disabled=true;
  try{state.job=await api('/jobs/'+state.job.id+'/rewrite',{product:$('rewrite-product').value,audience:$('rewrite-audience').value,core_point:$('rewrite-point').value,duration:$('rewrite-duration').value,requirements:$('rewrite-requirements').value});state.lastRender='';render();}catch(e){toast(e.message);$('generate-rewrite').disabled=false;}
};
$('copy-rewrite').onclick=async()=>{if(await clipboard($('rewrite-script').value))toast('AI 改写稿已复制。');else{$('rewrite-script').select();toast('请按 Ctrl+C 复制。');}};
$('save-rewrite').onclick=async()=>{try{state.job=await api('/jobs/'+state.job.id+'/rewrite-script',{text:$('rewrite-script').value});state.lastRender='';render();toast('改写稿已保存；原始逐字稿未改动。');}catch(e){toast(e.message);}};
function currentSpokenScript(){return state.job.spoken_script||state.job.transcript||'';}
async function copySpokenScript(){
  const text=$('spoken-script-dialog').open?$('spoken-script-text').value:currentSpokenScript();
  if(!text.trim())return toast('还没有可复制的口播稿。');
  if(await clipboard(text))toast('纯文本口播稿已复制，可直接粘贴到剪映或文生音频工具。');
  else{ $('spoken-script-text').value=text;$('spoken-script-dialog').showModal();$('spoken-script-text').select();toast('浏览器未允许自动复制，请按 Ctrl+C。'); }
}
$('edit-spoken-script').onclick=()=>{
  if(!state.job.transcript)return toast('文字稿尚未完成。');
  $('spoken-script-text').value=currentSpokenScript();visible('spoken-script-error',false);$('spoken-script-dialog').showModal();
};
$('copy-spoken-script').onclick=copySpokenScript;
$('copy-spoken-script-dialog').onclick=copySpokenScript;
$('save-spoken-script').onclick=async()=>{
  $('save-spoken-script').disabled=true;visible('spoken-script-error',false);
  try{
    const job=await api('/jobs/'+state.job.id+'/spoken-script',{text:$('spoken-script-text').value});
    state.job=job;state.lastRender='';render();$('spoken-script-dialog').close();toast('人工口播稿已保存；原始逐字稿未改动。');
  }catch(e){$('spoken-script-error').textContent=e.message;visible('spoken-script-error',true);}
  finally{$('save-spoken-script').disabled=false;}
};
async function loadPacket(){
  feature.packet=await api('/jobs/'+feature.copyJob+'/handoff?format='+$('copy-format').value+'&max_chars='+$('copy-limit').value);
  feature.part=0;showPacket();
}
function showPacket(){
  const p=feature.packet;if(!p)return;
  $('copy-preview').value=p.parts.length>1?p.parts[feature.part]:p.text;
  $('copy-info').textContent=p.characters.toLocaleString()+' 字符 / '+p.parts.length+' 段'+(p.partial?' / 当前任务未完成，资料不完整':'');
  $('copy-page').textContent='第 '+(feature.part+1)+' / '+p.parts.length+' 段';
  $('copy-prev').disabled=feature.part===0;$('copy-next').disabled=feature.part>=p.parts.length-1;
  $('copy-part').textContent='复制第 '+(feature.part+1)+' 段';
  $('copy-picture').disabled=!p.frame_count;
}
async function openCopy(){
  feature.copyJob=state.job.id;$('copy-format').value='ai';visible('picture-download',false);
  try{await loadPacket();$('copy-dialog').showModal();}catch(e){toast(e.message);}
}
$('copy').onclick=async()=>{
  try{
    feature.copyJob=state.job.id;
    const p=await api('/jobs/'+feature.copyJob+'/handoff');
    if(p.characters>12000){await openCopy();toast('内容较长，可以整份复制或按顺序分段粘贴。');return;}
    if(await clipboard(p.text))toast('完整视频资料已复制，可直接粘贴给其他 AI。');
    else{await openCopy();$('copy-preview').select();toast('浏览器未允许自动复制，请按 Ctrl+C。');}
  }catch(e){toast(e.message);}
};
$('copy-options').onclick=openCopy;
$('copy-format').onchange=$('copy-limit').onchange=()=>loadPacket().catch(e=>toast(e.message));
$('copy-prev').onclick=()=>{feature.part=Math.max(0,feature.part-1);showPacket();};
$('copy-next').onclick=()=>{feature.part=Math.min(feature.packet.parts.length-1,feature.part+1);showPacket();};
async function copyPacket(whole){const text=whole?feature.packet.text:feature.packet.parts[feature.part];if(await clipboard(text))toast(whole?'全部内容已复制。':'第 '+(feature.part+1)+' 段已复制。');else{$('copy-preview').value=text;$('copy-preview').select();toast('请按 Ctrl+C 复制已选中的内容。');}}
$('copy-full').onclick=()=>copyPacket(true);$('copy-part').onclick=()=>copyPacket(false);
$('copy-picture').onclick=async()=>{
  $('copy-picture').disabled=true;
  try{
    const result=await api('/jobs/'+feature.copyJob+'/storyboard',{});
    $('picture-download').href=result.url;$('picture-download').download='video-storyboard.png';visible('picture-download',true);
    const response=await fetch(result.url);if(!response.ok)throw Error('读取画面失败');
    const blob=await response.blob();
    if(!window.ClipboardItem)throw Error('这个浏览器不支持复制图片，请点击下载拼图后上传给 AI。');
    await navigator.clipboard.write([new ClipboardItem({'image/png':blob})]);toast('画面拼图已复制，请粘贴到 AI 聊天框。');
  }catch(e){toast(e.message||'图片复制失败，可以下载拼图后上传。');}
  finally{$('copy-picture').disabled=false;}
};
function beginInlineEditor(index,row,text){
  const j=state.job,s=j.segments[index];
  if(!s)return toast('文字稿刚刚刷新，请再点击一次“核对 / 修正”。');
  document.querySelectorAll('.segment-editing').forEach(el=>el.closest('.segment')?.querySelector('.inline-cancel')?.click());
  feature.edit={id:j.id,index,revision:j.revision||0};
  row.classList.add('segment-editing');
  const input=node('textarea',undefined,'inline-segment-input');
  input.value=s.text;input.rows=2;input.maxLength=4000;input.setAttribute('aria-label','修正 '+fmt(s.start)+' 的文字');
  const actions=node('span',undefined,'inline-edit-actions');
  const cancel=node('button','×','inline-cancel');cancel.type='button';cancel.title='取消修改';cancel.setAttribute('aria-label','取消修改');
  const save=node('button','✓','inline-save');save.type='button';save.title='保存修正';save.setAttribute('aria-label','保存修正');
  const finish=async()=>{
    if(save.disabled)return;
    save.disabled=cancel.disabled=true;
    try{
      const e=feature.edit;
      const updated=await api('/jobs/'+e.id+'/edit',{revision:e.revision,changes:[{index:e.index,text:input.value}]});
      if(state.selected===e.id){state.job=updated;state.lastRender='';render();}
      toast('修正已保存；原稿和修订记录已保留。');
    }catch(error){
      save.disabled=cancel.disabled=false;toast(error.message);
    }
  };
  cancel.onclick=()=>renderSegments();save.onclick=finish;
  input.onkeydown=event=>{
    if(event.key==='Escape'){event.preventDefault();cancel.click();}
    if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){event.preventDefault();finish();}
    // Ctrl+Z / Cmd+Z intentionally uses the browser's native textarea undo stack.
  };
  text.replaceWith(input);row.querySelector('.edit-segment').replaceWith(actions);actions.append(cancel,save);
  input.focus();input.setSelectionRange(input.value.length,input.value.length);
}
$('recognize-again').onclick=()=>{
  const j=state.job;feature.redoJob=j.id;$('redo-profile').value='accurate';
  $('redo-language').value=j.language||'';$('redo-terms').value=j.hotwords||'';
  $('redo-note').textContent=j.media_available?'将复用本地音频，新结果会单独保留。':'原音视频已清理，将重新下载；来源失效时可能无法恢复。';
  $('recognize-dialog').showModal();
};
$('confirm-redo').onclick=async()=>{
  $('confirm-redo').disabled=true;
  try{
    const original=await api('/jobs/'+feature.redoJob);
    const options={profile:$('redo-profile').value,language:$('redo-language').value||null,hotwords:$('redo-terms').value};
    if(original.local_source&&!original.media_available)throw Error('原文件已移动或修改，请在「电脑里的视频」重新选择后导入。');
    const job=original.media_available?await api('/jobs/'+original.id+'/recognize',options):await api('/jobs',{url:original.url,mode:'transcript',force:true,...options});
    $('recognize-dialog').close();await selectJob(job.id);toast(original.media_available?'正在复用音频重新识别。':'已开始重新下载与识别。');
  }catch(e){toast(e.message);}finally{$('confirm-redo').disabled=false;}
};
function resetPlan(){feature.cleanup=null;visible('cleanup-preview',false);$('storage-message').textContent='';}
async function openStorage(jid=null){
  feature.storageJob=jid;resetPlan();$('storage-select-all').checked=false;
  const stats=await api('/storage');feature.storage=stats.jobs;
  $('storage-total').textContent='任务文件 '+mb(stats.total_bytes)+'，其中音视频 '+mb(stats.media_bytes)+'；磁盘剩余 '+(stats.free_bytes/1073741824).toFixed(1)+' GB';
  await loadDataDir().catch(e=>setDataDirMessage(e.message,true));
  const list=$('storage-jobs');list.replaceChildren();
  for(const job of stats.jobs){
    const label=node('label',undefined,'storage-row');const check=node('input');check.type='checkbox';check.value=job.id;check.disabled=job.busy;check.checked=!job.busy&&job.id===jid;check.onchange=resetPlan;
    const desc=node('span');desc.append(node('strong',job.title),node('small',mb(job.bytes)+(job.busy?' / 正在使用，暂不清理':' / '+labels[job.status])));
    if(job.external_source)desc.append(node('small','仅统计应用缓存；本地原文件不在清理范围内'));
    label.append(check,desc);list.append(label);
  }
  if(!$('storage-dialog').open)$('storage-dialog').showModal();
}
async function loadDataDir(){
  const info=await api('/settings/data-dir');feature.dataDir=info;
  $('data-dir-path').textContent=info.data_dir;
  $('data-dir-badge').hidden=!info.custom;
  $('reset-data-dir').hidden=!info.custom;
  const parts=['已占用 '+mb(info.bytes)];
  if(info.origin==='legacy')parts.push('当前用程序目录里的历史缓存，还没设过自定义位置');
  if(info.origin==='default')parts.push('当前是系统默认位置');
  if(info.env_override)parts.push('当前由环境变量 VIDEO_DATA_DIR 指定，界面改动会被它覆盖');
  const last=info.last_migration;
  if(last&&last.ok===false)parts.push('上次迁移失败：'+(last.error||'未知原因')+'，仍在用原目录');
  else if(last&&last.ok===true)parts.push('上次已迁移 '+mb(last.bytes||0));
  $('data-dir-meta').textContent=parts.join('；');
}
function setDataDirMessage(text,isError){
  const box=$('data-dir-message');
  box.hidden=false;box.className=isError?'path-status error':'path-status';box.textContent=text;
}
async function waitForRestart(timeout=30000){
  const started=Date.now();
  await new Promise(resolve=>setTimeout(resolve,1500));
  while(Date.now()-started<timeout){
    try{
      const response=await fetch('/api/health',{cache:'no-store'});
      if(response.ok){
        const health=await response.json();
        if(health.service==='video-inbox'){location.reload();return;}
      }
    }catch{}
    await new Promise(resolve=>setTimeout(resolve,1200));
  }
  throw Error('服务没有在预期时间内回来。请双击桌面的「视频收件箱」重新启动，再刷新本页。');
}
$('change-data-dir').onclick=async()=>{
  const button=$('change-data-dir');
  try{
    button.disabled=true;$('data-dir-message').hidden=true;
    const picked=await api('/settings/pick-directory',{});
    if(!picked.path)return;
    const preview=await api('/settings/data-dir/preview',{path:picked.path});
    const ok=confirm('把 '+mb(preview.source_bytes)+' 缓存复制到：\n'+preview.target+'\n\n目标盘剩余 '+(preview.free_bytes/1073741824).toFixed(1)+' GB。\n迁移期间服务会自动重启；原目录保留不删，确认新位置能用后你自己删。\n\n继续吗？');
    if(!ok)return;
    const result=await api('/settings/data-dir',{path:picked.path});
    setDataDirMessage(result.message+'。页面会在十几秒内自动恢复，先别关这个标签页…',false);
    await waitForRestart();
  }catch(e){setDataDirMessage(e.message,true);}
  finally{button.disabled=false;}
};
$('reset-data-dir').onclick=async()=>{
  if(!confirm('切回默认位置？\n\n只切换「读取哪个文件夹」，不会移动或删除任何文件；自定义目录里已有的缓存会留在原处。'))return;
  try{
    const result=await api('/settings/data-dir/reset',{});
    setDataDirMessage(result.message+'。页面会在十几秒内自动恢复…',false);
    await waitForRestart();
  }catch(e){setDataDirMessage(e.message,true);}
};
$('storage-button').onclick=()=>openStorage().catch(e=>toast(e.message));
$('clean-job').onclick=()=>openStorage(state.job.id).catch(e=>toast(e.message));
function openDeleteJob(id){
  feature.deleteJob=id;
  $('delete-job-dialog').showModal();
}
$('delete-job').onclick=()=>{if(state.job)openDeleteJob(state.job.id);};
$('confirm-delete-job').onclick=async()=>{
  const id=feature.deleteJob;if(!id)return;
  $('confirm-delete-job').disabled=true;
  try{
    await api('/jobs/'+id+'/delete',{});
    if(state.selected===id){state.selected=null;state.job=null;localStorage.removeItem('video.selected');}
    state.jobs=await api('/jobs');renderHistory();visible('result',false);visible('empty',false);
    feature.deleteJob=null;$('delete-job-dialog').close();toast('这条生成记录及应用缓存已删除。');
  }catch(e){toast(e.message);}
  finally{$('confirm-delete-job').disabled=false;}
};
$('storage-select-all').onchange=()=>{document.querySelectorAll('#storage-jobs input:not(:disabled)').forEach(c=>c.checked=$('storage-select-all').checked);resetPlan();};
$('cleanup-scope').onchange=resetPlan;
$('preview-cleanup').onclick=async()=>{
  try{
    const ids=[...document.querySelectorAll('#storage-jobs input:checked')].map(c=>c.value);
    if(!ids.length)throw Error('请先选择要清理的视频。');
    const p=await api('/storage/preview',{ids,scope:$('cleanup-scope').value});feature.cleanup=p;
    $('cleanup-description').textContent='将删除 '+p.files.length+' 个媒体文件，预计释放 '+mb(p.bytes)+'。'+(p.skipped.length?' '+p.skipped.length+' 个使用中的任务已跳过。':'');
    $('confirm-cleanup').disabled=!p.files.length;visible('cleanup-preview',true);
  }catch(e){$('storage-message').textContent=e.message;}
};
$('confirm-cleanup').onclick=async()=>{
  if(!feature.cleanup)return;$('confirm-cleanup').disabled=true;
  try{
    // Release this page's media handles; other consumers are checked by the backend.
    for(const id of ['player','audio-player','edit-audio']){$(id).pause();$(id).removeAttribute('src');$(id).load();}
    const result=await api('/storage/cleanup',{token:feature.cleanup.token});
    await openStorage(feature.storageJob);
    $('storage-message').textContent='已释放 '+mb(result.reclaimed_bytes)+'，保留文字和历史。'+(result.errors.length?' 部分文件正在使用或无法删除，请稍后重试。':'');
    if(state.selected)await selectJob(state.selected);
  }catch(e){$('storage-message').textContent=e.message;resetPlan();$('storage-message').textContent=e.message;}
  finally{$('confirm-cleanup').disabled=false;}
};
document.querySelectorAll('[name=mode]').forEach(input=>input.addEventListener('change',()=>{const onlyDownload=document.querySelector('[name=mode]:checked').value==='download';$('cleanup-after').disabled=onlyDownload;if(onlyDownload)$('cleanup-after').checked=false;}));
