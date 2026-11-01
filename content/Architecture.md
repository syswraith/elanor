---
title: Architecture
description: How Elanor's modular build pipeline turns a folder of Markdown into a static site.
keywords: architecture, build pipeline, internals, link index, wikilinks, markdown extensions, modular design
---

# Architecture

Elanor is organized into a clean, modular Python package (`elanor`) with `main.py` serving as the top-level CLI entry point.
This page explains how the codebase is structured and how the build pipeline works.

## Codebase structure

The implementation is split across dedicated modules with clear responsibilities:

- **`elanor/constants.py`** — path configurations, regex patterns, and default settings.
- **`elanor/utils.py`** — slug generation, key normalisation, and relative URL calculation.
- **`elanor/frontmatter.py`** — frontmatter parsing, metadata extraction, draft checking, and summary generation.
- **`elanor/fs.py`** — source file iteration, asset copying, folder title derivation, and manifest/pruning operations.
- **`elanor/index.py`** — `LinkIndex` model, directory assignment, and wikilink resolution.
- **`elanor/processors.py`** — Python-Markdown tree and inline processors (wikilinks, tasks, embeds, asset paths).
- **`elanor/builder.py`** — core site build loop, folder index generator, and reporting.
- **`elanor/cli.py`** — configuration loader and command-line execution entry point.
- **`main.py`** — top-level executable entry point and backwards-compatible namespace re-export.

## Build pipeline overview

```
content/          elanor.builder       generated/
  *.md    ──────►    build()   ──────►   */index.html
  images/                                images/
  ...                                    pygments.css
                                         favicon.ico
```

The `main()` function runs these steps in order:

1. **Read config** — load `assets/config.json` (or run the wizard).
2. **Load template** — parse `assets/template.html` with Jinja2.
3. **Build link index** — scan `content/` to map every page, asset, folder,
   and alias.
4. **Assign output directories** — choose a slug-based output path for each
   page, resolving collisions.
5. **Render pages** — convert each Markdown file to HTML with all extensions.
6. **Build folder indexes** — generate listing pages for folders without
   `index.md`.
7. **Write assets** — copy `pygments.css` and `favicon.*`.
8. **Prune stale files** — remove outputs from previous builds that no longer
   have a source.
9. **Write manifest** — record all generated files for the next prune pass.
10. **Report** — print broken wikilinks and skipped files.

## The link index

Before any page is rendered, Elanor walks the entire `content/` tree and builds
a `LinkIndex` — a data structure that maps every possible link target to its
output location:

- **`pages`** — maps content-relative keys (like `guides/install`) to output
  directories (like `guides/install`).
- **`assets`** — the set of non-Markdown files.
- **`by_name`** — maps bare filenames to their full keys, for Obsidian-style
  `[[note]]` links that skip the path. Ambiguous names (duplicates) resolve to
  `None`.
- **`by_alias`** — maps frontmatter `alias` values to page keys.
- **`folders`** — the set of content subdirectories.

This index is what makes wikilinks work: `[[Some Post]]` is looked up against
`by_name`, and `[[guides/install]]` is looked up against `pages`.

## URL structure

Elanor writes every page to `<slug>/index.html` so URLs are clean:

```
content/Blogs/Hello World.md
  → generated/blogs/hello-world/index.html
  → served at /blogs/hello-world/
```

The slug is derived from the `title` frontmatter field, falling back to the
filename. Non-ASCII characters are dropped, and collisions get a numeric suffix
(`-2`, `-3`, etc.).

A file named `index.md` keeps its folder's URL rather than getting nested
further.

## Markdown extensions

Elanor configures Python-Markdown with these extensions:

| Extension               | Purpose                                    |
|------------------------|--------------------------------------------|
| `fenced_code`          | ` ``` ` code blocks.                       |
| `codehilite`           | Pygments syntax highlighting.              |
| `markdown.extensions.tables` | Pipe tables.                          |
| `markdown.extensions.toc`   | `[TOC]` and heading anchors.          |
| `markdown_katex`       | Server-side KaTeX rendering.               |

On top of these, Elanor registers custom processors:

### WikilinkProcessor (inline, priority 175)

Matches `[[...]]` and resolves them through the link index. Produces
`LinkElement` nodes (a subclass of `<a>`) tagged with `page_relative = True`
so the asset path rewriter knows to skip them.

### TaskProcessor (inline, priority 180)

Matches `[x]` and `[ ]` at the start of list items and replaces them with
real `<input type="checkbox">` elements.

### EmbedProcessor (tree, priority 15)

Finds paragraphs whose only child is a link labelled `embed`, extracts the
YouTube video ID from the URL, and replaces the paragraph with a responsive
`<figure>` containing a privacy-enhanced iframe.

### AssetPathProcessor (tree, priority 1)

Rewrites relative `src` and `href` attributes on images, videos, audio, and
plain links so they resolve correctly from the page's output directory rather
than its source directory.

## Incremental cleanup

Elanor writes a `.elanor-manifest` file listing every generated path. On the
next build, any files in the old manifest that aren't in the new one are
deleted, and empty directories are removed. This keeps `generated/` clean
without requiring a full wipe between builds.

## Frontmatter handling

Frontmatter is parsed with `python-frontmatter`, which preserves YAML types
(lists for tags, booleans for draft flags). If the YAML is malformed, Elanor
warns on stderr but still builds the page — the raw frontmatter block is
stripped by regex so it never appears in the rendered HTML.

## Security

- **Jinja2 autoescape** is enabled. Frontmatter values (title, description,
  author) are escaped before they reach HTML attributes.
- **Embeds** are built from an allowlist of video ID patterns, never from
  fetched markup. The video ID regex (`^[A-Za-z0-9_-]{6,20}$`) ensures only
  safe values reach an `iframe src`.
- **HTML files** in `content/` are excluded from the build to prevent
  publishing stray build artifacts.
