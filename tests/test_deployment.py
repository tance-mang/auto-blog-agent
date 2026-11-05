import base64
import json
import unittest

from autoblog.html_publish import publish_html


class DeploymentTests(unittest.TestCase):
    def test_html_publication_writes_navigation_and_uses_nonforce_update(self):
        blog = {"repository": "example/site", "branch": "main", "section": "create"}
        marker = '<section class="entry-list">'
        template = '<title>【文章标题】</title><div class="post-body">placeholder</div>'
        writes = []
        existing = []

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
        self.assertEqual(writes[-1], ("PATCH", {"sha": "new", "force": False}))
        existing.append({"path": path})
        writes.clear()
        self.assertEqual(publish_html(blog, "2026-11-05", article, request, "token"), "already_published")
        self.assertEqual(writes, [])
