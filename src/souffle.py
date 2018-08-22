import argparse
from collections import defaultdict
import glob
import http.server
import io
import os
import re
import shutil
import socketserver
import urllib.parse


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
                head = [f"Links for {dist_name}"]
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
                    "<p>PyPi: <a href=\"https://pypi.org/projects/souffle\">https://pypi.org/projects/souffle</a>",
                    "<p>Source Code: <a href=\"https://github.com/sffjunkie/souffle\">https://github.com/sffjunkie/souffle</a></p>"
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
        self.output = None
        self.wheel_cache_dir = None
        self.wheel_info = self._get_wheel_info()
        http.server.HTTPServer.__init__(self,
                                        ("", port),
                                        WheelHandler)

    def _get_wheel_info(self):
        info = None
        app_data = os.environ.get("LOCALAPPDATA", None)
        if app_data:
            self.wheel_cache_dir = os.path.join(app_data, "pip", "cache", "wheels")
            pattern = os.path.join(self.wheel_cache_dir, "**")
            files = glob.glob(pattern, recursive=True)
            if files:
                info = defaultdict(list)
                for f in files:
                    if f.endswith(".whl"):
                        filename = os.path.splitext(os.path.basename(f))[0]
                        dist_name = get_distribution_name_from_filename(filename)
                        info[dist_name].append(f)
        return info


if __name__ == "__main__":
    print(f"Server listening on port {PORT}...")
    httpd = WinWheelCacheServer(PORT)
    httpd.serve_forever()
