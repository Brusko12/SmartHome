import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from launcher.main import probe


@pytest.fixture
def local_server():
    class Handler(BaseHTTPRequestHandler):
        status = 200

        def do_GET(self):
            self.send_response(self.status)
            self.send_header("X-SmartHome", "SmartHome")
            self.send_header("X-SmartHome-Instance", "test-instance")
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {"port": server.server_port, "instance_id": "test-instance"}, Handler
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_loopback_probe_is_independent_of_https_configuration(local_server, monkeypatch):
    def unavailable_context(*_args, **_kwargs):
        raise FileNotFoundError("Unavailable system TLS configuration")

    monkeypatch.setattr(ssl, "create_default_context", unavailable_context)
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    instance, _ = local_server
    assert probe(instance, require_healthy=True)
    assert not probe({**instance, "instance_id": "another-instance"})


def test_existing_degraded_instance_is_reused_but_not_ready(local_server):
    instance, handler = local_server
    handler.status = 503
    assert probe(instance)
    assert not probe(instance, require_healthy=True)


def test_probe_rejects_invalid_metadata():
    assert not probe({})
    assert not probe({"port": "8000", "instance_id": "test"})
    assert not probe({"port": 80, "instance_id": "test"})
