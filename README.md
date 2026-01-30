# Daily AI Blog on GitHub Pages

This repo is set up to publish a daily AI-generated blog post using GitHub Actions,
and host it for free on GitHub Pages.

## How it works
- GitHub Actions runs on a daily schedule (UTC).
- The workflow calls the OpenAI API to generate a post.
- A new Markdown file is created in `_posts/`.
- A hero image is generated and saved to `assets/images/`.
- GitHub Pages builds the site with Jekyll and publishes it.

## Required GitHub Secrets
Set these in your repo: Settings → Secrets and variables → Actions → New repository secret.

- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (optional, default `gpt-4o-mini`)
- `BLOG_TOPIC` (optional, e.g. `AI productivity tips`)
- `POST_WORDS` (optional, default `700`)

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
