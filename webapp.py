import asyncio
import io
import logging
import os
import secrets
import shutil
import webbrowser
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from library import Library
from local_media import pick_file, pick_directory, original_path
from restart import schedule_restart
from runtime_paths import (data_dir_state, default_data_dir, executable, prepare_runtime,
                           read_bootstrap, resource_dir, user_data_dir, write_bootstrap)
from version import __version__

BASE = resource_dir()


def transport_errors(loop, context):
    # Windows reports a normal browser disconnect again during socket shutdown.
    error = context.get('exception')
    if (isinstance(error, ConnectionResetError) and getattr(error, 'winerror', None) == 10054
            and '_ProactorBasePipeTransport._call_connection_lost' in context.get('message', '')):
        logging.getLogger(__name__).debug('Browser connection closed during Windows transport shutdown')
        return
    loop.default_exception_handler(context)


@asynccontextmanager
async def lifespan(app):
    prepare_runtime()
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(transport_errors)
    app.state.token = secrets.token_urlsafe(32)
    app.state.library = Library(user_data_dir())
    try:
        yield
    finally:
        app.state.library.close()
        loop.set_exception_handler(previous_handler)


app = FastAPI(title='视频收件箱 API', version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', '[::1]', 'testserver'])


@app.middleware('http')
async def local_guard(request: Request, call_next):
    origin = request.headers.get('origin')
    if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
        return JSONResponse({'detail': '不允许跨站访问本地视频资料'}, status_code=403)
    if request.headers.get('sec-fetch-site') == 'cross-site':
        return JSONResponse({'detail': '不允许跨站访问'}, status_code=403)
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        if request.headers.get('x-video-token') != getattr(request.app.state, 'token', None):
            return JSONResponse({'detail': '页面连接已更新，请刷新后重试'}, status_code=403)
        if int(request.headers.get('content-length', '0')) > 32768:
            return JSONResponse({'detail': '请求太大'}, status_code=413)
        body = await request.body()
        if len(body) > 32768:
            return JSONResponse({'detail': '请求太大'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; media-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    elif request.url.path == '/' or request.url.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-cache'
    return response


class JobInput(BaseModel):
    url: str = Field(min_length=1, max_length=8000)
    profile: Literal['fast', 'balanced', 'accurate'] = 'balanced'
    mode: Literal['transcript', 'visual', 'download'] = 'transcript'
    language: Literal['zh', 'en', 'ja', 'ko'] | None = None
    hotwords: str = Field(default='', max_length=500)
    force: bool = False
    cleanup_after: bool = False


class RerecognizeInput(BaseModel):
    profile: Literal['fast','balanced','accurate'] = 'balanced'
    language: Literal['zh','en','ja','ko'] | None = None
    hotwords: str = Field(default='',max_length=500)


class LocalJobInput(BaseModel):
    path: str = Field(min_length=1,max_length=4096)
    profile: Literal['fast','balanced','accurate'] = 'balanced'
    mode: Literal['transcript','visual'] = 'visual'
    language: Literal['zh','en','ja','ko'] | None = None
    hotwords: str = Field(default='',max_length=500)
    force: bool = False
    cleanup_after: bool = False
    reference_url: str = Field(default='',max_length=2000)
    context_notes: str = Field(default='',max_length=8000)


class SegmentChange(BaseModel):
    index: int = Field(ge=0)
    text: str = Field(min_length=1,max_length=4000)


class EditInput(BaseModel):
    revision: int = Field(ge=0)
    changes: list[SegmentChange] = Field(min_length=1,max_length=200)


class SpokenScriptInput(BaseModel):
    text: str = Field(min_length=1, max_length=50000)


class CleanupInput(BaseModel):
    ids: list[str] = Field(min_length=1,max_length=200)
    scope: Literal['intermediates','media','all_media'] = 'media'


class CleanupCommit(BaseModel):
    token: str = Field(pattern=r'^[a-f0-9]{32}$')


class SummaryInput(BaseModel):
    vision: bool = False


class RewriteInput(BaseModel):
    product: str = Field(default='', max_length=1000)
    audience: str = Field(default='', max_length=1000)
    core_point: str = Field(default='', max_length=2000)
    duration: str = Field(default='', max_length=100)
    requirements: str = Field(default='', max_length=4000)


class ClipInput(BaseModel):
    start: float = Field(ge=0, le=86400)
    end: float = Field(gt=0, le=86400)
    mode: Literal['precise', 'copy'] = 'precise'


@app.exception_handler(KeyError)
async def missing(request, exc):
    return JSONResponse({'detail': '任务或文件不存在'}, status_code=404)


@app.exception_handler(ValueError)
async def invalid(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=400)


@app.get('/api/health')
def health(request: Request):
    base=os.environ.get('VIDEO_AI_BASE_URL','')
    parsed=urlparse(base)
    configured = bool(base and os.environ.get('VIDEO_AI_MODEL') and (os.environ.get('VIDEO_AI_API_KEY') or parsed.hostname in {'localhost','127.0.0.1','::1'}))
    return {'status': 'ok', 'service': 'video-inbox', 'version': __version__, 'token': request.app.state.token,
            'ffmpeg': bool(executable('ffmpeg')), 'ai_configured': configured,
            'ai_host': parsed.hostname if configured else None,
            'device': os.environ.get('VIDEO_WHISPER_DEVICE', 'cpu'),
            'data_dir': str(request.app.state.library.root)}


@app.get('/api/jobs')
def jobs(request: Request):
    return request.app.state.library.list()


@app.get('/api/diagnostics')
def environment_report():
    from diagnostics import collect
    return collect()


@app.post('/api/jobs', status_code=202)
def create_job(body: JobInput, request: Request):
    return request.app.state.library.submit(**body.model_dump())


@app.get('/api/jobs/{jid}')
def get_job(jid: str, request: Request):
    return request.app.state.library.get(jid)


@app.post('/api/local/pick')
def choose_local_file():
    return pick_file()


@app.post('/api/local/pick-directory')
def choose_local_directory():
    return pick_directory()


@app.post('/api/local/jobs',status_code=202)
def create_local_job(body: LocalJobInput, request: Request):
    return request.app.state.library.submit_local(**body.model_dump())


@app.get('/api/jobs/{jid}/original')
def original_video(jid: str, request: Request):
    library=request.app.state.library
    job=library.get(jid)
    path=original_path(job)
    if not path:
        raise HTTPException(404,'本地原文件已移动、删除或修改，请重新选择文件')
    return FileResponse(path)


@app.post('/api/jobs/{jid}/cancel')
def cancel_job(jid: str, request: Request):
    return request.app.state.library.cancel(jid)


@app.post('/api/jobs/{jid}/open-source')
def open_source_for_verification(jid: str, request: Request):
    """Open only this job's original public URL in the user's default browser.

    This is intentionally an explicit, user-clicked escape hatch for a platform
    login or CAPTCHA; it never exports cookies or tries to complete verification.
    """
    job = request.app.state.library.get(jid)
    if job.get('platform') not in {'douyin', 'youtube', 'tiktok'}:
        raise ValueError('只有登录或验证失败的抖音、YouTube、TikTok 任务可以打开原视频')
    parsed = urlparse(job.get('url') or '')
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        raise ValueError('此任务没有可在浏览器打开的原始链接')
    if not webbrowser.open(job['url'], new=2):
        raise ValueError('无法打开默认浏览器，请手动复制原始链接')
    return {'opened': True, 'message': '已在默认浏览器打开原视频。请自行完成登录或验证后下载文件，再使用“电脑里的视频”导入。'}


@app.post('/api/jobs/{jid}/summary', status_code=202)
def summarize(jid: str, body: SummaryInput, request: Request):
    return request.app.state.library.summarize(jid, body.vision)


@app.post('/api/jobs/{jid}/rewrite', status_code=202)
def rewrite(jid: str, body: RewriteInput, request: Request):
    return request.app.state.library.rewrite(jid, body.model_dump())


@app.post('/api/jobs/{jid}/rewrite-script')
def save_rewrite(jid: str, body: SpokenScriptInput, request: Request):
    return request.app.state.library.save_rewrite(jid, body.text)


@app.get('/api/jobs/{jid}/assets/{name}')
def asset(jid: str, name: str, request: Request):
    path = request.app.state.library.asset(jid, name)
    inline = path.suffix.lower() in {'.jpg', '.png', '.mp4', '.webm', '.flac', '.m4a', '.wav'}
    return FileResponse(path, filename=None if inline else name)


@app.get('/api/jobs/{jid}/source')
def source_audio(jid: str, request: Request):
    library = request.app.state.library
    library.get(jid)
    path = library.source_path(jid)
    if not path:
        raise HTTPException(404,'原音视频已清理，请重新下载后复听')
    return FileResponse(path)


@app.post('/api/jobs/{jid}/save-video')
def save_video(jid: str, request: Request):
    return request.app.state.library.save_video(jid)


@app.post('/api/jobs/{jid}/clips', status_code=202)
def export_clip(jid: str, body: ClipInput, request: Request):
    return request.app.state.library.export_clip(jid, **body.model_dump())


@app.post('/api/jobs/{jid}/clips/{clip_id}/open-location')
def open_clip_location(jid: str, clip_id: str, request: Request):
    return request.app.state.library.open_clip_location(jid, clip_id)


@app.get('/api/jobs/{jid}/handoff')
def handoff(jid: str, request: Request, format: Literal['ai','plain','timestamps','summary']='ai',
            max_chars: int=Query(default=8000,ge=2000,le=20000)):
    return request.app.state.library.handoff(jid,format,max_chars)


@app.post('/api/jobs/{jid}/storyboard')
def storyboard(jid: str, request: Request):
    name = request.app.state.library.storyboard(jid)
    return {'name':name,'url':f'/api/jobs/{jid}/assets/{name}'}


@app.post('/api/jobs/{jid}/recognize',status_code=202)
def rerecognize(jid: str, body: RerecognizeInput, request: Request):
    return request.app.state.library.rerecognize(jid,**body.model_dump())


@app.post('/api/jobs/{jid}/edit')
def edit(jid: str, body: EditInput, request: Request):
    return request.app.state.library.edit_segments(jid,body.revision,[s.model_dump() for s in body.changes])


@app.post('/api/jobs/{jid}/delete')
def delete_job(jid: str, request: Request):
    return request.app.state.library.delete_job(jid)


@app.post('/api/jobs/{jid}/spoken-script')
def save_spoken_script(jid: str, body: SpokenScriptInput, request: Request):
    return request.app.state.library.save_spoken_script(jid, body.text)


@app.get('/api/storage')
def storage(request: Request):
    return request.app.state.library.storage_stats()


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for item in path.rglob('*'):
            try:
                if item.is_file() and not item.is_symlink():
                    total += item.stat().st_size
            except OSError:
                continue
    except OSError:
        return total
    return total


def _validate_data_dir(raw: str, library) -> dict:
    """只做校验，不落盘。迁移与预览共用同一套规则。"""
    text = (raw or '').strip().strip('"')
    if not text:
        raise HTTPException(400, '请先选择一个新的文件夹')
    target = Path(text).expanduser()
    if not target.is_absolute():
        raise HTTPException(400, '请提供完整的绝对路径')
    try:
        target = target.resolve()
    except OSError as exc:
        raise HTTPException(400, f'这个路径不可用：{exc}') from exc
    current = Path(library.root).resolve()
    if target == current:
        raise HTTPException(400, '新位置和当前位置是同一个文件夹')
    if target.is_file():
        raise HTTPException(400, '这个路径是个文件，请选择文件夹')
    if target.is_relative_to(current) or current.is_relative_to(target):
        raise HTTPException(400, '新位置不能和当前缓存目录互相嵌套')
    if target.is_relative_to(Path(BASE).resolve()):
        raise HTTPException(400, '不能把缓存放进程序目录，程序更新时会覆盖它')
    busy = [jid for jid in library.jobs if library.busy(jid)]
    if busy:
        raise HTTPException(409, f'还有 {len(busy)} 个任务在处理，等它们结束再搬')
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / '.video-inbox-write-test'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink()
    except OSError as exc:
        raise HTTPException(400, f'这个文件夹不可写：{exc}') from exc
    source_bytes = _dir_size(current)
    free = shutil.disk_usage(target).free
    needed = int(source_bytes * 1.05) + 209715200
    if free < needed:
        raise HTTPException(400, f'目标磁盘空间不够：需要约 {needed / 1048576:.0f} MB，可用 {free / 1048576:.0f} MB')
    return {'target': target, 'source': current, 'source_bytes': source_bytes,
            'free_bytes': free, 'needed_bytes': needed}


class DataDirInput(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


@app.get('/api/settings/data-dir')
def data_dir_info(request: Request):
    state = data_dir_state()
    state['bytes'] = _dir_size(Path(state['data_dir']))
    last = read_bootstrap().get('last_migration')
    state['last_migration'] = last if isinstance(last, dict) else None
    return state


@app.post('/api/settings/pick-directory')
def pick_data_dir():
    return pick_directory('选择视频收件箱的文件存放位置')


@app.post('/api/settings/data-dir/preview')
def preview_data_dir(body: DataDirInput, request: Request):
    info = _validate_data_dir(body.path, request.app.state.library)
    return {'target': str(info['target']), 'source': str(info['source']),
            'source_bytes': info['source_bytes'], 'free_bytes': info['free_bytes'],
            'needed_bytes': info['needed_bytes']}


@app.post('/api/settings/data-dir')
def set_data_dir(body: DataDirInput, request: Request):
    """记录迁移意图并重启；真正的复制发生在下次启动的最早期。

    复制放在重启之后是因为：数据库和媒体文件此时全被旧进程占用，
    带着连接复制只会得到一份坏库。先退出再复制，失败也不会丢原目录。
    """
    info = _validate_data_dir(body.path, request.app.state.library)
    settings = read_bootstrap()
    settings['pending_migration'] = {'from': str(info['source']), 'to': str(info['target'])}
    write_bootstrap(settings)
    schedule_restart()
    return {'restart': True, 'target': str(info['target']), 'bytes': info['source_bytes'],
            'message': f'正在把 {info["source_bytes"] / 1048576:.0f} MB 缓存搬到新位置，服务会自动重启'}


@app.post('/api/settings/data-dir/reset')
def reset_data_dir(request: Request):
    """只切回默认位置，不移动任何文件。"""
    settings = read_bootstrap()
    settings.pop('data_dir', None)
    settings.pop('pending_migration', None)
    write_bootstrap(settings)
    schedule_restart()
    return {'restart': True, 'target': str(default_data_dir()),
            'message': '已切回默认位置，只切换读取路径，不会移动已有文件'}


@app.post('/api/settings/restart')
def restart_service():
    schedule_restart()
    return {'restart': True, 'message': '服务正在重启'}


@app.post('/api/storage/preview')
def preview(body: CleanupInput, request: Request):
    return request.app.state.library.cleanup_preview(body.ids,body.scope)


@app.post('/api/storage/cleanup')
def cleanup(body: CleanupCommit, request: Request):
    return request.app.state.library.cleanup_commit(body.token)


@app.get('/api/jobs/{jid}/bundle')
def bundle(jid: str, request: Request):
    library = request.app.state.library
    job = library.get(jid)
    if job['status'] != 'done':
        raise HTTPException(409, '请等任务完成后再导出')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in job['assets']:
            if Path(name).suffix.lower() in {'.mp4','.webm','.mkv','.m4a','.mp3','.wav','.flac','.ogg'}:
                continue
            archive.write(library.asset(jid, name), name)
    return Response(stream.getvalue(), media_type='application/zip',
                    headers={'Content-Disposition': f'attachment; filename="video-notes-{jid[:8]}.zip"'})


@app.get('/')
def index():
    return FileResponse(BASE / 'static' / 'index.html')


@app.get('/docs')
def api_docs():
    return FileResponse(BASE / 'static' / 'api.html')


app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')
