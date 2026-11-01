---
title: Writing Content
description: Markdown syntax, frontmatter fields, wikilinks, embeds, and everything else you can put in a note.
keywords: markdown, frontmatter, wikilinks, embeds, katex, math, syntax highlighting
---

# Writing Content

Elanor reads every `.md` and `.markdown` file in `content/`, converts it to
HTML, and writes the result to `generated/`. This page covers everything you
can do inside a note.

## Frontmatter

Every note can start with a YAML front matter block:

```yaml
---
title: My Page Title
description: A short summary for search engines and link previews.
keywords: foo, bar, baz
tags: [notes, demo]
author: Your Name
lang: en
draft: false
alias: [old-name, /legacy/path]
---
```

| Field         | Type           | Purpose                                              |
|--------------|----------------|------------------------------------------------------|
| `title`      | string         | Page `<title>` and heading. Falls back to filename.  |
| `description`| string         | `<meta>` description. Falls back to first paragraph. |
| `keywords`   | string or list | `<meta>` keywords. `tags` is accepted too.           |
| `author`     | string         | `<meta>` author.                                     |
| `lang`       | string         | `<html lang="">`. Defaults to `en`.                  |
| `draft`      | boolean        | `true` excludes the page from the build.             |
| `publish`    | boolean        | `false` excludes the page (Obsidian convention).     |
| `alias`      | string or list | Alternative names for wikilink resolution.           |

If frontmatter is malformed, Elanor warns but still builds the page — the
broken YAML block is stripped so it never leaks into the HTML.

## Basic Markdown

All standard Markdown works, plus these extensions:

### Fenced code blocks with syntax highlighting

````markdown
```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```
````

Syntax highlighting is powered by Pygments. The generated `pygments.css` is
included automatically.

### Tables

```markdown
| Column A | Column B |
|----------|----------|
| Cell 1   | Cell 2   |
```

### Table of contents

The `toc` extension is enabled. Use `[TOC]` in your Markdown to insert a
generated table of contents.

## KaTeX math

Elanor supports math in three forms:

### Display math (fenced)

````markdown
```math
E = mc^2
```
````

### Display math (dollar signs)

```markdown
$$
\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$
```

### Inline math

```markdown
The area of a circle is \(A = \pi r^2\).
```

Fenced `math` blocks and `` $`inline`$ `` syntax are rendered at build time by
the KaTeX CLI (requires Node.js). Dollar-sign display math and `\(...\)` inline
math are rendered client-side by the KaTeX JavaScript library.

## Wikilinks

Elanor resolves Obsidian-style `[[wikilinks]]`:

| Syntax                          | Result                                      |
|--------------------------------|---------------------------------------------|
| `[[Page Name]]`               | Links to the page titled "Page Name".       |
| `[[Page Name\|display text]]`  | Custom link text.                           |
| `[[Page Name#Heading]]`       | Deep link to a heading on the target page.  |
| `[[#Heading]]`                | Anchor link within the current page.        |
| `[[folder/note]]`             | Explicit path to a note in a subfolder.     |
| `[[image.png]]`               | Links to an asset file in the same folder.  |

Resolution order:

1. Relative to the current file's directory.
2. Relative to the content root.
3. By unique filename anywhere in the tree (Obsidian convention).
4. By frontmatter alias.

Unresolved wikilinks are left as plain text so you can spot them.

## Task lists

Standard GitHub-flavored task list syntax:

```markdown
- [x] Write documentation
- [ ] Deploy to GitHub Pages
- [ ] Celebrate
```

These render as real (disabled) checkboxes.

## YouTube embeds

Write a link labelled `embed` on its own line:

```markdown
[embed](https://www.youtube.com/watch?v=dQw4w9WgXcQ)
```

Elanor extracts the video ID from the URL and produces a responsive,
privacy-enhanced iframe (`youtube-nocookie.com`). Nothing is fetched at build
time, so builds work fully offline.

Supported URL formats:

- `https://www.youtube.com/watch?v=ID`
- `https://youtu.be/ID`
- `https://www.youtube.com/embed/ID`
- `https://www.youtube.com/shorts/ID`
- `https://music.youtube.com/watch?v=ID`

Any other URL is left as a normal link.

## Assets

Non-Markdown files in `content/` (images, PDFs, etc.) are copied to `generated/`
at their original relative path. Reference them with standard Markdown:

```markdown
![screenshot](images/screenshot.png)
```

Elanor rewrites relative paths so they resolve correctly from the page's output
directory.

## Subfolders and folder indexes

Organise notes into subdirectories:

```
content/
├── Guides/
│   ├── install.md
│   └── upgrade.md
└── index.md
```

Folders without an `index.md` get a generated listing page that links to every
note and subfolder inside them, so `[[Guides/]]`-style wikilinks always land
somewhere.

## Drafts

Mark a note as a draft to exclude it from the build:

```yaml
---
draft: true
---
```

Or, using the Obsidian convention:

```yaml
---
publish: false
---
```

Links to draft pages remain unresolved and are reported as broken in the build
output — useful for catching references to unpublished content.

## Next steps

- [[Configuration]] — themes, site URL, and Open Graph settings.
- [[Deployment]] — get your site live on GitHub Pages.
