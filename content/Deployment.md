---
title: Deployment
description: Deploy your Elanor site to GitHub Pages automatically or manually.
keywords: deployment, github pages, ci, github actions, ghp-import
---

# Deployment

Elanor ships with a GitHub Actions workflow that builds and deploys to GitHub
Pages on every push to `main`. You can also deploy manually.

## Automatic deploy (GitHub Actions)

The workflow lives at `.github/workflows/deploy.yml` and does four things:

1. Checks out the repository.
2. Installs Python and the project's dependencies.
3. Runs `python main.py` to generate the site.
4. Pushes the `generated/` directory to the `gh-pages` branch.

### Setup

1. Go to your repo's **Settings → Pages**.
2. Set the source to **Deploy from a branch**.
3. Set the branch to `gh-pages` and the folder to `/ (root)`.
4. Push a commit to `main` — the workflow runs and your site goes live.

Your site will be available at:

```
https://<username>.github.io/<repo>/
```

### The workflow file

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install -r requirements.txt ghp-import

      - run: python main.py

      - env:
          GIT_AUTHOR_NAME: github-actions[bot]
          GIT_AUTHOR_EMAIL: 41898282+github-actions[bot]@users.noreply.github.com
          GIT_COMMITTER_NAME: github-actions[bot]
          GIT_COMMITTER_EMAIL: 41898282+github-actions[bot]@users.noreply.github.com
        run: |
          git config --global user.name "$GIT_AUTHOR_NAME"
          git config --global user.email "$GIT_AUTHOR_EMAIL"
          ghp-import -n -f generated
          git push -f https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${{ github.repository }} gh-pages
```

Key details:

- **`ghp-import -n`** adds a `.nojekyll` file so GitHub Pages serves the site
  as-is, without running Jekyll.
- **`-f`** force-pushes to `gh-pages` — the branch is always a clean snapshot
  of `generated/`.
- **`permissions: contents: write`** is required for the bot to push.

### Non-interactive theme

The workflow doesn't have a terminal, so if `config.json` doesn't exist yet,
set the `ELANOR_THEME` environment variable in the workflow:

```yaml
      - run: python main.py
        env:
          ELANOR_THEME: 10
```

This auto-creates `config.json` with the selected theme and skips the
interactive prompt.

## Manual deploy

If you prefer not to use CI:

```sh
# 1. Build
python3 main.py

# 2. Install ghp-import
pip install ghp-import

# 3. Push to gh-pages
ghp-import -n -f generated
git push -f origin gh-pages
```

Or simply copy the contents of `generated/` to any static file host (Netlify,
Cloudflare Pages, a VPS with nginx, etc.).

## Custom domain

To use a custom domain with GitHub Pages:

1. Add a `CNAME` file to `content/` containing your domain:
   ```
   docs.example.com
   ```
   Elanor copies non-Markdown files as-is, so it will end up in `generated/`.

2. Configure your DNS to point at GitHub Pages
   ([GitHub's guide](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)).

3. Update `site_url` in `config.json`:
   ```json
   {
     "site_url": "https://docs.example.com"
   }
   ```

## Next steps

- [[Architecture]] — understand the build pipeline under the hood.
- [[Configuration]] — fine-tune your `config.json`.
