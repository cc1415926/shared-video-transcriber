"""Start the local video inbox. No frontend build tools required."""
import json
import os
import socket
import sys
import threading
import urllib.request
import webbrowser
import time
from pathlib import Path
from configuration import load_settings
from runtime_paths import prepare_runtime, user_data_dir

# 无窗口启动（pythonw / 开机自启）时 stdout/stderr 是 None，
# 底部两行带 flush=True 的提示会直接 AttributeError，服务起不来。
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')  # noqa: SIM115
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')  # noqa: SIM115

load_settings()

import uvicorn
from webapp import app


def find_existing():
    root = user_data_dir()
    explicit = os.environ.get('VIDEO_PORT') or os.environ.get('GRADIO_SERVER_PORT')
    ports = list(dict.fromkeys(([int(explicit)] if explicit else []) + list(range(7860, 7880))))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for port in ports:
        url = f'http://127.0.0.1:{port}'
        try:
            with opener.open(url + '/api/health', timeout=.3) as response:
                health = json.loads(response.read(16384))
            if health.get('service') == 'video-inbox' and Path(health['data_dir']).resolve() == root:
                return url
        except (OSError, ValueError, KeyError):
            continue
    return None


def choose_port():
    explicit = os.environ.get('VIDEO_PORT') or os.environ.get('GRADIO_SERVER_PORT')
    if explicit:
        port = int(explicit)
        if not 1 <= port <= 65535:
            raise ValueError('端口必须在 1–65535 之间')
        return port
    for port in range(7860, 7880):
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError('7860–7879 端口均被占用，请设置 VIDEO_PORT')


def open_when_ready(url, timeout=45):
    """Open the page only after this instance answers its health endpoint."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with opener.open(url + '/api/health', timeout=.5) as response:
                health = json.loads(response.read(16384))
            if health.get('service') == 'video-inbox':
                webbrowser.open(url)
                return
        except (OSError, ValueError):
            time.sleep(.25)


if __name__ == '__main__':
    prepare_runtime()
    existing = find_existing()
    if existing:
        print(f'视频收件箱已经在运行：{existing}', flush=True)
        if os.environ.get('VIDEO_OPEN_BROWSER', '1') == '1':
            webbrowser.open(existing)
        raise SystemExit(0)
    port = choose_port()
    url = f'http://127.0.0.1:{port}'
    print(f'\n视频收件箱：{url}\n关闭此程序会停止服务。任务记录保存在本地。\n', flush=True)
    if os.environ.get('VIDEO_OPEN_BROWSER', '1') == '1':
        thread = threading.Thread(target=open_when_ready, args=(url,), daemon=True)
        thread.start()
    uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning')
