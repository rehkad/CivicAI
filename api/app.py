from http.server import BaseHTTPRequestHandler, HTTPServer


class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/chat":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"message": "Hello from CivicAI chat"}')
        elif self.path == "/":
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Hello from CivicAI API!")
        else:
            self.send_error(404)


def run(server_class=HTTPServer, handler_class=SimpleHandler, host='0.0.0.0', port=8000):
    server_address = (host, port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    httpd.serve_forever()


if __name__ == '__main__':
    run()
