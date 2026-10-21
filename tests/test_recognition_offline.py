"""_set_hf_offline_if_cached: 只有完整缓存的模型才切离线，防止代理 502 炸掉本地识别。"""
import os
import tempfile
import unittest
from pathlib import Path

from recognition import _set_hf_offline_if_cached


class HfOfflineTests(unittest.TestCase):
    def setUp(self):
        self._old = {k: os.environ.get(k) for k in ('HF_HOME', 'HF_HUB_OFFLINE')}
        self.hf_home = tempfile.mkdtemp(prefix='hf_offline_test_')
        os.environ['HF_HOME'] = self.hf_home
        os.environ.pop('HF_HUB_OFFLINE', None)

    def tearDown(self):
        for key, value in self._old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _make_model(self, size, with_model_bin):
        snap = Path(self.hf_home) / 'hub' / f'models--Systran--faster-whisper-{size}' / 'snapshots' / 'abc123'
        snap.mkdir(parents=True)
        if with_model_bin:
            (snap / 'model.bin').write_bytes(b'x')

    def test_complete_cache_engages_offline(self):
        self._make_model('small', with_model_bin=True)
        _set_hf_offline_if_cached('small')
        self.assertEqual(os.environ.get('HF_HUB_OFFLINE'), '1')

    def test_partial_cache_stays_online(self):
        self._make_model('small', with_model_bin=False)
        _set_hf_offline_if_cached('small')
        self.assertIsNone(os.environ.get('HF_HUB_OFFLINE'))

    def test_missing_model_stays_online(self):
        _set_hf_offline_if_cached('medium')
        self.assertIsNone(os.environ.get('HF_HUB_OFFLINE'))

    def test_explicit_setting_is_respected(self):
        os.environ['HF_HUB_OFFLINE'] = '0'
        self._make_model('small', with_model_bin=True)
        _set_hf_offline_if_cached('small')
        self.assertEqual(os.environ.get('HF_HUB_OFFLINE'), '0')


if __name__ == '__main__':
    unittest.main()
