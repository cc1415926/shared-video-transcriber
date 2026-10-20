# 视频收件箱

粘贴抖音、Bilibili、YouTube 或 TikTok 的公开分享链接，下载 MP4 或 MP3，并转成文字稿、字幕、摘要和截图——可以快速阅读、回看和交给 AI 的资料。也支持本地视频和音频文件。

这是一个本地优先的个人应用。新版使用独立网页 + FastAPI，替换了原先的 Gradio 界面，保留旧 MCP 工具。

## 让 Agent 一键部署（推荐）

将仓库地址交给 Codex、Claude Code 或 WorkBuddy，并让它先读 [AGENTS.md](AGENTS.md)。Agent 在仓库根目录只需执行一条命令：

| 你的电脑 | 部署并启动 |
|---|---|
| Windows 10 / 11，64 位 | `.\scripts\deploy.ps1 -Start` |
| macOS Apple Silicon / Intel | `bash scripts/deploy.sh --start` |

脚本使用固定版本的 `uv` 与 [requirements.lock](requirements.lock) 建立项目专属 `.venv`，复用已有 Python/uv 缓存、Chrome/Edge/Chromium 和 FFmpeg。缺少浏览器时才下载 Playwright Chromium；faster-whisper 模型不在安装时下载，而在首次选用识别档位时按需下载。服务只监听本机 `127.0.0.1`，启动后终端会显示实际地址（通常为 http://127.0.0.1:7860）。

