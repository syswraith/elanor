---
title: Configuration
description: Customise Elanor's theme, site URL, Open Graph metadata, and build behaviour through config.json.
keywords: configuration, themes, config.json, open graph, site url, classless css
---

# Configuration

Elanor is configured through `assets/config.json`. If the file doesn't exist
when you run `main.py`, the interactive wizard creates it for you.

## config.json

```json
{
  "theme": "https://unpkg.com/sakura.css/css/sakura.css",
  "site_url": "https://yourusername.github.io/elanor",
  "og_image": "https://example.com/image.png"
}
```

| Key              | Required | Purpose                                                  |
|-----------------|----------|----------------------------------------------------------|
| `theme`         | **Yes**  | URL to a classless CSS stylesheet.                       |
| `site_url`      | No       | Base URL for canonical links and Open Graph metadata.    |
| `og_image`      | No       | Image URL for Open Graph / Twitter cards.                |
| `exclude_drafts`| No       | `true` (default) to skip `draft: true` notes.            |

## Choosing a theme

Elanor ships with 20 classless CSS themes in `assets/themes.json`:

| # | Theme           | Style                                    |
|---|----------------|------------------------------------------|
| 1 | awsm           | Clean, minimal, readable.                |
| 2 | bahunya        | Bold, high-contrast.                     |
| 3 | bamboo         | Natural, earthy tones.                   |
| 4 | bootstrap      | The classic Bootstrap look.              |
| 5 | holiday        | Bright and cheerful.                     |
| 6 | kacit          | Sharp, geometric.                        |
| 7 | minicss        | Lightweight utility framework.           |
| 8 | no-class       | Truly classless, true to the name.       |
| 9 | pico           | Modern, dark mode support.               |
| 10| sakura         | Elegant pink-accented default.           |
| 11| sakura-vader   | Sakura's dark side.                      |
| 12| simple         | Simple.css — minimal and accessible.     |
| 13| tacit          | Opinionated, zero-class.                 |
| 14| tufte          | Edward Tufte–inspired typography.        |
| 15| w3c-chocolate  | W3C Core Style — warm.                   |
| 16| w3c-traditional| W3C Core Style — classic.                |
| 17| water-dark     | Water.css dark mode.                     |
| 18| water-light    | Water.css light mode.                    |
| 19| writ           | Tiny, opinionated.                       |
| 20| yorha          | NieR: Automata–inspired.                 |

### Interactive selection

Run `main.py` without a `config.json` and it will prompt you:

```
Choose a theme:
  1: awsm
  2: bahunya
  ...
Your choice:
```

### Non-interactive (CI)

Set the `ELANOR_THEME` environment variable to the theme number:

```sh
ELANOR_THEME=10 python3 main.py
```

This writes `config.json` automatically and skips all prompts.

### Using a custom theme

You can use any classless CSS stylesheet. Just set `theme` to its URL:

```json
{
  "theme": "https://cdn.example.com/my-custom-theme.css"
}
```

The theme is loaded as a `<link rel="stylesheet">` — Elanor doesn't bundle or
process it.

## Site URL

The `site_url` value powers two things:

1. **Canonical links** — `<link rel="canonical">` on every page.
2. **Open Graph URLs** — `<meta property="og:url">` for rich link previews.

Set it to the root URL where your site will be served:

```json
{
  "site_url": "https://yourusername.github.io/elanor"
}
```

Leave it blank or omit it entirely if you don't need canonical URLs.

## Open Graph image

The `og_image` field sets the image used in social media previews. It can be:

- An absolute URL: `https://example.com/banner.png`
- A site-relative path: `images/banner.png` (resolved against `site_url`)

If omitted, Elanor falls back to the project icon on GitHub.

## The template

The HTML shell that wraps every page lives at `assets/template.html`. It's a
Jinja2 template with these variables:

| Variable        | Content                                       |
|----------------|-----------------------------------------------|
| `{{ theme }}`  | URL from `config.json`.                       |
| `{{ content }}`| The rendered HTML body of the note.            |
| `{{ prefix }}` | Relative path back to the site root (`../`).   |
| `{{ title }}`  | From frontmatter or filename.                 |
| `{{ lang }}`   | From frontmatter, defaults to `en`.           |
| `{{ author }}` | From frontmatter.                             |
| `{{ description }}` | From frontmatter or first paragraph.     |
| `{{ keywords }}`    | From frontmatter.                        |
| `{{ canonical }}`   | Full canonical URL.                      |
| `{{ og_image }}`    | Open Graph image URL.                    |
| `{{ katex_version }}`| KaTeX CDN version string.               |

You can edit this template to add a header, footer, navigation, analytics, or
anything else — Elanor will pick up your changes on the next build.

## Next steps

- [[Deployment]] — get your configured site live.
- [[Architecture]] — understand how Elanor processes your config.
