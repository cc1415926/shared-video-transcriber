'use strict';

let wxChannelLoading=false;
let wxChannelInitialized=false;
let wxChannelKnown=new Set();

function wxSize(bytes){return (bytes/1048576).toFixed(bytes>=10485760?1:2)+' MB';}
function wxTime(seconds){return new Date(seconds*1000).toLocaleString('zh-CN',{hour12:false});}
function wxNode(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}

async function refreshWxChannelStatus(){
  const button=$('start-wx-channel');
  try{
    const data=await api('/wx-channel/status');
    if(data.running){button.textContent='视频号下载已启动';button.disabled=false;}
    else if(data.executable_found){button.textContent='启动视频号下载功能';button.disabled=false;}
    else{button.textContent='未找到视频号下载器';button.disabled=true;}
    return data;
  }catch(error){button.textContent='无法检查下载器';button.disabled=true;throw error;}
}

async function loadWxChannelFiles(options={}){
  if(wxChannelLoading)return;
  wxChannelLoading=true;
  const status=$('wx-channel-status'), target=$('wx-channel-files'), refresh=$('refresh-wx-channel');
  if(options.announce!==false)status.textContent='正在同步视频号采集器的本地下载目录…';
  refresh.disabled=true;
  try{
    const [service,data]=await Promise.all([refreshWxChannelStatus(),api('/wx-channel/files')]);
    target.replaceChildren();
    if(!data.available){status.textContent=data.bundled&&data.executable_found?'视频号采集器已随安装包就绪。点击“启动视频号下载功能”，首次启动会创建下载目录并请求管理员确认。':data.downloads_configured?'尚未找到已配置的视频号下载目录。请检查 WX_CHANNEL_HOME 配置后重试。':'尚未配置视频号采集器。请按使用指南设置 WX_CHANNEL_HOME，然后重新启动视频收件箱。';return;}
    const current=new Set(data.items.map(item=>item.relative_path));
    const added=[...current].filter(path=>!wxChannelKnown.has(path));
    if(wxChannelInitialized&&added.length)toast(`已采集 ${added.length} 条新视频到视频号收件箱。`);
    wxChannelKnown=current;wxChannelInitialized=true;
    const running=service.running?'下载器已启动':'下载器未启动';
    const removed=data.removed_count?` · 已移出 ${data.removed_count} 条` : '';
    status.textContent=data.items.length?`${running} · 已同步 ${data.items.length} 条完成视频${removed}。新下载内容会自动出现。`:`${running} · 暂无可处理的已完成视频${removed}。下载完成后会自动出现。`;
    if(!data.items.length){target.append(wxNode('div','在微信视频号里点击下载后，等待下载完成，视频会自动进入这里。','wx-channel-empty'));return;}
    for(const item of data.items){
      const row=wxNode('article',undefined,'wx-channel-file');
      const info=wxNode('div',undefined,'wx-channel-info');
      const badge=wxNode('span','已采集','wx-source-badge');
      info.append(badge,wxNode('strong',item.title),wxNode('small',`${item.author} · ${item.quality} · ${wxSize(item.size)} · ${wxTime(item.modified)}`));
      const actions=wxNode('div',undefined,'wx-channel-actions');
      const process=wxNode('button','开始处理  ↗','secondary wx-process-button');process.type='button';process.onclick=()=>importWxChannelFile(item,process);
      const remove=wxNode('button','删除下载文件','text-button wx-delete-button');remove.type='button';remove.onclick=()=>removeWxChannelFile(item,remove);
      actions.append(process,remove);row.append(info,actions);target.append(row);
    }
  }catch(error){status.textContent='读取失败：'+error.message;}
  finally{refresh.disabled=false;wxChannelLoading=false;}
}

async function startWxChannel(){
  const button=$('start-wx-channel');button.disabled=true;button.textContent='正在启动…';
  try{
    const data=await api('/wx-channel/start',{});
    toast(data.message);
    window.setTimeout(()=>loadWxChannelFiles({announce:false}),900);
  }catch(error){toast(error.message);await refreshWxChannelStatus().catch(()=>{});}
}

async function removeWxChannelFile(item,button){
  if(!window.confirm('将永久删除这条视频的原始下载文件，并从视频号收件箱移除，无法恢复。确定删除吗？'))return;
  button.disabled=true;button.textContent='正在删除…';
  try{const data=await api('/wx-channel/remove',{relative_path:item.relative_path});toast(data.message);await loadWxChannelFiles({announce:false});}
  catch(error){button.disabled=false;button.textContent='删除下载文件';toast(error.message);}
}

async function importWxChannelFile(item,button){
  button.disabled=true;button.textContent='正在开始…';
  try{
    const body={relative_path:item.relative_path,profile:$('profile').value,mode:document.querySelector('[name=mode]:checked').value,language:$('language').value||null,hotwords:$('hotwords').value,force:$('force').checked,cleanup_after:$('cleanup-after').checked};
    const job=await api('/wx-channel/import',body);
    state.selected=job.id;localStorage.setItem('video.selected',job.id);showPage('workspace');await selectJob(job.id);$('result').scrollIntoView({block:'start',behavior:'smooth'});toast(job.reused?'已打开已有的视频号任务。':'已开始处理视频号视频。');
  }catch(error){button.disabled=false;button.textContent='开始处理';toast(error.message);}
}

$('refresh-wx-channel').onclick=()=>loadWxChannelFiles();
$('start-wx-channel').onclick=startWxChannel;
window.setInterval(()=>{if(!$('wx-channel-input').hidden)loadWxChannelFiles({announce:false});},3000);
