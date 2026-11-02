"""Regression checks for every generated language edition and its crawlable assets."""

import json
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BASE = "https://arpanjot-coding.github.io/CheatCraft/"
LANGS = ["en", "it", "ja", "ko", "zh-CN", "hi", "fil", "vi", "th", "es", "pt", "de", "fr"]


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.nodes = []
        self.ids = set()
        self.schema = []
        self.in_schema = False
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.nodes.append((tag, attrs))
        if "id" in attrs:
            self.ids.add(attrs["id"])
        self.in_schema = tag == "script" and attrs.get("type") == "application/ld+json"

    def handle_data(self, data):
        if self.in_schema:
            self.schema.append(json.loads(data))

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_schema = False


class WebsiteTests(unittest.TestCase):
    def pages(self):
        for lang in LANGS:
            path = DOCS / "index.html" if lang == "en" else DOCS / lang / "index.html"
            yield lang, path, Document(path)

    def test_metadata_and_reciprocal_locales(self):
        expected = {
            "tl" if lang == "fil" else lang: BASE + ("" if lang == "en" else lang + "/")
            for lang in LANGS
        }
        expected["x-default"] = BASE
        for lang, path, doc in self.pages():
            with self.subTest(lang=lang):
                self.assertEqual([a["lang"] for t, a in doc.nodes if t == "html"], [lang])
                self.assertEqual(sum(t == "h1" for t, a in doc.nodes), 1)
                canonical = [
                    a["href"] for t, a in doc.nodes if t == "link" and a.get("rel") == "canonical"
                ]
                self.assertEqual(canonical, [BASE + ("" if lang == "en" else lang + "/")])
                alternatives = {
                    a["hreflang"]: a["href"]
                    for t, a in doc.nodes
                    if t == "link" and a.get("rel") == "alternate"
                }
                self.assertEqual(alternatives, expected)
                metas = {
                    a.get("name", a.get("property")): a.get("content")
                    for t, a in doc.nodes
                    if t == "meta"
                }
                for key in [
                    "description",
                    "viewport",
                    "og:title",
                    "og:locale",
                    "og:image",
                    "twitter:image",
                ]:
                    self.assertTrue(metas.get(key), key)
                self.assertEqual(metas["og:image"], BASE + "social-card.png")
                self.assertIn("main", doc.ids)

    def test_local_links_images_and_accessible_screenshot(self):
        for lang, path, doc in self.pages():
            for tag, a in doc.nodes:
                reference = a.get("href") or a.get("src")
                if reference:
                    parsed = urlsplit(reference)
                    if reference.startswith("#"):
                        self.assertIn(reference[1:], doc.ids)
                    elif reference.startswith(BASE):
                        target = DOCS / unquote(reference[len(BASE) :].split("#")[0])
                        self.assertTrue(target.exists(), reference)
                    elif not parsed.scheme and not parsed.netloc:
                        self.assertTrue(
                            (path.parent / unquote(parsed.path)).resolve().exists(), reference
                        )
                if tag == "img":
                    self.assertTrue(a.get("alt"))
                    self.assertEqual((a["width"], a["height"]), ("1362", "930"))
                    self.assertIn("screenshots/memory-search.jpg", a["src"])

    def test_truthful_schema_and_sitemap(self):
        for lang, path, doc in self.pages():
            app = doc.schema[0]["@graph"][0]
            self.assertEqual(app["softwareVersion"], "0.4.0")
            self.assertEqual(app["offers"]["price"], "0")
            self.assertNotIn("aggregateRating", app)
            self.assertNotIn("review", app)
        ns = {
            "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "x": "http://www.w3.org/1999/xhtml",
        }
        urls = ET.parse(DOCS / "sitemap.xml").findall("s:url", ns)
        self.assertEqual(len(urls), 13)
        for url in urls:
            self.assertEqual(len(url.findall("x:link", ns)), 14)
        self.assertIn("noindex", (DOCS / "404.html").read_text())

    def test_image_dimensions(self):
        for name, expected in [
            ("social-card.png", (1200, 630)),
            ("screenshots/memory-search.jpg", (1362, 930)),
        ]:
            with Image.open(DOCS / name) as image:
                self.assertEqual(image.size, expected)
                self.assertEqual(image.format, "JPEG" if name.endswith(".jpg") else "PNG")


if __name__ == "__main__":
    unittest.main(verbosity=2)
