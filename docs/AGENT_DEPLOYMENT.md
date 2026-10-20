# 交给 AI Agent 部署

把仓库地址和下面这段话交给 Codex、Claude Code 或 WorkBuddy 即可：

> 克隆此仓库，先阅读 `AGENTS.md`，然后在仓库根目录执行对应平台的部署命令。不要删除现有数据、不要关闭 TLS 校验、不要配置公网访问。部署完成后执行环境检查并启动本地服务，报告实际本地 URL 和未满足的可选依赖。

Windows PowerShell：

```powershell
.\scripts\deploy.ps1 -Start
```

macOS Terminal：

```bash
bash scripts/deploy.sh --start
```

脚本会固定安装 `requirements.lock` 中的依赖到项目 `.venv`，并复用 uv、Python 下载缓存、已有 Chrome/Edge/Chromium 和已有 FFmpeg。首次缺少 Python 3.12 时，uv 会在自己的缓存目录中获取兼容解释器；缺少 uv 时，脚本通过当前用户的 Python 安装固定版本的 uv，不要求管理员权限。

## 按需组件与恢复

| 项目 | 默认行为 | 需要时 |
|---|---|---|
| Playwright Chromium | 先查本机 Chrome/Edge 和已有 Playwright 缓存；都没有才下载 | 本地文件工作可加 `-SkipBrowser` / `--skip-browser` |
| FFmpeg | 只检测，不会默认改动系统 | Windows：`-InstallFfmpeg`；macOS：`--install-ffmpeg`（需要 Homebrew） |
| faster-whisper 模型 | 不在部署时下载 | 用户首次在页面选择识别档位时自动按需下载 |

失败时直接重跑同一条命令即可。脚本不会删除 `.venv`；若它已损坏，会要求先手动改名备份后再重建。绝不要为解决安装问题删除 `.data`、平台数据目录、模型缓存或媒体文件。

只检查环境、不启动：

```powershell
.\scripts\deploy.ps1 -CheckOnly
```

```bash
bash scripts/deploy.sh --check
```

## MCP 配置

先启动网页服务，再把 `server.py` 配入 Agent。使用绝对路径，不要提交 `.env`：

```json
{
  "mcpServers": {
    "video-inbox": {
      "command": "C:\\absolute\\path\\to\\shared-video-transcriber\\.venv\\Scripts\\python.exe",
      "args": ["C:\\absolute\\path\\to\\shared-video-transcriber\\server.py"]
    }
  }
}
```

macOS 将 `command` 改为 `/absolute/path/to/shared-video-transcriber/.venv/bin/python`，`args` 使用同目录下 `server.py` 的绝对路径。MCP 沿用仓库现有工具；它桥接正在运行的本地收件箱，默认只访问 `127.0.0.1`。

## 已验证与待验证

- Windows：脚本语法、锁文件解析、现有项目环境检查已在 Windows 上验证。
- macOS：脚本按 macOS 路径、Homebrew 与系统浏览器逻辑编写，但当前没有 macOS 实机，尚未完成真实安装、浏览器下载和模型下载验收。
- 站点登录、验证码、会员内容和平台反爬不属于部署成功标准，仍可能影响个别链接采集。
