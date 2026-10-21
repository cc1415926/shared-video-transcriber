"""In-place restart helper.

目录迁移必须先让旧进程退出：SQLite 与缓存文件都还在被占用时复制没有意义。
这里先起一个脱离父进程的新实例，再让当前进程立刻退出，端口会在毫秒级释放，
新实例仍然能抢到同一个端口。
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

from runtime_paths import resource_dir


def _spawn() -> None:
    root = resource_dir()
    flags = 0
    if os.name == 'nt':
        flags = getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    env = dict(os.environ)
    env['VIDEO_OPEN_BROWSER'] = '0'
    try:
        subprocess.Popen(
            [sys.executable, str(root / 'app.py')],
            cwd=str(root),
            env=env,
            creationflags=flags,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        # 立刻退出，让监听端口马上释放给新实例。
        os._exit(0)


def schedule_restart(delay: float = 1.5) -> None:
    """返回响应之后再重启，避免前端拿到连接重置。"""
    timer = threading.Timer(delay, _spawn)
    timer.daemon = True
    timer.start()
