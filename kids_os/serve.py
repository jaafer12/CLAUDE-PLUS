"""يبني «نجوم» في ملف واحد ثم يشغّله من حاسوب على نفس شبكة الواي فاي.

    python3 serve.py

ثم افتح العنوان الذي يظهر من Safari على الآيباد.
"""
import http.server
import os
import socket
import socketserver
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build  # noqa: E402

PORT = 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = dict(http.server.SimpleHTTPRequestHandler.extensions_map, **{".appcache": "text/cache-manifest"})

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=build.DIST, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    build.make_quran()
    build.bundle()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        print("افتح هذا العنوان في Safari على الآيباد:")
        print("    http://%s:%d/" % (lan_ip(), PORT))
        print("للإيقاف: Ctrl+C")
        httpd.serve_forever()
