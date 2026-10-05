---
title: Elanor
description: Elanor is a minimalistic static site generator for Markdown files. Written in Python.
author: syswraith
keywords: elanor,syswraith,github,static site generator,python,python3,classless,css,minimal,installation,setup
---

![Elanor icon](https://github.com/syswraith/elanor/blob/main/assets/icon.png?raw=true)


# Requirements

Elanor needs **Python 3.10+** and **Node.js**. Node is a hard requirement of the
`markdown-katex` extension, which shells out to the KaTeX CLI to render math at
build time. If you do not write any math you can get away without it, but
install it anyway so builds do not fail the first time you add a formula.

# Installation


Clone the github repo and `cd` to it
```sh
git clone https://github.com/syswraith/elanor
cd elanor
```
Make a virtual environment and activate it
```sh
python3 -m venv venv && source ./venv/bin/activate
```
Install the required dependencies
```sh
pip install -r requirements.txt
```

# Setup

Your markdown files go inside the `content` directory. You may use nested directories to store them.
Any file in `content` that is not Markdown is copied through to `generated`
untouched, so images, SVG, CSS and PDFs all work without any extra configuration.

Wikilinks follow Obsidian's resolution rules, so links you already have in a
vault keep working:

```markdown
[[themes]]                   -> by unique filename anywhere in content
[[notes/release v1.2]]       -> relative to the file containing the link
[[notes/release v1.2|notes]] -> link text is whatever you put after the pipe
[[themes#my section]]        -> /themes/#my-section
[[#my section]]              -> anchor on the current page
[[notes/]]                    -> the folder's landing page
[[diagram.svg]]              -> links the file directly
```

A target is looked up relative to the current file, then relative to the content
root, then by unique filename, then by `aliases` in the note's frontmatter. If two
notes share a filename the link is ambiguous, so it is left as plain text instead
of guessing which one you meant.

Wiki syntax inside backticks or fenced code blocks is left alone, so documenting
your own links is safe. Anything that tries to escape the `content` directory is
left as plain text rather than turned into a link.

# URLs

Every note is served from its own directory, so URLs are readable and work on
GitHub Pages with no server config:

```
content/Blogs/Inside the CHIP-8 Virtual Machine.md
  -> generated/Blogs/inside-the-chip-8-virtual-machine/index.html
  -> /blogs/inside-the-chip-8-virtual-machine/
```

The slug comes from the note's `title`, falling back to its filename. Two notes
that slug identically get a `-2` suffix rather than overwriting each other, and
a note called `index.md` keeps its folder's URL so it acts as that folder's
landing page. Slugs keep non-ASCII characters, so a note titled `中文标题` gets
`/中文标题/`.

Folder indexes are generated for any content folder without its own `index.md`,
listing its notes and subfolders. A folder that holds only images gets no
spurious index page.

# Frontmatter

Frontmatter is parsed as YAML with `python-frontmatter`, so list values and real
booleans behave as you would expect:

```markdown
---
title: My note
description: Used for the meta description.
tags: [crypto, forensics]     -> becomes the page keywords
aliases: [/notes/]            -> [[/notes/]] links here
draft: true                   -> not published
---
```

`title`, `description`, `lang`, `author`, `keywords` and `tags` feed the page head.
Anything with `draft: true` or `publish: false` is left out of the build and
reported on stderr; set `"exclude_drafts": false` in `assets/config.json` to
publish drafts anyway. Invalid YAML does not stop the build: the note is rendered
with its frontmatter stripped and a warning is printed.

# Task lists

`- [x]` and `- [ ]` at the start of a list item become real checkboxes, as in
Obsidian. Elsewhere, such as `array[x]` inside a code block, the brackets are
left alone.

Once you're done, run `python3 main.py`. This generates the whole HTML tree into
`generated`, along with `pygments.css` and the favicon, so nothing needs to be
built by hand. If you rename or delete a Markdown file, its old HTML is removed on
the next run. Wikilinks that point at nothing are listed on stderr at the end of
the build.

# Configuration

Theme selection lives in `assets/config.json`. Delete that file and run `main.py`
to be asked again, or set `ELANOR_THEME` to the theme id from `assets/themes.json`
to choose non-interactively, which is what you want in CI.

```json
{
  "theme": "https://unpkg.com/sakura.css/css/sakura.css",
  "site_url": "https://example.com",
  "og_image": "https://example.com/icon.png"
}
```

`site_url` is used to build per-page `canonical` and `og:url` values, so every
page stops claiming to be the home page. `og_image` accepts an absolute URL or a
path relative to the site root.
