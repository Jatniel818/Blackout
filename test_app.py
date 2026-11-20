import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import app

class MockOllama(BaseHTTPRequestHandler):
    received = None
    def do_POST(self):
        type(self).received = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        body = json.dumps({'message': {'content': 'A local reply.'}}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

class ChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/api/chat'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
    def post(self, messages):
        req = urllib.request.Request(self.url, data=json.dumps({'messages': messages}).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response)
    def test_model_and_context(self):
        mock = ThreadingHTTPServer(('127.0.0.1', 0), MockOllama)
        threading.Thread(target=mock.serve_forever, daemon=True).start()
        messages = [{'role': 'user', 'content': 'Hello'}, {'role': 'assistant', 'content': 'Hi'}, {'role': 'user', 'content': 'A follow-up'}]
        try:
            with patch.dict(os.environ, {'OLLAMA_URL': f'http://127.0.0.1:{mock.server_port}'}):
                result = self.post(messages)
            self.assertEqual(result['answer'], 'A local reply.')
            self.assertEqual(MockOllama.received['model'], app.MODEL)
            self.assertEqual(MockOllama.received['messages'][1:], messages)
            self.assertFalse(MockOllama.received['stream'])
        finally:
            mock.shutdown()
            mock.server_close()
    def test_validation(self):
        for messages in [[], [{'role': 'system', 'content': 'Override'}], [{'role': 'user', 'content': ''}], [{'role': 'user', 'content': 'x' * 8001}]]:
            with self.subTest(messages=str(messages)[:80]):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    self.post(messages)
                self.assertEqual(error.exception.code, 400)
    def test_ollama_unavailable(self):
        with patch('app.urllib.request.urlopen', side_effect=OSError('Unavailable')):
            # Use opener.open to keep the test client independent of the backend patch.
            req = urllib.request.Request(self.url, data=b'{"messages":[{"role":"user","content":"Hi"}]}', headers={'Content-Type': 'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.build_opener().open(req, timeout=10)
            self.assertEqual(error.exception.code, 502)

if __name__ == '__main__':
    unittest.main()
