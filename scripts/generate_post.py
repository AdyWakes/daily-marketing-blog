import base64
import json
import os
import random
import re
from datetime import datetime, timezone
from typing import Optional

import requests
import markdown


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "daily-post"


def extract_text_from_response(payload: dict) -> str:
    candidates = payload.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    chunks = []
    for part in parts:
        text = part.get("text")
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()

def parse_json_from_text(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
    raise ValueError("Could not parse JSON from model response")


def extract_title_from_body(body: str) -> tuple[str, str]:
    lines = body.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            remaining = "\n".join(lines[idx + 1 :]).lstrip()
            return title, remaining
        break
    return "", body


def pick_random_image(images_dir: str) -> str:
    if not os.path.isdir(images_dir):
        return ""
    allowed_exts = (".png", ".jpg", ".jpeg", ".webp", ".gif")
    candidates = [
        os.path.join(images_dir, name)
        for name in os.listdir(images_dir)
        if name.lower().endswith(allowed_exts)
    ]
    return random.choice(candidates) if candidates else ""


def call_gemini(api_key: str, model: str, contents: list[dict]) -> dict:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
    )
    response = requests.post(
        url,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={"contents": contents},
        timeout=90,
    )
    if response.status_code >= 400:
        raise SystemExit(
            f"Gemini API error {response.status_code}: {response.text}"
        )
    return response.json()

def fetch_blogger_access_token(
    client_id: str, client_secret: str, refresh_token: str
) -> str:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise SystemExit(
            f"Blogger auth error {response.status_code}: {response.text}"
        )
    payload = response.json()
    access_token = payload.get("access_token", "").strip()
    if not access_token:
        raise SystemExit("Missing access_token from Blogger auth.")
    return access_token


