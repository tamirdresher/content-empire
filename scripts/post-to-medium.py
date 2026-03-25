#!/usr/bin/env python3
"""
Post articles from medium-ready/ to Medium as drafts.

Usage:
    python post-to-medium.py [--dry-run]

Env vars required:
    MEDIUM_INTEGRATION_TOKEN  - Medium integration token

Tracking file: scripts/medium-posted.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import markdown2
    _MD_BACKEND = "markdown2"
except ImportError:
    try:
        import mistune
        _MD_BACKEND = "mistune"
    except ImportError:
        _MD_BACKEND = None

import urllib.request
import urllib.error

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = REPO_ROOT / "medium-ready"
TRACKING_FILE = Path(__file__).resolve().parent / "medium-posted.json"
MEDIUM_API = "https://api.medium.com/v1"


def md_to_html(md_text: str) -> str:
    if _MD_BACKEND == "markdown2":
        return markdown2.markdown(md_text, extras=["fenced-code-blocks", "tables"])
    if _MD_BACKEND == "mistune":
        return mistune.html(md_text)
    # Minimal stdlib fallback — headings, paragraphs, code fences
    lines = md_text.splitlines()
    html_parts = []
    in_code = False
    for line in lines:
        if line.startswith("```"):
            if in_code:
                html_parts.append("</code></pre>")
                in_code = False
            else:
                html_parts.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            html_parts.append(line + "\n")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            html_parts.append(f"<h{level}>{m.group(2)}</h{level}>")
        elif line.strip():
            html_parts.append(f"<p>{line}</p>")
    return "\n".join(html_parts)


def parse_frontmatter(md_text: str) -> tuple[dict, str]:
    """Strip YAML frontmatter and return (meta_dict, remaining_markdown)."""
    meta = {}
    if md_text.startswith("---"):
        end = md_text.find("\n---", 3)
        if end != -1:
            fm_block = md_text[3:end].strip()
            for line in fm_block.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            md_text = md_text[end + 4:].lstrip("\n")
    return meta, md_text


def extract_title_and_body(md_text: str) -> tuple[str, str]:
    """Return (title, body_without_title) from markdown text (after frontmatter stripped)."""
    lines = md_text.splitlines()
    title = ""
    body_lines = []
    found_title = False
    for line in lines:
        if not found_title and line.startswith("# "):
            title = line[2:].strip()
            found_title = True
        else:
            body_lines.append(line)
    return title, "\n".join(body_lines)


def infer_tags(md_text: str, filename: str) -> list[str]:
    """Infer up to 5 tags from filename keywords and content."""
    TAG_KEYWORDS = {
        "ai": ["ai", "agent", "llm", "gpt", "copilot", "artificial"],
        "automation": ["automat", "workflow", "pipeline", "ci/cd", "github actions"],
        "kubernetes": ["kubernetes", "k8s", "helm", "cluster"],
        "python": ["python"],
        "javascript": ["javascript", "js", "node", "react"],
        "devops": ["devops", "deployment", "docker", "container"],
        "productivity": ["productiv", "solopreneur", "side project"],
        "writing": ["writing", "content", "newsletter", "medium", "substack"],
        "software-engineering": ["engineer", "architecture", "design pattern"],
        "mcp": ["mcp", "model context protocol"],
        "playwright": ["playwright"],
    }
    combined = (filename + " " + md_text[:2000]).lower()
    tags = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            tags.append(tag)
        if len(tags) >= 5:
            break
    return tags or ["software-engineering", "automation"]


def medium_request(method: str, path: str, token: str, body: dict | None = None):
    url = f"{MEDIUM_API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"  ✗ HTTP {e.code}: {body_text}", file=sys.stderr)
        raise


def get_author_id(token: str) -> str:
    data = medium_request("GET", "/me", token)
    return data["data"]["id"]


def load_tracking() -> dict:
    if TRACKING_FILE.exists():
        return json.loads(TRACKING_FILE.read_text())
    return {}


def save_tracking(tracking: dict) -> None:
    TRACKING_FILE.write_text(json.dumps(tracking, indent=2))


def post_article(author_id: str, token: str, title: str, html: str, tags: list[str]) -> str:
    payload = {
        "title": title,
        "contentFormat": "html",
        "content": html,
        "tags": tags[:5],
        "publishStatus": "draft",
    }
    result = medium_request("POST", f"/users/{author_id}/posts", token, payload)
    return result["data"]["url"]


def main():
    parser = argparse.ArgumentParser(description="Post articles to Medium as drafts")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    args = parser.parse_args()

    token = os.environ.get("MEDIUM_INTEGRATION_TOKEN", "")
    if not token and not args.dry_run:
        print("✗ MEDIUM_INTEGRATION_TOKEN not set.", file=sys.stderr)
        sys.exit(1)

    if _MD_BACKEND is None:
        print("⚠  No markdown library found. Using minimal HTML fallback.")
        print("   Run: pip install markdown2")

    tracking = load_tracking()

    articles = sorted(ARTICLES_DIR.glob("*.md"))
    if not articles:
        print(f"No articles found in {ARTICLES_DIR}")
        sys.exit(0)

    author_id = None
    if not args.dry_run:
        print("Fetching Medium author ID…")
        author_id = get_author_id(token)
        print(f"  Author ID: {author_id}")

    posted = 0
    skipped = 0

    for article_path in articles:
        key = article_path.name
        if key in tracking:
            print(f"  [SKIP] {key} (already posted)")
            skipped += 1
            continue

        md_text = article_path.read_text(encoding="utf-8")
        meta, md_text = parse_frontmatter(md_text)
        title, body = extract_title_and_body(md_text)
        if not title:
            title = meta.get("title") or article_path.stem.replace("-", " ").title()
        # Prefer frontmatter tags if available
        fm_tags_raw = meta.get("tags", "")
        if fm_tags_raw:
            import ast
            try:
                fm_tags = ast.literal_eval(fm_tags_raw) if fm_tags_raw.startswith("[") else [t.strip() for t in fm_tags_raw.split(",")]
            except Exception:
                fm_tags = []
        else:
            fm_tags = []
        tags = (fm_tags + infer_tags(md_text, article_path.stem))[:5] or ["software-engineering"]
        html = md_to_html(body)

        print(f"\n→ {key}")
        print(f"  Title : {title}")
        print(f"  Tags  : {tags}")
        print(f"  Body  : {len(html)} chars of HTML")

        if args.dry_run:
            print("  [DRY RUN] Would post to Medium")
        else:
            print("  Posting…")
            url = post_article(author_id, token, title, html, tags)
            tracking[key] = {"title": title, "url": url}
            save_tracking(tracking)
            print(f"  ✓ Draft created: {url}")
            posted += 1

    print(f"\nDone. Posted: {posted}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
