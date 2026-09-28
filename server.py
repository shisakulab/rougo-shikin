"""老後資金シミュレーターをこのパソコンの中だけで起動する。

既定では見本の config.example.json を読み取り専用で使う（保存しない）。
--local を付けると config.json を読み込み、画面で設定した値を config.json に保存する。"""
import argparse
import json
import os
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, urlsplit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_FILE = "老後資金シミュレーター.html"
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
EXAMPLE_FILE = os.path.join(BASE_DIR, "config.example.json")
MAX_BODY = 1_000_000


class Handler(SimpleHTTPRequestHandler):
    local = False  # True: config.json を読み書きする / False: config.example.json を読み取り専用で返す

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/" + quote(APP_FILE))
            self.end_headers()
            return
        if path == "/api/config":
            self.send_config()
            return
        super().do_GET()

    def do_PUT(self):
        if urlsplit(self.path).path != "/api/config":
            self.send_error(404)
            return
        if not self.local:
            self.send_json(403, {"error": "見本の設定で起動しているため保存しません（--local で起動すると config.json に保存します）"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            self.send_json(400, {"error": "送られてきたデータの大きさが不正です"})
            return
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.send_json(400, {"error": "JSONとして読めません"})
            return
        if not isinstance(data, dict) or not isinstance(data.get("params"), dict):
            self.send_json(400, {"error": "params がありません"})
            return
        if not isinstance(data.get("presets", []), list):
            self.send_json(400, {"error": "presets は一覧（配列）である必要があります"})
            return
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, CONFIG_FILE)
        self.send_json(200, {"ok": True})

    def send_config(self):
        path = CONFIG_FILE if self.local else EXAMPLE_FILE
        name = os.path.basename(path)
        headers = {} if self.local else {"X-Config-Readonly": "1"}
        if not os.path.exists(path):
            self.send_json(404, {"error": f"{name} がまだありません"}, headers)
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except ValueError as e:
            self.send_json(500, {"error": f"{name} の書式が正しくありません（{e}）"}, headers)
            return
        self.send_json(200, data, headers)

    def send_json(self, status, obj, headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # HTMLを直したときにすぐ反映されるよう、キャッシュさせない
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="老後資金シミュレーターを起動します")
    parser.add_argument("--port", type=int, default=8765, help="使うポート番号（既定: 8765）")
    parser.add_argument("--no-browser", action="store_true", help="ブラウザを自動で開かない")
    parser.add_argument("--local", action="store_true",
                        help="config.json を読み込み、画面の変更を保存する（付けないと config.example.json を読み取り専用で使う）")
    args = parser.parse_args()
    Handler.local = args.local
    url = f"http://127.0.0.1:{args.port}/"

    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        print(f"ポート {args.port} は使用中です。すでに起動している場合はブラウザで {url} を開いてください。")
        print("別のアプリが使っている場合は、python server.py --port 8766 のように番号を変えて起動してください。")
        if not args.no_browser:
            webbrowser.open(url)
        sys.exit(1)

    print("老後資金シミュレーターを起動しました")
    print(f"  画面:     {url}")
    if args.local:
        print(f"  設定保存: {CONFIG_FILE}")
    else:
        print(f"  設定:     {EXAMPLE_FILE}（見本・読み取り専用。保存するには --local を付けて起動）")
    print("終了するには、このウィンドウを閉じるか Ctrl+C を押してください。")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
