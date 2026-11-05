"""Publish an article and its navigation in one GitHub commit."""
import base64
from html import escape
import json
import re
from urllib.parse import quote


def render(template, title, body, day, section):
    label = section.title()
    headline = escape(title)
    date_label = day.replace("-", " · ")
    content = "".join(f"<p>{escape(block).replace(chr(10), '<br>')}</p>"
                      for block in re.split(r"\n\s*\n", body.strip()) if block.strip())
    replacements = {
        "【文章标题】": headline,
        "【一句话副标题】": f"{label} · {headline}",
        "2026-06-15": day,
        "2026 · 06 · 15": date_label,
        "02 / Observe · 【分类，比如：复盘 / 思考 / 学习】": f"{label} · 自动发布",
        "【标签1 / 标签2】": "Auto Blog Agent",
        "X min": "约 3 min",
    }
    template = re.sub(r"(?s)<!--.*?-->", "", template)
    for source, replacement in replacements.items():
        template = template.replace(source, replacement)
    template, count = re.subn(r'(?s)(<div class="post-body">).*?(</div>)',
                              lambda m: m[1] + content + m[2], template, count=1)
    if not count:
        raise ValueError("Blog template has no post-body slot")
    if section == "create":
        template = template.replace('href="/observe.html" class="is-current"', 'href="/observe.html"')
        template = template.replace('href="/create.html"', 'href="/create.html" class="is-current"', 1)
        template = template.replace('/observe.html">← back to observe', '/create.html">← back to create')
    return template


def publish_html(blog, day, article, request, token):
    repo, branch = blog["repository"], blog["branch"]
    section = blog.get("section", "create")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo) or section not in {"create", "observe"}:
        raise ValueError("Invalid HTML blog repository or section")
    root = f"https://api.github.com/repos/{repo}"
    ref = f"/git/refs/heads/{quote(branch, safe='/')}"

    def api(path, payload=None, method=None):
        return json.loads(request(root + path, payload, token, method))

    parent = api(ref)["object"]["sha"]
    base_tree = api(f"/git/commits/{parent}")["tree"]["sha"]

    def read(path):
        entry = api(f"/contents/{path}?ref={parent}")
        return base64.b64decode(entry["content"]).decode("utf-8")

    path = f"{day.replace('-', '/')}/auto-{section}"
    href = f"/{path}/"
    navigation = (f'<a href="{href}" class="entry"><span class="entry-date">'
                  f'{day.replace("-", " · ")}</span><div class="entry-body">'
                  f'<h2 class="entry-title">{escape(article["title"])}</h2></div>'
                  f'<span class="entry-meta">{section.title()}</span></a>')
    files = {}
    for index in (f"{section}.html", "archives/index.html"):
        contents = read(index)
        if f'href="{href}"' in contents:
            return "already_published"
        marker = '<section class="entry-list">'
        if contents.count(marker) != 1:
            raise ValueError(f"Blog index has no unique entry list: {index}")
        files[index] = contents.replace(marker, marker + "\n" + navigation, 1)
    # A fixed slot per section and day is the idempotency key, even after runner state loss.
    daily_tree = api(f"/git/trees/{base_tree}?recursive=1")
    if daily_tree.get("truncated"):
        raise ValueError("Repository tree too large to check existing publication")
    if any(item["path"] == f"{path}/index.html" for item in daily_tree["tree"]):
        return "already_published"
    files[f"{path}/index.html"] = render(read("_template-post.html"), article["title"],
                                         article["body"], day, section)
    tree = api("/git/trees", {"base_tree": base_tree, "tree": [
        {"path": name, "mode": "100644", "type": "blob", "content": value}
        for name, value in files.items()
    ]}, "POST")["sha"]
    commit = api("/git/commits", {"message": "blog: add reviewed article",
                                 "tree": tree, "parents": [parent]}, "POST")["sha"]
    api(ref, {"sha": commit, "force": False}, "PATCH")
    return "published"
