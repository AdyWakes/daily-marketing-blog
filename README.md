# Daily AI Blog on GitHub Pages

This repo is set up to publish a daily Gemini-generated blog post to Blogger using
GitHub Actions.

## How it works
- GitHub Actions runs on a daily schedule (UTC).
- The workflow calls the Gemini API to generate a post.
- A new Markdown file is created in `_posts/` for archive.
- A hero image is copied from `assets/random-images/` to `assets/images/`.
- The post is published to Blogger.

## Required GitHub Secrets
Set these in your repo: Settings → Secrets and variables → Actions → New repository secret.

- `GEMINI_API_KEY` (required)
- `GEMINI_TEXT_MODEL` (optional, default `gemini-2.5-flash`)
- `BLOG_TOPIC` (optional, e.g. `marketing strategies to increase app users`)
- `POST_WORDS` (optional, default `700`)
- `BLOGGER_CLIENT_ID` (required)
- `BLOGGER_CLIENT_SECRET` (required)
- `BLOGGER_REFRESH_TOKEN` (required)
- `BLOGGER_BLOG_ID` (required)

## Images
Add any images to `assets/random-images/`. One will be chosen at random per post.

## GitHub Pages setup
1. In repo settings: Pages → Source = `Deploy from a branch`.
2. Branch = `main`, folder = `/ (root)`.
3. Save. Wait for the Pages build to complete.

## Custom domain
GitHub Pages lets you use a custom domain, but you still need to buy the domain
from a registrar. Hosting is free.

If you want a free URL, use the default:
`https://<your-username>.github.io/<repo-name>/`

## Local preview (optional)
If you want to preview locally:
1. Install Ruby + Jekyll.
2. Run: `bundle exec jekyll serve`
