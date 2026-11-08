import base64
import json
import unittest
from pathlib import Path

import yaml

from autoblog.html_publish import publish_html, render


class DeploymentTests(unittest.TestCase):
    def test_html_publication_writes_navigation_and_uses_nonforce_update(self):
        blog = {"repository": "example/site", "branch": "main", "section": "create"}
        marker = '<section class="entry-list">'
        template = '<title>【文章标题】</title><div class="post-body">placeholder</div>'
        writes = []
        existing = [{"path": "2026/11/07/chatgpt-to-codex/index.html"}]

        def request(url, data, token, method):
            if method:
                writes.append((method, data))
                return json.dumps({"sha": "new"})
            if "/git/refs/" in url:
                return '{"object":{"sha":"old"}}'
            if "/git/commits/" in url:
                return '{"tree":{"sha":"tree"}}'
            if "/git/trees/" in url:
                return json.dumps({"tree": existing})
            content = template if "_template-post.html" in url else marker
            return json.dumps({"content": base64.b64encode(content.encode()).decode()})

        article = {"title": "Example", "body": "<script>alert(1)</script>"}
        self.assertEqual(publish_html(blog, "2026-11-05", article, request, "token"), "published")
        files = {item["path"]: item["content"] for item in writes[0][1]["tree"]}
        path = "2026/11/05/auto-create/index.html"
        self.assertIn("&lt;script&gt;", files[path])
        self.assertIn("/2026/11/05/auto-create/", files["archives/index.html"])
        self.assertIn("/2026/11/05/auto-create/", files["create.html"])
        self.assertNotIn("2026/11/07/chatgpt-to-codex/index.html", files)
        self.assertEqual(writes[-1], ("PATCH", {"sha": "new", "force": False}))
        existing.append({"path": path})
        writes.clear()
        self.assertEqual(publish_html(blog, "2026-11-05", article, request, "token"), "already_published")
        self.assertEqual(writes, [])

    def test_observe_section_updates_only_its_index_and_archives(self):
        blog = {"repository": "tance-mang/tance-mang.github.io", "branch": "main", "section": "observe"}
        marker = '<section class="entry-list">'
        template = '<title>【文章标题】</title><div class="post-body">placeholder</div>'
        writes = []

        def request(url, data, token, method):
            if method:
                writes.append((method, data))
                return json.dumps({"sha": "new"})
            if "/git/refs/" in url:
                return '{"object":{"sha":"old"}}'
            if "/git/commits/" in url:
                return '{"tree":{"sha":"tree"}}'
            if "/git/trees/" in url:
                return json.dumps({"tree": [{"path": "2026/11/07/chatgpt-to-codex/index.html"}]})
            content = template if "_template-post.html" in url else marker
            return json.dumps({"content": base64.b64encode(content.encode()).decode()})

        article = {"title": "Observe <note>", "body": "记录一段可核对的变更。"}
        self.assertEqual(publish_html(blog, "2026-11-08", article, request, "token"), "published")
        files = {item["path"]: item["content"] for item in writes[0][1]["tree"]}
        self.assertEqual(set(files), {"2026/11/08/auto-observe/index.html", "observe.html", "archives/index.html"})
        self.assertIn("/2026/11/08/auto-observe/", files["observe.html"])
        self.assertIn("/2026/11/08/auto-observe/", files["archives/index.html"])
        self.assertIn("Observe &lt;note&gt;", files["observe.html"])
        self.assertNotIn("2026/11/07/chatgpt-to-codex/index.html", files)
        self.assertEqual(writes[-1], ("PATCH", {"sha": "new", "force": False}))

    def test_existing_navigation_link_is_not_rewritten(self):
        blog = {"repository": "example/site", "branch": "main", "section": "create"}
        href = "/2026/11/05/auto-create/"
        marker = f'<section class="entry-list"><a href="{href}" class="entry">old</a>'
        writes = []

        def request(url, data, token, method):
            if method:
                writes.append((method, data))
                return json.dumps({"sha": "new"})
            if "/git/refs/" in url:
                return '{"object":{"sha":"old"}}'
            if "/git/commits/" in url:
                return '{"tree":{"sha":"tree"}}'
            return json.dumps({"content": base64.b64encode(marker.encode()).decode()})

        article = {"title": "Example", "body": "body"}
        self.assertEqual(publish_html(blog, "2026-11-05", article, request, "token"), "already_published")
        self.assertEqual(writes, [])

    def test_html_publication_rejects_unknown_section(self):
        with self.assertRaises(ValueError):
            publish_html({"repository": "owner/repo", "branch": "main", "section": "news"},
                         "2026-11-08", {"title": "x", "body": "y"}, lambda *args: "{}", "token")

    def test_render_fills_site_placeholders_for_create(self):
        template = '''<a href="/create.html">Create</a>
        <a href="/observe.html" class="is-current">Observe</a>
        <span class="post-eyebrow">02 / Observe · 【分类，比如：复盘 / 思考 / 学习】</span>
        <h1>【文章标题】</h1>
        <time datetime="2026-06-15">2026 · 06 · 15</time>
        <div class="post-body"><p>old</p></div>
        <a href="/observe.html">← back to observe</a>'''
        page = render(template, "标题", "正文段落。", "2026-11-08", "create")
        self.assertIn("标题", page)
        self.assertIn("2026-11-08", page)
        self.assertIn("2026 · 11 · 08", page)
        self.assertIn("正文段落。", page)
        self.assertNotIn("old", page)
        self.assertIn('href="/create.html" class="is-current"', page)
        self.assertNotIn('href="/observe.html" class="is-current"', page)
        self.assertIn('/create.html">← back to create', page)

    def test_default_config_cannot_publish_and_example_points_at_owner_blog(self):
        root = Path(__file__).resolve().parents[1]
        cfg = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["blog"]["repository"], "")
        self.assertFalse(cfg["writer_model"])
        self.assertFalse(cfg["reviewer_model"])
        example_text = (root / "config.example.yaml").read_text(encoding="utf-8")
        self.assertNotRegex(example_text, r"(ghp_|github_pat_|sk-[A-Za-z0-9]{8,})")
        example = yaml.safe_load(example_text)
        self.assertFalse(example["enabled"])
        self.assertEqual(example["blog"]["repository"], "tance-mang/tance-mang.github.io")
        self.assertEqual(example["blog"]["branch"], "main")
        self.assertEqual(example["blog"]["format"], "tance-html")
        self.assertEqual(example["blog"]["section"], "create")
        self.assertFalse(example["writer_model"])
        self.assertFalse(example["reviewer_model"])
