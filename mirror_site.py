#!/usr/bin/env python3
"""Static mirror crawler for honeybee-early-learning.com.

Crawls same-site pages, rewrites internal links to relative local paths,
and downloads every referenced asset (images, css, js, fonts) regardless
of host (Squarespace serves assets from CDN subdomains), rewriting CSS
url()/@import references too. Produces a static, offline-servable copy.

Known limitation: Squarespace's contact forms, booking widgets, and any
e-commerce/cart features are backed by Squarespace's own servers and will
NOT work once self-hosted. Those need to be replaced separately (e.g. a
plain <form> posting to a service like Formspree, or a small backend).
"""
import hashlib
import os
import re
import sys
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

START_URL = "https://www.honeybee-early-learning.com/"
SITE_HOSTS = {"honeybee-early-learning.com", "www.honeybee-early-learning.com"}
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror")
MAX_PAGES = 60
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

visited_pages = set()
page_queue = [START_URL]
asset_cache = {}  # remote url -> local relative path (from OUT_DIR)
page_local_paths = {}  # normalized page url -> local relative path

session_headers = {"User-Agent": USER_AGENT}


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=session_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def norm_page_url(url):
    parsed = urlparse(url)
    path = parsed.path or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def local_page_path(url):
    parsed = urlparse(norm_page_url(url))
    path = parsed.path.strip("/")
    if path == "":
        return "index.html"
    if "." in os.path.basename(path):
        return path
    return path + "/index.html"


def local_asset_path(url):
    if url in asset_cache:
        return asset_cache[url]
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        path = "asset"
    if parsed.query:
        h = hashlib.sha1(parsed.query.encode()).hexdigest()[:8]
        root, ext = os.path.splitext(path)
        path = f"{root}__{h}{ext}"
    if "." not in os.path.basename(path):
        # No extension: avoid the same path later doubling as a directory
        # prefix for a deeper asset (e.g. "/foo" and "/foo/bar").
        path = path + "/_asset"
    rel = os.path.join("_assets", parsed.netloc, path)
    asset_cache[url] = rel
    return rel


def save_bytes(rel_path, data):
    full = os.path.join(OUT_DIR, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)


def rel_from(from_rel_path, to_rel_path):
    from_dir = os.path.dirname(from_rel_path)
    return os.path.relpath(to_rel_path, from_dir or ".")


CSS_URL_RE = re.compile(r'url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)')
CSS_IMPORT_RE = re.compile(r'@import\s+[\'"]([^\'"]+)[\'"]')


def rewrite_css(css_url, css_rel_path, text):
    def repl_url(m):
        target = m.group(1)
        if target.startswith("data:"):
            return m.group(0)
        abs_url = urljoin(css_url, target)
        new_rel = download_asset(abs_url, css_rel_path)
        return f"url({new_rel})"

    def repl_import(m):
        target = m.group(1)
        abs_url = urljoin(css_url, target)
        new_rel = download_asset(abs_url, css_rel_path)
        return f'@import "{new_rel}"'

    text = CSS_URL_RE.sub(repl_url, text)
    text = CSS_IMPORT_RE.sub(repl_import, text)
    return text


def download_asset(url, referrer_rel_path):
    """Download asset; if CSS, rewrite its internal urls too."""
    rel = local_asset_path(url)
    full = os.path.join(OUT_DIR, rel)
    if url in asset_cache and os.path.exists(full):
        return rel_from(referrer_rel_path, rel)
    try:
        data, ctype = fetch(url)
    except Exception as e:
        print(f"  ! asset failed: {url} ({e})", file=sys.stderr)
        return url
    try:
        if "css" in ctype or rel.endswith(".css"):
            text = data.decode("utf-8", errors="replace")
            text = rewrite_css(url, rel, text)
            save_bytes(rel, text.encode("utf-8"))
        else:
            save_bytes(rel, data)
    except OSError as e:
        print(f"  ! asset save failed: {url} ({e})", file=sys.stderr)
        return url
    return rel_from(referrer_rel_path, rel)