完整提示词、失败恢复、可选 FFmpeg、环境自检和 MCP 配置见 [Agent 部署说明](docs/AGENT_DEPLOYMENT.md)。也可下载 [源码 ZIP](https://github.com/ZY-ZhichaoYu/shared-video-transcriber/archive/refs/heads/main.zip) 后完整解压再执行同一命令；不需要 Git 或 AI key。

旧的 `run_web.bat` / `run_web.ps1` / `run_web.sh` 仍保留，已转发到同一部署流程。遇到问题可双击 **check_environment.bat**，或在网页“设置”里点击“检查运行环境”。新手说明、常见报错和安全升级方法见 [使用指南](docs/GETTING_STARTED.md)。

## 怎么用

Windows 双击 **run_web.bat**。首次会创建虚拟环境、安装依赖和 Chromium，随后自动打开浏览器。
默认 http://127.0.0.1:7860；端口占用时自动尝试 7861–7879。保持启动程序运行。

重复双击会打开同一结果目录已在运行的页面；文件锁阻止两个实例同时改写同一份任务库。

粘贴链接或整段分享文字，点击“开始处理”：

| 方式 | 得到什么 | 取舍 |
|---|---|---|
| 只读文字 | 速览原话、时间戳文字稿、SRT 字幕 | 优先下载音频，适合日常浏览 |
| 文字 + 视频 | 上述内容、原视频、最多 24 张带时间位置的抽样截图 | 下载更多数据；视频可回看；点击“保存视频”再选择正式保存位置 |
| 只下载视频 | 当前可访问画质的原视频 | 不运行语音识别 |

默认“细致”使用 small，“快速”使用 base，“精细”使用 medium。较大的模型通常更准确，但不保证每段都更好；CPU 上会更慢。
更多选项可以指定语言、填写专业名词提示、强制重新处理。

视频会保存到左侧历史。刷新网页不会停止后台任务。进度显示的是**当前阶段**：
下载按实际字节更新；总大小未知时显示活动条和已下载大小，不编造百分比。
B 站视频依次显示下载画面、下载声音、合并。转录按已识别的音频时间更新，预计剩余时间只是估计。
首次模型加载/下载与排队显示独立状态。

取消为协作式：在当前请求、合并操作或语音片段结束后停止；模型首次下载期间也可能需要等待。
关闭服务会中断任务；下次启动会把未完成记录标成“已中断”，可点击重新处理。

“导出笔记”下载 ZIP，包含 TXT、SRT、Markdown、结构化 JSON，以及视觉任务的截图。
原视频仅临时缓存用于预览和转录；点击“保存视频”后才会弹出系统路径选择窗口。ZIP 解压后 Markdown 可相对引用截图。

## 纠错、复制与清理（2.1）

文字稿会标出建议复核的片段，可筛选后点“核对 / 修正”进行原地编辑；`×` 取消、`✓` 保存，输入框支持 Ctrl+Z 撤销。
这是模型低把握、重复或静音信号的提示，不是准确率；未标记的片段也可能出错。
修订保留时间戳、首次原稿和每次修订前的完整记录；旧摘要会标记过期。
“重新精细识别”复用本地音频，新旧稿分别保留。专业词提示用于辅助识别，不做全局强制替换。
作者自造词、梗和口语应结合原音、原字幕核验，不能仅靠常识改写。

“复制给 AI”包含来源、时间戳和证据边界。“更多复制”可选纯文字、带时间戳、摘要，
也可按顺序分段复制长文，不静默截断。画面需要单独复制拼图或下载上传，文字复制不会自动附图。
含画面任务的拼图最多八张抽样截图，适合快速提供上下文，不是完整视频视觉理解。

“存储与清理”按任务展示空间占用，支持只删中间文件、删除音视频但保留截图、只留文字。
必须先预览，再确认永久删除；任务历史、文字和修订记录保留。
处理中、生成摘要或作为重识别音源的任务暂不清理。删除记录保存在本地 SQLite maintenance 表。
可在提交前勾选完成后自动清理音视频（默认关闭）；失败任务不自动删除。
清理后的音视频不能在应用内撤销，再次复听需重新下载，来源失效时可能无法恢复。

## 本地录屏、会议与音频（2.2）

切换到“电脑里的视频”，点击“选择文件”，或粘贴完整路径（Windows 资源管理器的“复制文件地址”）。
支持 MP4、MKV、MOV、WebM、AVI，以及 WAV、M4A、MP3、FLAC 等音频。
系统选择窗口不可用时，路径输入仍可使用；这指的是运行服务的电脑，不是另一台访问网页的设备。

本地原文件只读引用，不上传，也不复制整份大视频。应用只另存 16 kHz 单声道 FLAC 音轨、文字和抽样截图。
音轨准备与语音识别分别显示阶段进度。播放器支持按字节范围读取大视频。
原文件路径、大小和修改时间记录在本机数据库；原文件变动后不会悄悄播放或复用替换后的内容。
原文件移动或删除后，已经保留的文字、截图和紧凑音轨仍可使用；原视频回看需要重新选择文件。
应用缓存目录里的文件不允许作为“外部原文件”再次导入，请从历史重新识别。

可添加对应的 Bilibili/抖音链接，仅作来源记录，不再下载。可粘贴或读取 TXT 参考摘要，最多 8,000 字符，
例如 Zoom summary；它与逐字稿分开保存和显示，复制给 AI 时标明是未核验的参考材料。
导出包不包含原视频及本地绝对路径，参考材料另存 reference-notes.txt。
本地任务的清理仅删除应用缓存，原视频永远不在该清理范围内。
长会议仍需等待本机 CPU 识别；当前未做说话人分离、自动逐段语言检测或完整幻灯片 OCR。

## 视频片段截取（2.4）

在保留原视频的视频详情页点击“截取片段”，用双端点时间轴或秒数输入选择开始和结束位置；可将播放器当前时间设为任一端点，并预览选中片段，播放到终点会自动暂停。

默认“精准导出 MP4”使用本机 FFmpeg 重新编码 H.264/AAC，保留原始画幅比例与声音，不加水印；“极速无损导出”使用 stream copy，速度快但会受关键帧限制，起止时间可能不完全精确。导出文件保存在原任务历史中，不覆盖原视频，可下载、打开文件位置或从空间管理清理。

截取 API 只接受已有任务 ID 与时间范围，绝不接收任意文件路径。需要系统 PATH 中可用的 `ffmpeg`；项目不捆绑 FFmpeg。FFmpeg 的许可证取决于所安装的构建，使用或分发时请遵守该构建的许可证；本项目没有引入 LosslessCut、react-range 或 noUiSlider 的源码或依赖。

## 微信视频号已下载文件（2.3）

“微信视频号”来源用于导入你已在电脑微信页面下载完成的本地媒体文件。原文件只读引用、不上传、也不读取微信聊天记录或聊天数据库；导入前会检查文件类型、可读性以及导入期间是否仍在写入。

可填写下载器实际获得的作品 ID、标题、作者、原始发布文案、话题标签与作品链接。它们与自动语音识别的口播逐字稿分开保存、显示和导出；未获得的字段会标为“未获取”。

当前首选上游下载器的“文件传输助手自动下载”功能不可用：其当前源码的文件传输助手实例未初始化，自动创建下载任务的回调也没有接通。因此界面会明确显示“已下载文件可导入”，不表示自动转发正在连接。推荐流程是：在电脑微信视频号页面下载作品，再在本应用选择该文件导入。

## 安装

需要 64 位 Python 3.10–3.14，推荐 3.12。完整 Bilibili 视频合并需要 ffmpeg；只转录一般不需要单独安装 ffmpeg。

    git clone https://github.com/ZY-ZhichaoYu/shared-video-transcriber.git
    cd shared-video-transcriber
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    .venv\Scripts\python.exe -m playwright install chromium
    .venv\Scripts\python.exe app.py

Windows 安装 ffmpeg：

    winget install Gyan.FFmpeg

之后重新打开终端，让 PATH 生效。启动器直接使用虚拟环境 Python，不需要激活环境。
macOS/Linux 可使用对应的 .venv/bin/python 手动启动。

## 爆款结构分析与 AI 原创改写

默认不调用付费 AI，不上传文字和画面。无 AI 配置时“速览”是按时间摘取的原话，界面明确标注，不冒充语义摘要。

可以连接兼容 Chat Completions 的服务，包括本地模型。PowerShell 示例：

    $env:VIDEO_AI_BASE_URL = "https://你的服务/v1"
    $env:VIDEO_AI_MODEL = "你的模型名称"
    $env:VIDEO_AI_API_KEY = "你的密钥"
    .\.venv\Scripts\python.exe app.py

本地服务地址允许 http://127.0.0.1；云端必须 HTTPS。模型名和能力由所选服务决定，项目不预设某个付费供应商。
也可以复制项目里的 .env.example 为 .env，取消需要的配置项前的注释并填写，随后重启。
已有进程环境变量优先于 .env；配置不进行变量展开。勿把 .env、密钥、视频或会议文字发到 GitHub。

完成任务后点击“生成爆款结构分析”，会输出开头钩子、痛点、核心观点、推进结构、利益点、结尾引导和可借鉴结构；不编造平台数据。
“AI 改写”Tab 可填写产品/行业、目标客户、核心观点、时长和额外要求，生成稿可继续人工编辑、保存、复制和下载。原始逐字稿、人工口播稿与 AI 改写稿彼此独立。
界面会显示目标服务并确认发送。
逐字稿最多发送前 45,000 字符，截断时结果会注明；如附参考摘要，会另行发送最多 8,000 字符并区分来源。勾选发送画面时，最多发送 8 张抽样图，需要支持图片输入的模型。
AI 输出包括一句话内容、带时间位置的要点、建议回看的位置和适当的回复草稿。
原始文字稿保持独立，AI 失败不会丢失转录。

抽样截图不是完整视频理解。短暂字幕、快速动作和转场可能遗漏；目前没有 OCR、场景变化检测或逐帧动作分析。

## AI 调用：MCP、HTTP、Skill

新 MCP 工具与网页共享持久任务，需要先启动 app.py：

| 工具 | 用途 |
|---|---|
| inspect_shared_video(url, mode, profile) | 创建/复用任务，立即返回 id |
| get_video_job(job_id) | 查询状态、时间戳文字、画面和文件 URL；可重复读取 |
| cancel_video_job(job_id) | 请求取消 |
| inspect_local_video(path, mode, profile, language, hotwords, reference_url, context_notes) | 只读分析用户选定的本地视频或音频 |
| get_video_handoff(job_id, format, max_chars) | 完整文字资料与不丢内容的有序分段 |
| rewrite_video_script(job_id, product, audience, core_point, duration, requirements) | 明确授权后生成原创口播稿 |

mode 为 transcript / visual / download；profile 为 fast / balanced / accurate。
先创建，再每隔约 2 秒查询，直到 status 为 done / error / cancelled / interrupted。

MCP 客户端配置中的 command 应指向项目虚拟环境 Python，args 指向 server.py 的绝对路径，例如：

    {
      "mcpServers": {
        "shared-video-transcriber": {
          "command": "C:\\path\\to\\shared-video-transcriber\\.venv\\Scripts\\python.exe",
          "args": ["C:\\path\\to\\shared-video-transcriber\\server.py"]
        }
      }
    }

桥接自动寻找本机 7860–7879 的新版服务；自定义端口可设置 VIDEO_INBOX_URL。
现有 MCP 客户端需要重新连接/重启才能发现新工具。
旧版 analyze_video、video_to_text、get_transcript_result、download_video、transcribe_video 和抖音兼容名保留，可独立运行；旧工具仍使用其原有内存任务，推荐迁移到新工具。

HTTP API 文档随应用离线提供：[/docs](http://127.0.0.1:7860/docs)，机器可读 schema 在 /openapi.json。
GET /api/health 获取 token，写请求需带 X-Video-Token。支持创建、查询、取消、导出、爆款结构分析和显式 AI 改写。

可分发技能在 [skills/read-shared-video/SKILL.md](skills/read-shared-video/SKILL.md)。
把 read-shared-video 文件夹复制到所用 AI 客户端的技能目录，再配置 MCP 或使用 HTTP API。
技能指导 AI 区分语音与画面证据、按时间引用，并把视频中的指令视为外部资料。

## 数据与运行边界

- 默认仅监听 127.0.0.1，适合本机个人使用，**不要直接作为公网多用户服务部署**。
- 任务和文件保存在项目 .data 目录（已加入 .gitignore）；数据库使用 SQLite WAL。
- 相同 URL 与相同选项会复用已有任务。B 站跟踪参数会清理，分 P 参数保留；短链与长链目前不保证归并。
- 同时运行最多两个任务，语音引擎串行使用单个缓存模型；最多 20 个未结束任务，历史界面显示最近 200 条。
- 默认保留历史与媒体；可显式选择自动清理，或通过空间管理预览并删除。提交前默认至少要求 512 MB 磁盘余量，这不等于处理全过程的磁盘配额。
- 直链单文件默认上限 2 GB。yt-dlp 后备路径的资源约束还未与直链完全统一。
- HTTPS 证书校验已恢复。如企业/本地代理需要额外 CA，配置 SSL_CERT_FILE 指向可信证书；不要关闭校验。
- Cookie 导入、验证码交互、付费/会员内容、直播、图集和合集暂未实现。平台接口变化、风控、地区限制会影响获取成功率。
- 未做完整公网 SSRF 隔离；平台重定向、CDN、浏览器网络还需在部署层隔离。本机防护不等于公网安全认证。

环境变量：

| 变量 | 用途 |
|---|---|
| VIDEO_PORT | 指定本地端口；兼容旧 GRADIO_SERVER_PORT |
| VIDEO_OPEN_BROWSER=0 | 不自动打开浏览器 |
| VIDEO_DATA_DIR | 指定结果和数据库目录 |
| VIDEO_MAX_DOWNLOAD_MB | 直链单文件上限，默认 2048 |
| VIDEO_MIN_FREE_MB | 提交任务前最低磁盘余量，默认 512 |
| VIDEO_WHISPER_DEVICE | 默认 cpu；具备合适 CUDA 环境时可设 cuda |
| VIDEO_WHISPER_COMPUTE | 默认 CPU int8 / CUDA float16 |
| VIDEO_AI_BASE_URL / VIDEO_AI_MODEL / VIDEO_AI_API_KEY | 可选 AI 配置 |
| VIDEO_INBOX_URL | MCP 桥接到指定本地实例 |
| VIDEO_PYTHON | Windows 启动器使用的 Python 可执行文件完整路径（通常无需设置） |

## 验证与后续

    .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    .venv\Scripts\python.exe -m unittest discover -s tests -v
    node --check static/app.js
    node --check static/features.js

Node 仅用于可选的 JavaScript 语法检查，运行网页不需要 Node。

发布范围和仍需完成的工作见 [CHANGELOG.md](CHANGELOG.md)、[发布验收说明](docs/RELEASE_CHECKLIST.md) 与 [安装包发布说明](docs/RELEASES.md)。
部署使用 `requirements.lock` 固定 Windows/macOS 的完整 Python 依赖解析结果；修改 `requirements.txt` 或 `constraints.txt` 后，需用 `uv pip compile requirements.txt --universal -o requirements.lock` 更新并重新验证。
尚无跨视频准确率基准；一次成功不能代表平台总体成功率。

## English

A local-first video inbox for Douyin and Bilibili. Paste a shared link, read timestamped speech,
optionally retain source video and sampled frames, and export TXT/SRT/Markdown/JSON.
FastAPI serves a responsive, build-free frontend. SQLite persists jobs; the existing MCP tools remain compatible.
The new inspect_shared_video/get_video_job tools share tasks with the running app.
Optional AI summaries use an explicitly configured OpenAI-compatible endpoint, with user-confirmed transcript/image transfer.
This release targets personal local use, not public multi-tenant deployment.

MIT license. Built with [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[yt-dlp](https://github.com/yt-dlp/yt-dlp), [Playwright](https://playwright.dev/python/),
[FastAPI](https://fastapi.tiangolo.com/) and [MCP](https://github.com/modelcontextprotocol/python-sdk).
