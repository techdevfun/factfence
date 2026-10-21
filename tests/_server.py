"""Local HTTP server helper for network tests (no outside traffic)."""

import functools
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def start_server(directory):
    """Serve *directory* on 127.0.0.1 with an ephemeral port.

    Returns (server, port). Caller must call server.shutdown().
    """
    handler = functools.partial(_QuietHandler, directory=str(directory))
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]