ASSET_ATTRS = {
    ("img", "src"), ("img", "data-src"), ("source", "src"),
    ("link", "href"), ("script", "src"), ("video", "src"),
    ("audio", "src"), ("source", "srcset"), ("img", "srcset"),
}


class Rewriter(HTMLParser):
    def __init__(self, base_url, page_rel_path):
        super().__init__(convert_charrefs=False)
        self.base_url = base_url
        self.page_rel_path = page_rel_path
        self.out = []
        self.discovered_links = []

    def handle_starttag(self, tag, attrs, self_closing=False):
        attrs = dict(attrs)
        new_attrs = []
        for k, v in list(attrs.items()):
            if v is None:
                new_attrs.append((k, None))
                continue
            if tag == "a" and k == "href":
                abs_url = urljoin(self.base_url, v)
                parsed = urlparse(abs_url)
                if parsed.netloc in SITE_HOSTS and parsed.scheme in ("http", "https"):
                    self.discovered_links.append(abs_url)
                    target_rel = local_page_path(abs_url)
                    frag = f"#{parsed.fragment}" if parsed.fragment else ""
                    v = rel_from(self.page_rel_path, target_rel) + frag
                new_attrs.append((k, v))
            elif (tag, k) in (("img", "srcset"), ("source", "srcset")):
                parts = []
                for chunk in v.split(","):
                    chunk = chunk.strip()
                    if not chunk:
                        continue
                    bits = chunk.split()
                    u = bits[0]
                    abs_url = urljoin(self.base_url, u)
                    if urlparse(abs_url).scheme in ("http", "https"):
                        new_u = download_asset(abs_url, self.page_rel_path)
                        bits[0] = new_u
                    parts.append(" ".join(bits))
                new_attrs.append((k, ", ".join(parts)))
            elif (tag, k) in ASSET_ATTRS:
                abs_url = urljoin(self.base_url, v)
                if urlparse(abs_url).scheme in ("http", "https"):
                    v = download_asset(abs_url, self.page_rel_path)
                new_attrs.append((k, v))
            else:
                new_attrs.append((k, v))
        attr_str = "".join(
            f' {k}="{v}"' if v is not None else f" {k}" for k, v in new_attrs
        )
        self.out.append(f"<{tag}{attr_str}{' /' if self_closing else ''}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, self_closing=True)

    def handle_endtag(self, tag):
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        self.out.append(data)

    def handle_comment(self, data):
        self.out.append(f"<!--{data}-->")

    def handle_entityref(self, name):
        self.out.append(f"&{name};")

    def handle_charref(self, name):
        self.out.append(f"&#{name};")

    def handle_decl(self, decl):
        self.out.append(f"<!{decl}>")


def crawl():
    os.makedirs(OUT_DIR, exist_ok=True)
    count = 0
    while page_queue and count < MAX_PAGES:
        url = page_queue.pop(0)
        norm = norm_page_url(url)
        if norm in visited_pages:
            continue
        visited_pages.add(norm)
        print(f"[{count+1}/{MAX_PAGES}] {norm}")
        try:
            data, ctype = fetch(norm)
        except Exception as e:
            print(f"  ! page failed: {e}", file=sys.stderr)
            continue
        if "html" not in ctype and not norm.endswith("/") and "." in os.path.basename(urlparse(norm).path):
            continue
        html = data.decode("utf-8", errors="replace")
        page_rel = local_page_path(norm)
        rewriter = Rewriter(norm, page_rel)
        try:
            rewriter.feed(html)
            rewriter.close()
            save_bytes(page_rel, "".join(rewriter.out).encode("utf-8"))
        except OSError as e:
            print(f"  ! page save failed: {norm} ({e})", file=sys.stderr)
            continue
        for link in rewriter.discovered_links:
            n = norm_page_url(link)
            if n not in visited_pages and link not in page_queue:
                page_queue.append(link)
        count += 1
        time.sleep(0.4)
    print(f"\nDone. {count} pages, {len(asset_cache)} assets -> {OUT_DIR}")


if __name__ == "__main__":
    crawl()
