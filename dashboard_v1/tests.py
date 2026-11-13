"""Verificações HTTP sem executar o pipeline ou alterar a base."""
import json
from unittest import mock
from django.test import Client, override_settings, SimpleTestCase
from dashboard_v1 import views

@override_settings(ALLOWED_HOSTS=['testserver', '172.27.152.41'])
class DashboardTests(SimpleTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_page_and_csrf(self):
        response = self.client.get('/', HTTP_HOST='172.27.152.41:5000')
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', response.cookies)
        self.assertEqual(self.client.post('/api/executar').status_code, 403)
        self.assertEqual(self.client.get('/api/executar').status_code, 405)

    def test_missing_data(self):
        with mock.patch.object(views.os.path, 'exists', return_value=False):
            self.assertEqual(self.client.get('/api/dados').status_code, 404)

    def test_report_with_csrf(self):
        self.client.get('/')
        token = self.client.cookies['csrftoken'].value
        with mock.patch.object(views.os.path, 'exists', return_value=True):
            response = self.client.post('/api/relatorio/tabela_filtrada',
                data=json.dumps({'itens': [{'serie': '123', 'municipio': 'Taubaté'}]}),
                content_type='application/json', HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 200)
            self.assertIn('Taubaté', b''.join(response.streaming_content).decode('utf-8-sig'))
            response.close()
            response = self.client.post('/api/relatorio/tabela_filtrada', data='{',
                content_type='application/json', HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 400)

    def test_stream_cleanup(self):
        response = self.client.get('/api/logs/stream')
        self.assertEqual(response.status_code, 200)
        views.log_subscribers[-1].put('teste')
        self.assertIn(b'data: teste', next(iter(response.streaming_content)))
        response.close()
        self.assertEqual(views.log_subscribers, [])

