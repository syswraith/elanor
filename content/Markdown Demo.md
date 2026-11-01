---
title: Markdown Feature Showcase
description: A live showcase demonstrating all Markdown extensions and features supported by Elanor.
keywords: demo, markdown, katex, wikilinks, syntax highlighting, tasks, embeds, tables
author: Elanor
alias: [feature-demo, markdown-features]
---

# Markdown Feature Showcase

This document demonstrates every Markdown feature and extension supported by Elanor — from syntax highlighting and mathematical typesetting to Obsidian-style wikilinks and responsive media embeds.

[TOC]

---

## Typography and Text Formatting

Elanor supports standard Markdown formatting, styled cleanly by your chosen classless CSS theme:

- **Bold text** with `**double asterisks**` or `__double underscores__`
- *Italic text* with `*single asterisks*` or `_single underscores_`
- ***Bold and italic text*** with `***triple asterisks***`
- ~~Strikethrough~~ with `~~double tildes~~`
- `Inline code snippets` with `` `backticks` ``
- Superscript and subscript where supported by standard HTML entities or math mode

### Blockquotes

> "All that is gold does not glitter,
> Not all those who wander are lost;
> The old that is strong does not wither,
> Deep roots are not reached by the frost."
>
> — *J.R.R. Tolkien, The Fellowship of the Ring*

Nested blockquotes are also fully supported:

> Multi-level blockquotes allow structuring commentaries or discussion threads:
>
> > This is a nested blockquote highlighting a supplementary observation.

---

## Lists and Task Lists

### Standard Lists

1. First ordered item
2. Second ordered item
   - Unordered sub-item A
   - Unordered sub-item B
     1. Nested ordered sub-point
     2. Another nested ordered sub-point
3. Third ordered item

### Interactive Task Lists

Elanor converts `- [ ]` and `- [x]` into styled HTML checkboxes with the `task-list-item-checkbox` class:

- [x] Initialise git repository and virtual environment
- [x] Install dependencies via `requirements.txt`
- [x] Configure classless CSS theme in `assets/config.json`
- [x] Author notes in `content/` with YAML frontmatter
- [ ] Deploy generated static site to GitHub Pages

---

## Code Blocks and Syntax Highlighting

Fenced code blocks are styled using **Pygments** with scoped `.codehilite` styles so they never conflict with your theme.

### Python

```python
from pathlib import Path
from elanor import build_link_index, assign_page_dirs

def generate_catalog(content_dir: Path) -> dict[str, str]:
    """Scan content directory and compute clean URL slugs."""
    index = build_link_index(content_dir)
    return assign_page_dirs(index, config={"exclude_drafts": True})

if __name__ == "__main__":
    catalog = generate_catalog(Path("content"))
    for key, out_dir in sorted(catalog.items()):
        print(f"/{key} -> /{out_dir}/")
```

### Rust

```rust
use std::collections::HashMap;

#[derive(Debug)]
pub struct Page {
    pub title: String,
    pub slug: String,
    pub published: bool,
}

fn main() {
    let mut catalog: HashMap<&str, Page> = HashMap::new();
    catalog.insert("demo", Page {
        title: String::from("Markdown Showcase"),
        slug: String::from("markdown-showcase"),
        published: true,
    });

    println!("Catalog: {:?}", catalog);
}
```

### Shell

```sh
# Build your site
source ./venv/bin/activate
python3 main.py

# Preview locally
python3 -m http.server 8000 --directory generated
```

---

## Mathematics (KaTeX)

Elanor renders math at **build time** using KaTeX CLI (`markdown_katex`), meaning zero client-side JavaScript overhead and full offline support.

### Inline Math

Einstein's mass–energy equivalence is given by $E = mc^2$.

Euler's identity, frequently called the most beautiful theorem in mathematics:

$$e^{i\pi} + 1 = 0$$

Gaussian integral over the real line:

$$\int_{-\infty}^{\infty} e^{-x^2} \, dx = \sqrt{\pi}$$

### Display Math Equations

Maxwell's equations in vacuum:

$$\begin{aligned}
\nabla \cdot \mathbf{E} &= \frac{\rho}{\varepsilon_0} \\
\nabla \cdot \mathbf{B} &= 0 \\
\nabla \times \mathbf{E} &= -\frac{\partial \mathbf{B}}{\partial t} \\
\nabla \times \mathbf{B} &= \mu_0 \mathbf{J} + \mu_0 \varepsilon_0 \frac{\partial \mathbf{E}}{\partial t}
\end{aligned}$$

A $3 \times 3$ matrix transformation:

$$\mathbf{A} = \begin{pmatrix}
a_{11} & a_{12} & a_{13} \\
a_{21} & a_{22} & a_{23} \\
a_{31} & a_{32} & a_{33}
\end{pmatrix}$$

---

## Tables

Standard GitHub-Flavored Markdown pipe tables with left, center, and right text alignment:

| Feature | Supported Syntax | Processor / Extension | Status |
| :--- | :---: | :--- | ---: |
| Wikilinks | `[[Target]]` | `WikilinkProcessor` | Active |
| Math Equations | `$...$` / `$$...$$` | `markdown_katex` | Active |
| Task Lists | `- [x]` / `- [ ]` | `TaskProcessor` | Active |
| Video Embeds | `[embed](url)` | `EmbedProcessor` | Active |
| Code Highlighting | ` ```lang ` | `codehilite` + Pygments | Active |
| Clean Slugs | `slugify()` | Built-in | Active |

---

## Obsidian-Style Wikilinks

Elanor provides deep integration with Obsidian-style internal links:

- **Direct note link**: [[Getting Started]]
- **Custom display text**: [[Writing Content|Comprehensive Authoring Guide]]
- **Deep link with heading anchor**: [[Architecture#Markdown extensions]]
- **In-page section jump**: [[#Typography and Text Formatting]]
- **Frontmatter alias resolution**: [[feature-demo]] (points back to this note via its `alias`)
- **File extension flexibility**: [[Deployment.md]] or [[Deployment.html]]

---

## Responsive Media Embeds

To embed a video, place a Markdown link labelled `embed` on its own line. Elanor extracts the video ID and renders a responsive, privacy-enhanced iframe (`youtube-nocookie.com`) wrapped in semantic `<figure>` and `<figcaption>` elements:

[embed](https://www.youtube.com/watch?v=dQw4w9WgXcQ)

---

## Navigation

- Return to [[Elanor|Home Page]]
- Read the [[Getting Started]] guide
- Consult [[Writing Content]] for authoring rules
- Review [[Configuration]] for theme options
- Inspect the underlying [[Architecture]]
