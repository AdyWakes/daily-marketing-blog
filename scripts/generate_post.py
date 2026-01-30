import json
import os
import re
from datetime import datetime, timezone

import requests


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "daily-post"


def extract_text(payload: dict) -> str:
    if isinstance(payload, dict) and payload.get("output_text"):
        return str(payload["output_text"]).strip()

    texts = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            ctype = content.get("type")
            if ctype in ("output_text", "text"):
                text = content.get("text", "")
                if text:
                    texts.append(text)
    return "\n".join(texts).strip()


def parse_json_from_text(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
    raise ValueError("Could not parse JSON from model response")


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required.")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    topic = os.environ.get("BLOG_TOPIC", "practical AI tips for everyday work")
    word_target = int(os.environ.get("POST_WORDS", "700"))
    site_title = os.environ.get("SITE_TITLE", "Daily AI Blog")

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
        "Return a JSON object with keys: title, body.\n"
        "body must be Markdown (no code fences)."
    )

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": prompt,
        },
        timeout=60,
    )

    if response.status_code >= 400:
        raise SystemExit(
            f"OpenAI API error {response.status_code}: {response.text}"
        )

    payload = response.json()
    text = extract_text(payload)
    if not text:
        raise SystemExit("Empty response from model.")

    try:
        data = parse_json_from_text(text)
        title = str(data.get("title", "")).strip() or f"Daily Post {date_prefix}"
        body = str(data.get("body", "")).strip() or text
    except ValueError:
        title = f"Daily Post {date_prefix}"
        body = text

    slug = slugify(title)
    filename = f"{date_prefix}-{slug}.md"
    filepath = os.path.join(posts_dir, filename)

    front_matter = (
        "---\n"
        f"title: \"{title.replace('\"', '')}\"\n"
        f"date: {today.isoformat()}\n"
        "layout: post\n"
        "---\n\n"
    )

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(front_matter)
        handle.write(body)
        handle.write("\n")

    print(f"Created {filepath}")


if __name__ == "__main__":
    main()
