---
title: Elanor
description: A minimalistic static site generator that turns Markdown into beautiful, classless-CSS-styled pages.
keywords: elanor, static site generator, markdown, python, classless css
---

# Elanor

Elanor is a minimalistic static site generator built for Markdown. Written in
Python, it converts a folder of Markdown files into a clean, navigable website
styled entirely with [classless CSS](https://github.com/dbohdan/classless-css)
— no build tooling, no component frameworks, just your words.

## Features

- **Markdown with batteries** — fenced code blocks, syntax highlighting, tables,
  and a table of contents, all out of the box.
- **KaTeX math** — inline and display math rendered at build time via the KaTeX
  CLI, so pages load fast and work offline.
- **Obsidian-style wikilinks** — `[[Page]]`, `[[Page|display text]]`, and
  `[[Page#heading]]` all resolve automatically.
- **Task lists** — `- [x]` and `- [ ]` become real checkboxes.
- **YouTube embeds** — write `[embed](https://youtube.com/watch?v=...)` on its
  own line and get a responsive, privacy-enhanced iframe.
- **Frontmatter** — YAML front matter for titles, descriptions, tags, aliases,
  drafts, and more.
- **20 classless CSS themes** — pick one at setup time; switch any time by
  editing a single JSON value.
- **Folder indexes** — directories without an `index.md` get a generated listing
  page so every folder is reachable.
- **Incremental cleanup** — stale output files from previous builds are pruned
  automatically.
- **GitHub Pages deploy** — ships with a CI workflow that builds and pushes to
  `gh-pages` on every commit to `main`.

## Quick start

```sh
# Clone the repo
git clone https://github.com/syswraith/elanor.git
cd elanor

# Create a virtualenv and install dependencies
python3 -m venv venv && source ./venv/bin/activate
pip install -r requirements.txt

# Build the site
python3 main.py
```

The generated site lands in `generated/`. Open `generated/index.html` in a
browser or serve it with `python3 -m http.server -d generated`.

## Requirements

- **Python 3.10+**
- **Node.js** — required by `markdown-katex`, which shells out to the KaTeX CLI
  at build time.

## Learn more

- [[Getting Started]] — installation, first build, and project layout.
- [[Writing Content]] — Markdown syntax, frontmatter, wikilinks, and embeds.
- [[Configuration]] — themes, site URL, Open Graph, and `config.json`.
- [[Deployment]] — GitHub Pages workflow and manual deploy.
- [[Architecture]] — how Elanor's build pipeline works under the hood.

---

*Elanor was named after Elanor Gardner — the first daughter of Samwise Gamgee,
to whom he gave the Red Book of Westmarch before he sailed away to Valinor.*
