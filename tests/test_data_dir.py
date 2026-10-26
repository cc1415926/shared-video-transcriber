"""缓存目录设置：迁移必须「先复制、校验、再切配置」，失败保留原目录。"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_paths


class DataDirTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.settings = base / 'settings' / 'bootstrap.json'
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.source = base / 'old'
        self.target = base / 'new'
        self.source.mkdir()
        (self.source / 'library.sqlite3').write_bytes(b'sqlite')
        (self.source / 'jobs').mkdir()
        (self.source / 'jobs' / 'clip.mp4').write_bytes(b'x' * 1024)
        (self.source / '.instance.lock').write_bytes(b'0')
        patcher = patch.object(runtime_paths, 'bootstrap_file', return_value=self.settings)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_settings(self, payload):
        self.settings.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')

    def test_migration_copies_media_skips_lock_and_switches_root(self):
        self.write_settings({'pending_migration': {'from': str(self.source), 'to': str(self.target)},
                             'data_dir': str(self.source)})
        report = runtime_paths.run_pending_migration()
        self.assertTrue(report['ok'], report)
        self.assertEqual(report['bytes'], 1024 + len(b'sqlite'))
        self.assertTrue((self.target / 'library.sqlite3').is_file())
        self.assertTrue((self.target / 'jobs' / 'clip.mp4').is_file())
        self.assertFalse((self.target / '.instance.lock').exists(), '实例锁不应被复制')
        settings = json.loads(self.settings.read_text(encoding='utf-8'))
        self.assertEqual(settings['data_dir'], str(self.target.resolve()))
        self.assertNotIn('pending_migration', settings)
        # 源目录必须保留，用户确认新位置能用后再自己删。
        self.assertTrue((self.source / 'jobs' / 'clip.mp4').is_file())

    def test_failed_migration_keeps_original_directory(self):
        self.write_settings({'pending_migration': {'from': str(self.source), 'to': str(self.target)},
                             'data_dir': str(self.source)})
        with patch.object(runtime_paths, '_copy_tree', side_effect=OSError('磁盘已满')):
            report = runtime_paths.run_pending_migration()
        self.assertFalse(report['ok'])
        self.assertIn('磁盘已满', report['error'])
        settings = json.loads(self.settings.read_text(encoding='utf-8'))
        self.assertNotIn('data_dir', settings, '迁移失败时不能把配置指向半成品目录')
        self.assertNotIn('pending_migration', settings)

    def test_missing_source_reports_failure_instead_of_crashing(self):
        self.write_settings({'pending_migration': {'from': str(self.source / 'gone'), 'to': str(self.target)}})
        report = runtime_paths.run_pending_migration()
        self.assertFalse(report['ok'])
        self.assertIn('源目录不存在', report['error'])

    def test_configured_directory_wins_over_legacy_checkout_data(self):
        custom = Path(self.temp.name) / 'custom'
        custom.mkdir()
        self.write_settings({'data_dir': str(custom)})
        with patch.object(runtime_paths, 'resource_dir', return_value=Path(self.temp.name) / 'app'), \
                patch.dict(os.environ, {'VIDEO_DATA_DIR': ''}):
            self.assertEqual(runtime_paths.user_data_dir(), custom.resolve())

    def test_unreachable_configured_directory_falls_back_to_default(self):
        self.write_settings({'data_dir': str(Path(self.temp.name) / 'unplugged-drive' / 'data')})
        fallback = Path(self.temp.name) / 'fallback'
        fallback.mkdir()
        with patch.object(runtime_paths, 'resource_dir', return_value=Path(self.temp.name) / 'app'), \
                patch.object(runtime_paths, 'default_data_dir', return_value=fallback), \
                patch.dict(os.environ, {'VIDEO_DATA_DIR': ''}):
            # GitHub's Windows runner may spell the same temporary directory
            # with a DOS 8.3 short path. Compare filesystem identity, not text.
            self.assertTrue(os.path.samefile(runtime_paths.user_data_dir(), fallback))


if __name__ == '__main__':
    unittest.main()
