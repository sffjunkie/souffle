# import argparse
import base64
from collections import defaultdict
import glob
import http.server
import io
import json
import os
import pickle
from pprint import pprint
import re
import shutil
import socketserver
import urllib.parse
import zlib


__author__ = "Simon Kennedy <sffjunkie+code@gmail.com"
__version__ = "0.1"

PORT = 8000

def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()

# def parse_wheel_name(name):
#     elems = name.split("-")
#     if len(elems) == 6:
#         distribution, version, _, python_tag, abi_tag, platform_tag = elems
#     else:
#         distribution, version, python_tag, abi_tag, platform_tag = elems

#     return [name, distribution, version, python_tag, abi_tag, platform_tag]


def _b64_decode_bytes(b):
    return base64.b64decode(b.encode("ascii"))


def _b64_decode_str(s):
    return _b64_decode_bytes(s).decode("utf8")


def get_distribution_name_from_filename(filename):
    elems = filename.split("-")
    return elems[0]


class WheelHandler(http.server.BaseHTTPRequestHandler):
    def _parse_requestline(self):
        elems = self.requestline.split(" ")
        urlinfo = urllib.parse.urlsplit(elems[1])
        elems[1] = urlinfo
        return elems

    def do_GET(self):
        req_info = self._parse_requestline()
        print(req_info)
        # Re-direct to /simple/
        if req_info[1].path == "/simple":
            print("Redirect")
            self.send_response(303)
            self.send_header("Content-type", "text/html")
            self.send_header("Location", "/simple/")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()

            wheel_info = self.server.wheel_info

            # List of projects
            if req_info[1].path == "/simple/":
                head = ["<title>Simple index</title>"]
                body = []
                for dist_name in sorted(wheel_info.keys(), key=str.lower):
                    normalized_name = normalize(dist_name)
                    target = f"/simple/{normalized_name}/"
                    body.append(f"<a href=\"{target}\">{dist_name}</a> ")
                self.wfile.write(self._get_html(body, head))

            # A distribution file
            elif req_info[1].query:
                wheel_file_name = urllib.parse.unquote(req_info[1].query)
                size = os.stat(wheel_file_name).st_size
                with open(wheel_file_name, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(size))
                    self.end_headers()
                    shutil.copyfileobj(f, self.wfile)

            # Distributions for a project
            elif req_info[1].path.startswith("/simple/"):
                dist_name = req_info[1].path[8:]
                dist_name = dist_name[:-1]
                dists = wheel_info[dist_name]
                head = [f"<title>Links for {dist_name}</title>"]
                body = [f"<h1>Links for {dist_name}</h1>"]
                for dist in dists:
                    distq = urllib.parse.quote_plus(dist)
                    link_title = os.path.basename(dist)
                    body.append(f"<a href=\"/simple/{dist_name}/?{distq}\">{link_title}</a><br>")
                self.wfile.write(self._get_html(body, head))

            # About
            else:
                title = f"Souffle v{__version__}"
                body  = [
                    f"<h1>{title}</h1>",
                    "<a href=\"/simple/\">Project Listing</a>",
                    f"<p>Serving from {self.server.pip_cache_dir}</p>",
                    "<p>PyPi: <a href=\"https://pypi.org/projects/souffle\">https://pypi.org/projects/souffle</a>",
                    "<p>Source Code: <a href=\"https://github.com/sffjunkie/souffle\">https://github.com/sffjunkie/souffle</a></p>",
                    "<p>Uses code from CacheControl Copyright 2015 Eric Larson</p>",
                ]
                self.wfile.write(self._get_html(body))

    # def do_POST(self):
    #     print(self._parse_requestline())

    def _get_html(self, body, head=[]):
        data = ["<!DOCTYPE html><html>"]
        if head:
            data.append("<head>")
            data.extend(head)
            data.append("</head>")
        data.append("<body>")
        data.extend(body)
        data.append("</body></html>")
        html = "".join(data)
        html = html.encode("utf-8")
        return html


class WinWheelCacheServer(http.server.HTTPServer):
    def __init__(self, port=PORT):
        app_data = os.environ.get("LOCALAPPDATA", None)
        self.pip_cache_dir = os.path.join(app_data, "pip", "cache")
        if os.path.exists(self.pip_cache_dir):
            self.wheel_cache_dir = os.path.join(self.pip_cache_dir, "wheels")
            self.http_cache_dir = os.path.join(self.pip_cache_dir, "http")

            if os.path.exists(self.wheel_cache_dir):
                self.wheel_info = self._get_wheel_info()

            if os.path.exists(self.http_cache_dir):
                self.http_info = self._get_http_info()

        http.server.HTTPServer.__init__(self,
                                        ("", port),
                                        WheelHandler)

    def serve_forever(self, poll_interval=0.5):
        print(f"Server listening on port {PORT}...")
        super(WinWheelCacheServer, self).serve_forever()

    def _get_http_info(self):
        # ce = obj["response"]["headers"]["Content-Encoding"]
        # # https://stackoverflow.com/questions/3122145/zlib-error-error-3-while-decompressing-incorrect-header-check/22310760#22310760
        # if ce == "gzip":
        #     wbits = zlib.MAX_WBITS | 16
        # elif ce == "deflate":
        #     wbits = -zlib.MAX_WBITS
        # data = zlib.decompress(obj["response"]["body"], wbits=wbits)
        # obj["response"]["body"] = data
        info = None
        pattern = os.path.join(self.http_cache_dir, "**")
        files = glob.glob(pattern, recursive=True)
        if files:
            info = defaultdict(list)
            for f in files:
                if os.path.isfile(f):
                    file_info = self._unpack(f)
                    # filename = file_info["filename"]
                    # dist_name = get_distribution_name_from_filename(filename)
                    # info[dist_name].append(filename)
            return info
        return None

    def _get_wheel_info(self):
        info = None
        pattern = os.path.join(self.wheel_cache_dir, "**", "*.whl")
        files = glob.glob(pattern, recursive=True)
        if files:
            info = defaultdict(list)
            for f in files:
                filename = os.path.splitext(os.path.basename(f))[0]
                dist_name = get_distribution_name_from_filename(filename)
                info[dist_name].append(f)
        return info


    def _unpack(self, filename):
        with open(filename, "rb") as fp:
            sig = fp.read(5)
            ver = 0
            if sig[:3] == b"cc=":
                try:
                    ver = int(chr((sig[3])))
                except:
                    print(sig)
                    raise

                print(f"Version: {ver}")
                if ver == 0:
                    fp.seek(0, os.SEEK_SET)
                    return fp.read(-1)
                elif ver == 1:
                    response = pickle.load(fp.read(-1))
                elif ver == 2:
                    data = fp.read(-1)
                    try:
                        response = json.loads(zlib.decompress(data).decode("utf8"))
                    except:
                        return
                    response["response"]["body"] = _b64_decode_bytes(response["response"]["body"])
                    response["response"]["headers"] = dict(
                        (_b64_decode_str(k), _b64_decode_str(v))
                        for k, v in response["response"]["headers"].items()
                    )
                    response["response"]["reason"] = _b64_decode_str(response["response"]["reason"])
                    response["vary"] = dict(
                        (_b64_decode_str(k), _b64_decode_str(v) if v is not None else v)
                        for k, v in response["vary"].items()
                    )
                    # del response["response"]["body"]
                    # pprint(response)
                elif ver == 3:
                    return
                elif ver == 4:
                    pass


if __name__ == "__main__":
    httpd = WinWheelCacheServer(PORT)
    httpd.serve_forever()