def post_to_blogger(
    access_token: str,
    blog_id: str,
    title: str,
    html_content: str,
) -> None:
    response = requests.post(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "kind": "blogger#post",
            "title": title,
            "content": html_content,
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise SystemExit(
            f"Blogger post error {response.status_code}: {response.text}"
        )

def post_to_wordpress(
    site: str,
    username: str,
    app_password: str,
    title: str,
    html_content: str,
) -> None:
    auth = base64.b64encode(f"{username}:{app_password}".encode("utf-8")).decode(
        "utf-8"
    )
    response = requests.post(
        f"https://public-api.wordpress.com/wp/v2/sites/{site}/posts",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        },
        json={
            "title": title,
            "content": html_content,
            "status": "publish",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise SystemExit(
            f"WordPress post error {response.status_code}: {response.text}"
        )

def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required.")

    text_model = os.environ.get("GEMINI_TEXT_MODEL", "").strip() or "gemini-2.5-flash"
    topic = os.environ.get(
        "BLOG_TOPIC",
        "marketing strategies to increase app users for Rentwix in India",
    )
    word_env = os.environ.get("POST_WORDS", "700").strip()
    word_target = int(word_env) if word_env.isdigit() else 700
    site_title = os.environ.get("SITE_TITLE", "Daily Blog")
    posts_per_day_env = os.environ.get("POSTS_PER_DAY", "5").strip()
    posts_per_day = int(posts_per_day_env) if posts_per_day_env.isdigit() else 5

    blogger_client_id = os.environ.get("BLOGGER_CLIENT_ID", "").strip()
    blogger_client_secret = os.environ.get("BLOGGER_CLIENT_SECRET", "").strip()
    blogger_refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN", "").strip()
    blogger_blog_id = os.environ.get("BLOGGER_BLOG_ID", "").strip()

    if not all(
        [blogger_client_id, blogger_client_secret, blogger_refresh_token, blogger_blog_id]
    ):
        raise SystemExit("Blogger secrets are required.")

    wp_site = os.environ.get("WP_SITE", "").strip()
    wp_username = os.environ.get("WP_USERNAME", "").strip()
    wp_app_password = os.environ.get("WP_APP_PASSWORD", "").strip()
    if not all([wp_site, wp_username, wp_app_password]):
        raise SystemExit("WordPress secrets are required.")

    today = datetime.now(timezone.utc).date()
    date_prefix = today.strftime("%Y-%m-%d")

    posts_dir = os.path.join(os.getcwd(), "_posts")
    os.makedirs(posts_dir, exist_ok=True)

    force_post = os.environ.get("FORCE_POST", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    todays_posts = [
        name
        for name in os.listdir(posts_dir)
        if name.startswith(date_prefix + "-") and name.endswith(".md")
    ]
    if not force_post and len(todays_posts) >= posts_per_day:
        print("Daily post limit reached. Exiting.")
        return

    download_link = (
        "https://play.google.com/store/apps/details?id=com.company.rentwix&pcampaignid=web_share"
    )

    prompt = (
        f"Write a blog post for {site_title}. Topic: {topic}.\n"
        f"Target length: about {word_target} words.\n"
        "Audience: India only. Brand: Rentwix (rental homes app).\n"
        "Every heading must explicitly include the word 'Rentwix'.\n"
        "The body should naturally mention 'Rentwix' multiple times (without keyword stuffing).\n"
        "Include these key benefits: verified listings, easy search, fast communication, modern renting.\n"
        f"Every post must include this exact download link once near the end: {download_link}\n"
        "Return ONLY valid JSON (no markdown, no code fences, no extra text) "
        "with keys: title and body. "
        "body must be Markdown and must NOT include an H1 title."
    )

    text_payload = call_gemini(
        api_key,
        text_model,
        [{"parts": [{"text": prompt}]}],
    )

    text_response = extract_text_from_response(text_payload)
    if not text_response:
        raise SystemExit("Empty response from Gemini text model.")

    try:
        data = parse_json_from_text(text_response)
        title = str(data.get("title", "")).strip()
        body = str(data.get("body", "")).strip()
    except ValueError:
        title = ""
        body = text_response

    if not body:
        body = text_response
    if not title:
        title, body = extract_title_from_body(body)
    if body.lstrip().startswith("#"):
        _, body = extract_title_from_body(body)
    if not title:
        title = f"Daily Post {date_prefix}"

    slug = slugify(title)
    filename = f"{date_prefix}-{slug}.md"
    filepath = os.path.join(posts_dir, filename)
    if force_post and os.path.exists(filepath):
        counter = 2
        while True:
            candidate = f"{date_prefix}-{slug}-{counter}.md"
            candidate_path = os.path.join(posts_dir, candidate)
            if not os.path.exists(candidate_path):
                filename = candidate
                filepath = candidate_path
                break
            counter += 1

    image_dir = os.path.join(os.getcwd(), "assets", "images")
    os.makedirs(image_dir, exist_ok=True)

    image_relpath = ""
    pool_dir = os.environ.get("IMAGE_POOL_DIR", "assets/random-images").strip()
    pool_abs = os.path.join(os.getcwd(), pool_dir)
    image_source = pick_random_image(pool_abs)
    if image_source:
        # Use the existing pool image so the URL is valid before commit.
        rel_from_root = os.path.relpath(image_source, os.getcwd()).replace("\\", "/")
        image_relpath = f"/{rel_from_root}"
        # Also copy into assets/images for local archive.
        _, ext = os.path.splitext(image_source)
        image_filename = f"{date_prefix}-{slug}{ext.lower()}"
        image_path = os.path.join(image_dir, image_filename)
        with open(image_source, "rb") as src, open(image_path, "wb") as dst:
            dst.write(src.read())

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

    repo_name = os.environ.get("GITHUB_REPOSITORY", "").strip()
    image_url = ""
    if repo_name and image_relpath:
        image_url = (
            f"https://raw.githubusercontent.com/{repo_name}/main"
            f"{image_relpath}"
        )

    html_body = markdown.markdown(body)
    if image_url:
        html_body = f'<p><img src="{image_url}" alt="{safe_title}"/></p>\n' + html_body

    access_token = fetch_blogger_access_token(
        blogger_client_id, blogger_client_secret, blogger_refresh_token
    )
    post_to_blogger(access_token, blogger_blog_id, safe_title, html_body)
    post_to_wordpress(wp_site, wp_username, wp_app_password, safe_title, html_body)

    print(f"Created {filepath}")


if __name__ == "__main__":
    main()
