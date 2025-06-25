import json
import threading
import http.client
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.app import SimpleHandler, HTTPServer


def start_server():
    httpd = HTTPServer(('localhost', 0), SimpleHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()
    return httpd


def stop_server(httpd):
    httpd.shutdown()
    httpd.server_close()


def test_chat_returns_json():
    httpd = start_server()
    port = httpd.server_address[1]

    conn = http.client.HTTPConnection('localhost', port)
    conn.request('GET', '/chat')
    resp = conn.getresponse()
    body = resp.read()

    assert resp.status == 200
    assert resp.getheader('Content-Type') == 'application/json'
    # Ensure response body is valid JSON
    data = json.loads(body.decode())
    assert 'message' in data

    conn.close()
    stop_server(httpd)
