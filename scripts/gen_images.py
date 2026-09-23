"""Generate AI images for posts via Pollinations.ai (free, no API key).

For every docs/posts/*.md missing an `image:` front-matter field, downloads a
deterministic AI image into docs/assets/images/<slug>.jpg and injects
`image: assets/images/<slug>.jpg` into the front matter. Also creates
docs/assets/images/og-image.jpg for social cards if missing.
"""

import hashlib
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

DOCS = Path(__file__).resolve().parent.parent / "docs"
IMAGES = DOCS / "assets" / "images"
POSTS = DOCS / "posts"

STYLE = "professional product photography, tech review, cinematic studio lighting, sharp focus, high detail"


def fetch(url: str, dest: Path, retries: int = 2) -> bool:
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "self-funding-agent/1.0"})
            with urlopen(req, timeout=60) as resp:
                data = resp.read()
            if len(data) < 5000:
                raise ValueError(f"too small: {len(data)} bytes")
            dest.write_bytes(data)
            print(f"  ok: {dest.name} ({len(data)//1024} KB)")
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"  retry {attempt + 1} for {dest.name}: {exc}")
            time.sleep(3)
    return False


def image_url(prompt: str, width: int, height: int, seed: int) -> str:
    return (
        f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        f"?width={width}&height={height}&nologo=true&seed={seed}&model=flux"
    )


def inject_front_matter(path: Path, key: str, value: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if re.search(rf"^{key}:", text, flags=re.M):
        return False
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return False
    block = m.group(1)
    if not block.endswith("\n"):
        block += "\n"
    new_text = f"---\n{block}{key}: {value}\n---\n" + text[m.end():]
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    IMAGES.mkdir(parents=True, exist_ok=True)
    posts = sorted(POSTS.glob("*.md"))
    if not posts:
        print("no posts found")
        return 0

    generated = 0
    for post in posts:
        slug = post.stem
        dest = IMAGES / f"{slug}.jpg"
        text = post.read_text(encoding="utf-8")
        if re.search(r"^image:", text, flags=re.M) and dest.exists():
            continue
        title_m = re.search(r'^title:\s*"?(.*?)"?\s*$', text, flags=re.M)
        title = title_m.group(1) if title_m else slug.replace("-", " ")
        prompt = f"{title}, {STYLE}"
        seed = int(hashlib.md5(slug.encode()).hexdigest()[:8], 16)
        print(f"[{slug}]")
        if fetch(image_url(prompt, 800, 500, seed), dest):
            inject_front_matter(post, "image", f"assets/images/{slug}.jpg")
            generated += 1
        time.sleep(1)

    og = IMAGES / "og-image.jpg"
    if not og.exists():
        print("[og-image]")
        if fetch(image_url("futuristic AI robot testing gadgets and smartwatch in a neon-lab, teal accents", 1200, 630, 42), og):
            generated += 1

    print(f"done: {generated} images generated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
