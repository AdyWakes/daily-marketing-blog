import os
import random
import re
import shutil
from datetime import datetime, timezone


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "daily-post"


def parse_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    front_matter = {}
    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
        if ":" in lines[idx]:
            key, value = lines[idx].split(":", 1)
            front_matter[key.strip()] = value.strip().strip('"').strip("'")

    if end_index is None:
        return {}, text

    body = "\n".join(lines[end_index + 1 :]).lstrip()
    return front_matter, body


def extract_title_from_body(body: str) -> tuple[str, str]:
    lines = body.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        title = stripped.lstrip("#").strip()
        remaining = "\n".join(lines[idx + 1 :]).lstrip()
        return title, remaining
    return "", body


def pick_random_image(images_dir: str, allowed_exts: tuple[str, ...]) -> str | None:
    if not os.path.isdir(images_dir):
        return None
    candidates = []
    for name in os.listdir(images_dir):
        if name.lower().endswith(allowed_exts):
            candidates.append(os.path.join(images_dir, name))
    return random.choice(candidates) if candidates else None


def main() -> None:
    today = datetime.now(timezone.utc).date()
    date_prefix = today.strftime("%Y-%m-%d")

    posts_dir = os.path.join(os.getcwd(), "_posts")
    os.makedirs(posts_dir, exist_ok=True)

    for name in os.listdir(posts_dir):
        if name.startswith(date_prefix + "-") and name.endswith(".md"):
            print("Post already exists for today. Exiting.")
            return

    drafts_dir = os.path.join(os.getcwd(), "drafts")
    if not os.path.isdir(drafts_dir):
        print("No drafts folder found. Exiting.")
        return

    draft_files = sorted(
        [
            name
            for name in os.listdir(drafts_dir)
            if name.lower().endswith(".md")
        ]
    )

    if not draft_files:
        print("No draft posts found. Exiting.")
        return

    draft_name = draft_files[0]
    draft_path = os.path.join(drafts_dir, draft_name)
    with open(draft_path, "r", encoding="utf-8") as handle:
        draft_text = handle.read()

    front_matter, body = parse_front_matter(draft_text)
    title = front_matter.get("title", "").strip()
    if not title:
        title, body = extract_title_from_body(body)
    if not title:
        title = f"Daily Post {date_prefix}"

    slug = slugify(title)
    filename = f"{date_prefix}-{slug}.md"
    filepath = os.path.join(posts_dir, filename)

    image_relpath = ""
    image_dir = os.path.join(os.getcwd(), "assets", "images")
    os.makedirs(image_dir, exist_ok=True)
    allowed_exts = (".png", ".jpg", ".jpeg", ".webp", ".gif")
    draft_image = front_matter.get("image", "").strip()
    image_source = None

    if draft_image:
        if draft_image.lower() in ("random", "auto"):
            image_source = pick_random_image(
                os.path.join(drafts_dir, "images"), allowed_exts
            )
        elif draft_image.startswith("http://") or draft_image.startswith("https://"):
            image_relpath = draft_image
        else:
            candidate = os.path.join(drafts_dir, draft_image)
            if os.path.isfile(candidate):
                image_source = candidate
    else:
        image_source = pick_random_image(
            os.path.join(drafts_dir, "images"), allowed_exts
        )

    if image_source:
        _, ext = os.path.splitext(image_source)
        image_filename = f"{date_prefix}-{slug}{ext.lower()}"
        image_relpath = f"/assets/images/{image_filename}"
        image_path = os.path.join(image_dir, image_filename)
        shutil.copy2(image_source, image_path)

    safe_title = title.replace('"', "")

    front_matter_lines = [
        "---",
        f"title: \"{safe_title}\"",
        f"date: {today.isoformat()}",
    ]
    if image_relpath:
        front_matter_lines.append(f"image: {image_relpath}")
    front_matter_lines.extend(["layout: post", "---", ""])
    front_matter = "\n".join(front_matter_lines) + "\n"

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(front_matter)
        handle.write(body)
        handle.write("\n")

    used_dir = os.path.join(drafts_dir, "used")
    os.makedirs(used_dir, exist_ok=True)
    shutil.move(draft_path, os.path.join(used_dir, draft_name))

    print(f"Created {filepath}")


if __name__ == "__main__":
    main()
