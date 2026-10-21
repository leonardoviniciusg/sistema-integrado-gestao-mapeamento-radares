import os
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch


class ConfigTests(unittest.TestCase):
    def test_onedrive_is_optional_and_configurable(self):
        config_path = Path(__file__).resolve().parents[1] / 'config.py'
        for value in ['', '   ', str(config_path.parent / 'destino_teste')]:
            with self.subTest(value=value), \
                 patch.dict(os.environ, {'ONEDRIVE_DIR': value}), \
                 patch('dotenv.load_dotenv'):
                config = runpy.run_path(str(config_path))
                expected = Path(value) / 'medidores_processados.xlsx' if value.strip() else None
                self.assertEqual(config['ONEDRIVE_EXCEL'], expected)
                self.assertEqual(config['ONEDRIVE_EXCEL_FIXO'], expected)
