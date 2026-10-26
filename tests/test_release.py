import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from configuration import load_settings
from bootstrap import requirements_hash, setup_lock
from diagnostics import collect
from scripts.package_source import validate_files


class ReleaseTests(unittest.TestCase):
    def test_agent_deployment_files_use_locked_dependencies_without_security_bypass(self):
        root=Path(__file__).resolve().parents[1]
        for name in ('AGENTS.md','requirements.lock','scripts/deploy.ps1','scripts/deploy.sh','docs/AGENT_DEPLOYMENT.md'):
            self.assertTrue((root/name).is_file(),name)
        windows=(root/'scripts/deploy.ps1').read_text(encoding='utf-8')
        macos=(root/'scripts/deploy.sh').read_text(encoding='utf-8')
        lock=(root/'requirements.lock').read_text(encoding='utf-8')
        self.assertIn('uv pip install',windows)
        self.assertIn('requirements.lock',windows)
        self.assertIn('requirements.lock',macos)
        self.assertNotIn('ExecutionPolicy Bypass',windows)
        self.assertNotIn('--trusted-host',windows+macos)
        self.assertIn('pywin32==312 ; sys_platform == \'win32\'',lock)

    def test_powershell_scripts_with_non_ascii_keep_utf8_bom(self):
        # Windows PowerShell 5.1 在文件没有 BOM 时按系统 ANSI（简体中文为 GBK）解码 .ps1，
        # 中文提示会变成乱码并破坏引号配对，脚本直接语法报错、启动器一闪而过。
        root=Path(__file__).resolve().parents[1]
        skipped={'.venv','build','dist','node_modules','.git'}
        for path in sorted(root.rglob('*.ps1')):
            if skipped & set(path.relative_to(root).parts):
                continue
            data=path.read_bytes()
            if all(byte < 0x80 for byte in data):
                continue
            self.assertTrue(data.startswith(b'\xef\xbb\xbf'),f'{path.relative_to(root)} 含非 ASCII 字符但缺少 UTF-8 BOM')

    def test_env_file_preserves_explicit_environment_and_literal_values(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'VIDEO_AI_API_KEY':'existing'}):
            (Path(root)/'.env').write_text('VIDEO_AI_API_KEY=from-file\nVIDEO_RELEASE_TEST=literal$dollar\n',encoding='utf-8')
            try:
                load_settings(root)
                self.assertEqual(os.environ['VIDEO_AI_API_KEY'],'existing')
                self.assertEqual(os.environ['VIDEO_RELEASE_TEST'],'literal$dollar')
            finally:os.environ.pop('VIDEO_RELEASE_TEST',None)

    def test_dependency_marker_tracks_constraints_as_well_as_requirements(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            (root/'requirements.txt').write_text('demo>=1')
            (root/'constraints.txt').write_text('demo==1')
            before=requirements_hash(root)
            (root/'constraints.txt').write_text('demo==2')
            self.assertNotEqual(before,requirements_hash(root))

    def test_setup_lock_excludes_second_launcher(self):
        with tempfile.TemporaryDirectory() as root:
            with setup_lock(Path(root)):
                with self.assertRaises(RuntimeError):
                    with setup_lock(Path(root)):pass

    def test_removed_platform_has_no_code_or_dependency_references(self):
        root=Path(__file__).resolve().parents[1]
        excluded={'.git','.venv','.data','__pycache__','build','dist','generated'}
        needles=('wechat_'+'channels','wx-'+'downloader','wx_'+'downloader',
                 'channels_'+'collector','weixin.qq.com/'+'sph')
        hits=[]
        for path in root.rglob('*'):
            if path.resolve() == Path(__file__).resolve():
                continue
            if not path.is_file() or excluded & set(path.relative_to(root).parts):
                continue
            if path.suffix.lower() not in {'.py','.js','.html','.css','.md','.txt','.lock','.ps1','.vbs','.bat','.sh'}:
                continue
            text=path.read_text(encoding='utf-8-sig',errors='ignore').lower()
            if any(needle in text for needle in needles):
                hits.append(str(path.relative_to(root)))
        self.assertEqual(hits,[])

    def test_windows_desktop_launcher_waits_for_actual_healthy_port(self):
        root=Path(__file__).resolve().parents[1]
        launcher=(root/'scripts/open_app.vbs').read_text(encoding='utf-8-sig')
        self.assertIn('For port = 7860 To 7879',launcher)
        self.assertIn('/api/health',launcher)
        self.assertIn('launcher.py',launcher)
        self.assertIn('launcher.log',launcher)
        self.assertNotIn('WScript.Sleep 9000',launcher)

    def test_packager_preserves_runtime_rejected_ca_policy(self):
        root=Path(__file__).resolve().parents[1]
        script=(root/'scripts/build_package.py').read_text(encoding='utf-8')
        self.assertIn('codex-rejected-cas.pem',script)
        self.assertIn("command += ['--add-data'",script)

    def test_private_files_cannot_enter_source_package(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            (root/'app.py').write_text('pass')
            self.assertEqual(validate_files(root,['app.py']),[root/'app.py'])
            for name in ['.env','.env.local','.data/result.json','clip.mp4','private.key','REFACTOR_REPORT.md','../outside.py']:
                with self.subTest(name=name),self.assertRaises(ValueError):validate_files(root,[name])

    def test_diagnostics_never_reports_credentials_urls_or_paths(self):
        with patch.dict(os.environ,{'VIDEO_AI_API_KEY':'secret-diagnostic-sentinel',
                                   'VIDEO_AI_BASE_URL':'https://private-host.invalid/v1',
                                   'VIDEO_AI_MODEL':'private-model',
                                   'VIDEO_DATA_DIR':str(Path(tempfile.gettempdir())/'private-folder-sentinel')}):
            text=json.dumps(collect())
            for value in ['secret-diagnostic-sentinel','private-host','private-model','private-folder-sentinel']:
                self.assertNotIn(value,text)


if __name__=='__main__':unittest.main()
