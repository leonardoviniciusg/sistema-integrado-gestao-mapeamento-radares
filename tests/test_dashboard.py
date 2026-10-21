import io
import queue
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pandas as pd

from dashboard_v1 import app as dashboard


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = dashboard.app.test_client()

    def test_process_exit_status_is_reported(self):
        for code, event in [(0, '[PROCESSO FINALIZADO]'), (1, '[PROCESSO FALHOU]')]:
            with self.subTest(code=code):
                proc = Mock(stdout=io.StringIO('Log de execução\n'))
                proc.wait.return_value = code
                subscriber = queue.Queue()
                with patch.object(dashboard, 'log_subscribers', [subscriber]), \
                     patch.object(dashboard, 'is_running', True), \
                     patch.object(dashboard, 'ultimo_status_msg', ''):
                    dashboard.stream_process_output(proc)
                    self.assertFalse(dashboard.is_running)
                    self.assertEqual(subscriber.get(), 'Log de execução\n')
                    self.assertEqual(subscriber.get().strip(), dashboard.ultimo_status_msg)
                    self.assertEqual(subscriber.get().strip(), event)
                    self.assertEqual('sucesso' in dashboard.ultimo_status_msg, code == 0)

    def test_data_keeps_instruments_without_coordinates_and_validity_today(self):
        today = datetime.now()
        instruments = pd.DataFrame([
            {'NumeroSerie': 'A', 'latitude': -23.0, 'longitude': -46.0, 'Faixas': 2,
             'DataValidade': (today - timedelta(days=1)).strftime('%d/%m/%Y')},
            {'NumeroSerie': 'B', 'latitude': None, 'longitude': None, 'Faixas': None,
             'DataValidade': today.strftime('%d/%m/%Y')},
            {'NumeroSerie': 'C', 'latitude': -23.0, 'longitude': None, 'Faixas': 0,
             'DataValidade': (today + timedelta(days=91)).strftime('%d/%m/%Y')},
        ])
        for column, value in {
            'DataUltimaVerificacao': '01/01/2026', 'Proprietario.Nome': 'Empresa',
            'Municipio': 'TAUBATÉ', 'tipo_local': 'Urbano', 'UltimoResultado': 'Aprovado',
            'metodo_geocodificacao': 'GOOGLE_ROOFTOP', 'LocalVerificacao': 'Rua A',
        }.items():
            instruments[column] = value
        control = pd.DataFrame([{'Parametro': 'Status', 'Valor': 'Atualizado'}])
        with patch.object(dashboard.os.path, 'exists', return_value=True), \
             patch.object(dashboard.pd, 'read_excel', side_effect=[control, instruments]):
            response = self.client.get('/api/dados')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['radares']), 3)
        self.assertIsNone(data['radares'][1]['lat'])
        self.assertIsNone(data['radares'][2]['lat'])
        self.assertEqual(data['radares'][1]['faixas'], 0)
        self.assertEqual(data['kpis_base'], {
            'total': 3, 'vencidos': 1, 'a_vencer': 1, 'vigentes': 1, 'faixas': 2,
        })


if __name__ == '__main__':
    unittest.main()
