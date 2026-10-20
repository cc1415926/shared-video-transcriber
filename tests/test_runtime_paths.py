import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_paths


class RuntimePathTests(unittest.TestCase):
    def test_explicit_data_directory_owns_all_mutable_caches(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'VIDEO_DATA_DIR': root}, clear=False):
            for name in ('HF_HOME', 'PLAYWRIGHT_BROWSERS_PATH'):
                os.environ.pop(name, None)
            paths = runtime_paths.prepare_runtime()
            base = Path(root).resolve()
            self.assertEqual(paths['root'], base)
            self.assertTrue(paths['logs'].is_dir())
            self.assertTrue(paths['models'].is_dir())
            self.assertTrue(paths['playwright'].is_dir())
            self.assertTrue(Path(os.environ['HF_HOME']).is_relative_to(base))
            self.assertTrue(Path(os.environ['PLAYWRIGHT_BROWSERS_PATH']).is_relative_to(base))

    def test_bundled_tool_takes_precedence_over_path_lookup(self):
        with patch.object(runtime_paths, 'bundled_executable', return_value=Path('C:/bundle/bin/ffmpeg.exe')):
            self.assertEqual(Path(runtime_paths.executable('ffmpeg')), Path('C:/bundle/bin/ffmpeg.exe'))

    def test_resource_directory_contains_static_ui_in_source_mode(self):
        self.assertTrue((runtime_paths.resource_dir() / 'static' / 'index.html').is_file())

    def test_explicit_data_directory_overrides_legacy_checkout_data(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'VIDEO_DATA_DIR': root}, clear=False):
            self.assertEqual(runtime_paths.user_data_dir(), Path(root).resolve())
