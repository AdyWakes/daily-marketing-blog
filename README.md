# Daily AI Blog on GitHub Pages

This repo is set up to publish a daily blog post from your prewritten drafts using
GitHub Actions, and host it for free on GitHub Pages.

## How it works
- GitHub Actions runs on a daily schedule (UTC).
- The workflow takes one Markdown file from `drafts/`.
- A new Markdown file is created in `_posts/`.
- If you add images to `drafts/images/`, one image is picked at random and copied
  to `assets/images/`.
- GitHub Pages builds the site with Jekyll and publishes it.

## Drafts format
- Put drafts in `drafts/` as `.md` files.
- The first non-empty line becomes the title (or add YAML front matter `title:`).
- Optional images:
  - Put images in `drafts/images/`.
  - Add `image: random` in the draft front matter to force a random image.
  - If no `image` is specified, the workflow still uses a random image if available.

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
