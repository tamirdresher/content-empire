#!/usr/bin/env python3
"""
Create a weekly "This Week in Tech" Substack newsletter draft
from the latest articles in medium-ready/.

Usage:
    python substack-newsletter.py [--dry-run]

Env vars required:
    SUBSTACK_SESSION_COOKIE     - connect.sid cookie value
    SUBSTACK_PUBLICATION_URL    - e.g. https://contentempire.substack.com

The script picks the 3–5 most-recently-modified articles and formats
them into a digest, then POSTs a draft to Substack's unofficial API.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = REPO_ROOT / "medium-ready"
MAX_ARTICLES = 5
MIN_ARTICLES = 3


# ---------------------------------------------------------------------------
# Article helpers
# ---------------------------------------------------------------------------

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


def extract_title(md_text: str, meta: dict, fallback: str) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return meta.get("title") or fallback


def extract_summary(md_text: str, max_chars: int = 300) -> str:
    """Return first non-heading paragraph, trimmed to max_chars."""
    in_code = False
    for line in md_text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not line.strip() or line.startswith("#"):
            continue
        # Strip inline markdown
        text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", line)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        text = text.strip()
        if len(text) > 30:
            return text[:max_chars].rstrip() + ("…" if len(text) > max_chars else "")
    return ""


def pick_articles(directory: Path, count: int) -> list[Path]:
    """Return `count` most-recently-modified .md files."""
    files = sorted(
        directory.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[:count]


# ---------------------------------------------------------------------------
# Newsletter template
# ---------------------------------------------------------------------------

ARTICLE_BLOCK = """\
<h2>{title}</h2>
<p>{summary}</p>
<p><a href="{url}">Read the full article →</a></p>
<hr />
"""

def build_newsletter_html(articles: list[dict], pub_url: str) -> str:
    week_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    blocks = "".join(
        ARTICLE_BLOCK.format(
            title=a["title"],
            summary=a["summary"],
            url=a.get("url", pub_url),
        )
        for a in articles
    )
    return f"""<p><em>Your weekly digest from Content Empire — curated picks from our latest writing.</em></p>
<hr />
{blocks}
<p style="font-size:0.9em;color:#666;">
  You received this because you subscribed to Content Empire.<br/>
  <a href="{{{{unsubscribe_url}}}}">Unsubscribe</a>
</p>"""


def build_newsletter_title() -> str:
    week_str = datetime.now(timezone.utc).strftime("%b %d")
    return f"This Week in Tech — {week_str}"


# ---------------------------------------------------------------------------
# Substack API
# ---------------------------------------------------------------------------

def substack_post(pub_url: str, cookie: str, payload: dict) -> dict:
    base = pub_url.rstrip("/")
    url = f"{base}/api/v1/posts"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Cookie": f"connect.sid={cookie}",
            "Accept": "application/json",
            "User-Agent": "ContentEmpire-Newsletter-Bot/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"  ✗ HTTP {e.code}: {body_text}", file=sys.stderr)
        raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Create weekly Substack newsletter draft")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    args = parser.parse_args()

    cookie = os.environ.get("SUBSTACK_SESSION_COOKIE", "")
    pub_url = os.environ.get("SUBSTACK_PUBLICATION_URL", "")

    if not args.dry_run:
        if not cookie:
            print("✗ SUBSTACK_SESSION_COOKIE not set.", file=sys.stderr)
            sys.exit(1)
        if not pub_url:
            print("✗ SUBSTACK_PUBLICATION_URL not set.", file=sys.stderr)
            sys.exit(1)

    article_paths = pick_articles(ARTICLES_DIR, MAX_ARTICLES)
    if len(article_paths) < MIN_ARTICLES:
        print(f"⚠  Only {len(article_paths)} article(s) available (minimum {MIN_ARTICLES}).")
        if not article_paths:
            sys.exit(1)

    articles = []
    for p in article_paths:
        md_text = p.read_text(encoding="utf-8")
        meta, md_text = parse_frontmatter(md_text)
        title = extract_title(md_text, meta, p.stem.replace("-", " ").title())
        summary = extract_summary(md_text)
        articles.append({"title": title, "summary": summary, "url": pub_url})
        print(f"  ✓ {p.name}: {title}")

    newsletter_title = build_newsletter_title()
    newsletter_html = build_newsletter_html(articles, pub_url)

    print(f"\n📰 Newsletter: {newsletter_title}")
    print(f"   Articles  : {len(articles)}")
    print(f"   HTML size : {len(newsletter_html)} chars")

    if args.dry_run:
        print("\n[DRY RUN] Would create Substack draft with:")
        print(f"  title: {newsletter_title}")
        print("  body preview:")
        print(newsletter_html[:500])
        return

    payload = {
        "draft_title": newsletter_title,
        "draft_body": newsletter_html,
        "draft_subtitle": "Your weekly dose of tech insights from Content Empire",
        "audience": "everyone",
        "draft_podcast_url": "",
        "section_chosen": False,
        "type": "newsletter",
    }

    print("\nCreating Substack draft…")
    result = substack_post(pub_url, cookie, payload)
    draft_id = result.get("id", "unknown")
    print(f"✓ Draft created! ID: {draft_id}")
    print(f"  Edit at: {pub_url}/publish/post/{draft_id}")


if __name__ == "__main__":
    main()
