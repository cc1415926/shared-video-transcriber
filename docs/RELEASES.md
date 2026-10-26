# 安装包发布（维护者）

推送形如 `v2.3.0` 的 Git 标签，或在 GitHub Actions 手动运行 **Build and publish installers** 并填写一个已存在的标签，即会构建并发布：

- `VideoInbox-Setup-Windows-x64.exe`（内置 wx_channel v5.7.13 视频号采集器）
- `VideoInbox-Portable-Windows-x64.zip`（解压后运行 `VideoInbox.exe`）
- `VideoInbox-macOS-AppleSilicon.dmg`
- `VideoInbox-macOS-Intel.dmg`
- 每个安装包对应的 `.sha256` 校验文件

工作流会先运行单元测试，再分别在 Windows、Apple Silicon macOS 和 Intel macOS 构建。Windows 使用 PyInstaller onedir 与 Inno Setup；macOS 使用 PyInstaller `.app` 和 DMG。安装程序不会删除用户数据目录。

## 可选签名配置

机密只在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中配置，绝不放进代码库：

| 平台 | 必需机密 |
|---|---|
| Windows 签名 | `WINDOWS_CERT_PFX_BASE64`、`WINDOWS_CERT_PASSWORD` |
| macOS Developer ID 签名 | `MACOS_CERTIFICATE_P12_BASE64`、`MACOS_CERTIFICATE_PASSWORD`、`MACOS_SIGNING_IDENTITY` |
| macOS 公证 | `MACOS_NOTARY_KEY_BASE64`、`MACOS_NOTARY_KEY_ID`、`MACOS_NOTARY_ISSUER` |

未配置 macOS Developer ID 证书时，工作流仍可产生用于内部测试的 `-unsigned-test.dmg`，它不是已签名或已公证的正式安装包。配置证书但不配置公证机密时，只会产出已签名、未公证的 DMG。Windows 未配置证书时会产出未签名安装包。

首次正式发布前，应在真实 Windows 10/11、Apple Silicon 和 Intel macOS 设备安装并验收；GitHub Actions 的构建成功不等同于真实设备验收。

Windows 便携 ZIP 与安装版都不包含用户数据、AI 密钥、Whisper 模型或 FFmpeg。正式 Windows 安装版会内置经 SHA-256 固定校验的 `wx_channel` v5.7.13；它只在用户从收件箱明确启动并确认 Windows 管理员授权后运行。便携 ZIP 不内置采集器，用户可以自行安装后在其私有配置文件中设置 `WX_CHANNEL_HOME`。普通转录会在首次选择识别档位时下载模型；完整媒体处理依赖用户自行安装的 FFmpeg。
