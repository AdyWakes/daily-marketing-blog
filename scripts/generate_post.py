import base64
import json
import os
import re
from datetime import datetime, timezone

import markdown
import requests


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


def extract_inline_image(payload: dict) -> tuple[str, str]:
    candidates = payload.get("candidates", [])
    if not candidates:
        return "", ""
    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if not inline:
            continue
        data = inline.get("data", "")
        mime_type = inline.get("mimeType") or inline.get("mime_type", "")
        if data:
            return data, mime_type
    return "", ""


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


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required.")

    text_model = os.environ.get("GEMINI_TEXT_MODEL", "").strip() or "gemini-2.5-flash"
    image_model = (
        os.environ.get("GEMINI_IMAGE_MODEL", "").strip()
        or "gemini-2.5-flash-image"
    )
    topic = os.environ.get(
        "BLOG_TOPIC", "marketing strategies to increase app users"
    )
    word_env = os.environ.get("POST_WORDS", "700").strip()
    word_target = int(word_env) if word_env.isdigit() else 700
    site_title = os.environ.get("SITE_TITLE", "Daily Blog")

    blogger_client_id = os.environ.get("BLOGGER_CLIENT_ID", "").strip()
    blogger_client_secret = os.environ.get("BLOGGER_CLIENT_SECRET", "").strip()
    blogger_refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN", "").strip()
    blogger_blog_id = os.environ.get("BLOGGER_BLOG_ID", "").strip()

    if not all(
        [blogger_client_id, blogger_client_secret, blogger_refresh_token, blogger_blog_id]
    ):
        raise SystemExit("Blogger secrets are required.")

    today = datetime.now(timezone.utc).date()
    date_prefix = today.strftime("%Y-%m-%d")

    posts_dir = os.path.join(os.getcwd(), "_posts")
    os.makedirs(posts_dir, exist_ok=True)

    for name in os.listdir(posts_dir):
        if name.startswith(date_prefix + "-") and name.endswith(".md"):
            print("Post already exists for today. Exiting.")
            return

    prompt = (
        f"Write a blog post for {site_title}. Topic: {topic}.\n"
        f"Target length: about {word_target} words.\n"
        "Return a JSON object with keys: title and body.\n"
        "body must be Markdown (no code fences)."
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
        data = json.loads(text_response)
        title = str(data.get("title", "")).strip() or f"Daily Post {date_prefix}"
        body = str(data.get("body", "")).strip() or text_response
    except json.JSONDecodeError:
        title = f"Daily Post {date_prefix}"
        body = text_response

    slug = slugify(title)
    filename = f"{date_prefix}-{slug}.md"
    filepath = os.path.join(posts_dir, filename)

    image_dir = os.path.join(os.getcwd(), "assets", "images")
    os.makedirs(image_dir, exist_ok=True)

    image_prompt = (
        "Create a clean, modern, marketing-themed hero image for a blog post. "
        f"Topic: {topic}. "
        "Style: minimal, high-contrast, professional, no text, no logos, "
        "no brand names, no watermarks."
    )

    image_payload = call_gemini(
        api_key,
        image_model,
        [{"parts": [{"text": image_prompt}]}],
    )

    image_data, image_mime = extract_inline_image(image_payload)
    if not image_data:
        raise SystemExit("No image returned from Gemini image model.")

    ext = "png"
    if image_mime.endswith("jpeg"):
        ext = "jpg"
    elif image_mime.endswith("webp"):
        ext = "webp"

    image_filename = f"{date_prefix}-{slug}.{ext}"
    image_relpath = f"/assets/images/{image_filename}"
    image_path = os.path.join(image_dir, image_filename)

    with open(image_path, "wb") as handle:
        handle.write(base64.b64decode(image_data))

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
    if repo_name:
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

    print(f"Created {filepath}")


if __name__ == "__main__":
    main()
