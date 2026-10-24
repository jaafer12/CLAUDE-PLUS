"""خادم صغير لتشغيل «نجوم» من حاسوب على نفس شبكة الواي فاي.

    python3 serve.py

ثم افتح العنوان الذي يظهر من متصفح Safari في الآيباد.
يرسل ملف nujoom.appcache بالنوع الصحيح ويضع فيه بصمة الملفات،
فيحدّث الآيباد نسخته المخزّنة تلقائياً كلما تغيّر شيء.
"""
import hashlib
import http.server
import os
import socket
import socketserver

PORT = 8000
ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = "nujoom.appcache"


def manifest_bytes():
    with open(os.path.join(ROOT, MANIFEST), encoding="utf-8") as f:
        text = f.read()
    h = hashlib.sha1()
    for line in text.splitlines():
        p = os.path.join(ROOT, line.strip())
        if line.strip() and not line.startswith(("#", "CACHE", "NETWORK", "*")) and os.path.isfile(p):
            with open(p, "rb") as g:
                h.update(g.read())
    return text.replace("# version: dev", "# version: " + h.hexdigest()[:12]).encode("utf-8")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0].lstrip("/") == MANIFEST:
            body = manifest_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/cache-manifest")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


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
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        print("افتح هذا العنوان في Safari على الآيباد:")
        print("    http://%s:%d/" % (lan_ip(), PORT))
        print("للإيقاف: Ctrl+C")
        httpd.serve_forever()
