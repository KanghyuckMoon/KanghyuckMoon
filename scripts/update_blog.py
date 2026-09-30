"""Update only the profile's latest-posts block from the public Astro RSS feed."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

FEED_URL = "https://kanghyuckmoon.github.io/rss.xml"
START = "<!-- BLOG-POST-LIST:START -->"
END = "<!-- BLOG-POST-LIST:END -->"
EMPTY = "블로그를 준비하고 있습니다. 첫 개발 기록이 올라오면 최신 글 3개가 이곳에 표시됩니다."
SAMPLES = {
    "/blog/first-post": "First post",
    "/blog/second-post": "Second post",
    "/blog/third-post": "Third post",
    "/blog/markdown-style-guide": "Markdown Style Guide",
    "/blog/using-mdx": "Using MDX",
}


def render_posts(data, now=None):
    root = ET.fromstring(data)
    if root.tag != "rss" or root.find("channel") is None:
        raise ValueError("Expected an RSS channel; README was not changed.")
    now = now or datetime.now(timezone.utc)
    posts = []
    for item in root.findall("./channel/item"):
        title = " ".join((item.findtext("title") or "").split())
        link = (item.findtext("link") or "").strip()
        url = urlsplit(link)
        if not title or url.scheme != "https" or url.netloc.lower() != "kanghyuckmoon.github.io":
            continue
        if SAMPLES.get(url.path.rstrip("/")) == title:
            continue
        try:
            date = parsedate_to_datetime(item.findtext("pubDate") or "")
            date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
            date = date.astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue
        if date <= now:
            posts.append((date, title, link))
    posts.sort(key=lambda post: post[0], reverse=True)
    lines, seen = [], set()
    for date, title, link in posts:
        if link in seen:
            continue
        seen.add(link)
        # Feed titles remain plain Markdown text; links cannot escape their destination.
        title = re.sub(r"([\\`*_{}\[\]()<>!|])", r"\\\1", title)
        link = link.replace("(", "%28").replace(")", "%29").replace("<", "%3C").replace(">", "%3E")
        lines.append(f"- [{title}]({link}) · {date:%Y-%m-%d}")
        if len(lines) == 3:
            break
    return "\n".join(lines) if lines else EMPTY


def update_readme(content, block):
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError("Expected exactly one latest-posts block.")
    start = content.index(START) + len(START)
    end = content.index(END)
    if end < start:
        raise ValueError("Latest-posts markers are out of order.")
    return content[:start] + "\n" + block + "\n" + content[end:]


def main():
    # A local feed fixture can be supplied for offline validation.
    if len(sys.argv) > 1:
        data = Path(sys.argv[1]).read_bytes()
    else:
        request = Request(FEED_URL, headers={"User-Agent": "KanghyuckMoon-profile"})
        with urlopen(request, timeout=30) as response:
            data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("RSS feed is unexpectedly large.")
    block = render_posts(data)
    path = Path(__file__).resolve().parents[1] / "README.md"
    before = path.read_text(encoding="utf-8")
    after = update_readme(before, block)
    if before != after:
        path.write_text(after, encoding="utf-8")
        print("Updated latest blog posts.")
    else:
        print("Latest blog posts unchanged.")


if __name__ == "__main__":
    main()
