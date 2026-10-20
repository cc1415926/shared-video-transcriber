"""Packaged application entry point for Video Inbox.

The launcher is deliberately small: it prepares user-writable runtime folders,
starts the local-only FastAPI service in this process, and leaves normal
shutdown to Uvicorn's lifecycle.  No child Python process is left behind.
"""
from __future__ import annotations

import argparse
import logging
import os
import runpy
import sys
from pathlib import Path

from runtime_paths import prepare_runtime
from version import __version__


def configure_logging() -> Path:
    log_dir = prepare_runtime()['logs']
    path = log_dir / 'launcher.log'
    logging.basicConfig(
        filename=path,
        encoding='utf-8',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Video Inbox local launcher')
    parser.add_argument('--no-browser', action='store_true', help='start local service without opening a browser')
    parser.add_argument('--diagnostics', action='store_true', help='print a sanitized local environment report')
    parser.add_argument('--mcp', action='store_true', help='run the existing MCP stdio server')
    parser.add_argument('--version', action='store_true', help='print the application version')
    options = parser.parse_args(argv)
    if options.version:
        print(__version__)
        return 0
    prepare_runtime()
    log_path = configure_logging()
    logging.info('launcher started version=%s', __version__)
    try:
        if options.diagnostics:
            from diagnostics import collect
            import json
            print(json.dumps(collect(), ensure_ascii=False, indent=2))
            return 0
        if options.mcp:
            from server import mcp
            mcp.run(transport='stdio')
            return 0
        if options.no_browser:
            os.environ['VIDEO_OPEN_BROWSER'] = '0'
        runpy.run_module('app', run_name='__main__')
        return 0
    except KeyboardInterrupt:
        logging.info('launcher stopped by user')
        return 130
    except Exception:
        logging.exception('launcher failed; log=%s', log_path)
        print(f'启动失败。可在此查看日志：{log_path}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
