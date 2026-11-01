---
title: Getting Started
description: Install Elanor, run your first build, and understand the project layout.
keywords: installation, setup, quickstart, project structure
---

# Getting Started

This guide walks you through installing Elanor, building your first site, and
understanding the files that make it tick.

## Prerequisites

| Dependency   | Version | Why                                           |
|-------------|---------|-----------------------------------------------|
| Python      | 3.10+   | Elanor is written in Python.                  |
| Node.js     | Any LTS | `markdown-katex` calls the KaTeX CLI at build.|
| pip / uv    | Latest  | To install Python packages.                   |

## Installation

```sh
git clone https://github.com/syswraith/elanor.git
cd elanor

# Option A: pip
python3 -m venv venv && source ./venv/bin/activate
pip install -r requirements.txt

# Option B: uv (faster)
uv venv venv && source ./venv/bin/activate
uv pip install -r requirements.txt
```

## Your first build

Create a `content/` directory next to `main.py` and add a Markdown file:

```
elanor/
├── content/
│   └── hello.md        ← your first note
├── assets/
│   ├── config.json
│   ├── template.html
│   └── themes.json
├── main.py
└── requirements.txt
```

Write something in `content/hello.md`:

```markdown
---
title: Hello World
---

# Hello World

This is my first Elanor page!
```

Then build:

```sh
python3 main.py
```

If `assets/config.json` doesn't exist yet, Elanor will prompt you to choose a
theme interactively. You can also set `ELANOR_THEME=10` (sakura) to skip the
prompt in CI.

The output lands in `generated/`:

```
generated/
├── hello-world/
│   └── index.html
├── index.html
├── pygments.css
└── favicon.ico
```

Every note becomes a directory with an `index.html` so URLs look clean:
`/hello-world/` instead of `/hello-world.html`.

## Project layout

| Path                    | Purpose                                                |
|------------------------|--------------------------------------------------------|
| `main.py`              | The entire generator — one file, no packages.          |
| `content/`             | Your Markdown notes and assets (images, PDFs, etc.).   |
| `generated/`           | Build output. Deployed to `gh-pages`.                  |
| `assets/config.json`   | Theme URL, site URL, Open Graph image.                 |
| `assets/template.html` | Jinja2 HTML shell that wraps every page.               |
| `assets/themes.json`   | Map of theme IDs to names and CDN URLs.                |
| `assets/config.py`     | Interactive config wizard (runs when config is missing).|
| `.elanor-manifest`     | Tracks generated files for incremental cleanup.        |

## Serving locally

Python's built-in HTTP server is the easiest way to preview:

```sh
python3 -m http.server -d generated
```

Then open [http://localhost:8000](http://localhost:8000).

## Next steps

- [[Writing Content]] — learn the Markdown extensions Elanor supports.
- [[Configuration]] — customise themes, metadata, and Open Graph tags.
