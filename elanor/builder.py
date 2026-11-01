import os
import sys
from html import escape
from pathlib import Path, PurePosixPath

import markdown
from pygments.formatters import HtmlFormatter

from elanor.constants import (
    ASSETS_DIR,
    CONTENT_DIR,
    DEFAULT_LANG,
    DESCRIPTION_LIMIT,
    GENERATED_DIR,
    KATEX_VERSION,
    MARKDOWN_EXTENSIONS,
    MARKDOWN_SUFFIXES,
    PYGMENTS_STYLE,
    ROOT,
    TASK_PATTERN,
    WIKILINK_PATTERN,
)
from elanor.frontmatter import (
    first_paragraph,
    is_draft,
    meta_value,
    parse_frontmatter,
)
from elanor.fs import (
    copy_file,
    folder_pages,
    folder_title,
    has_notes,
    is_excluded_asset,
    iter_sources,
)
from elanor.index import assign_page_dirs, build_link_index
from elanor.processors import (
    EXTENSION_CONFIGS,
    AssetPathProcessor,
    EmbedProcessor,
    TaskProcessor,
    WikilinkProcessor,
    katex_extension,
)
from elanor.utils import (
    normalise_key,
    og_image_for,
    rel_href,
    site_url_for,
    strip_markdown_suffix,
)


def write_pygments_css(generated_dir=None):
    if generated_dir is None:
        generated_dir = GENERATED_DIR
    formatter = HtmlFormatter(style=PYGMENTS_STYLE)
    (generated_dir / 'pygments.css').write_text(
        formatter.get_style_defs('.codehilite') + '\n', encoding='utf-8'
    )


def render_folder_list(items, subfolders, rel_dir):
    """Build the folder landing page body.

    Returns HTML rather than markdown so it cannot be re-parsed, and is marked
    safe by the template.
    """
    source = rel_dir.as_posix()
    parts = []

    if subfolders:
        parts.append('<h2>Folders</h2>')
        parts.append('<ul>')
        for folder in subfolders:
            href = rel_href(folder, source, trailing_slash=True)
            parts.append(f'<li><a href="{href}">{escape(PurePosixPath(folder).name)}/</a></li>')
        parts.append('</ul>')

    parts.append('<h2>Notes</h2>')
    parts.append('<ul>')
    for note in items:
        href = rel_href(note['out_dir'], source, trailing_slash=True)
        parts.append(f'<li><a href="{href}">{escape(note["title"])}</a></li>')
    parts.append('</ul>')

    return '\n'.join(parts)


def build_folder_indexes(config, template, written, links, index, content_dir=None, generated_dir=None):
    """Generate index.html for every content folder that has no index note."""
    if content_dir is None:
        content_dir = CONTENT_DIR
    if generated_dir is None:
        generated_dir = GENERATED_DIR

    exclude_drafts = config.get('exclude_drafts', True)
    count = 0

    for rel_root, dirs, files in os.walk(content_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        rel_dir = Path(rel_root).relative_to(content_dir)
        if any(file.lower() == 'index.md' for file in files):
            # The vault provides its own landing page; leave it alone.
            continue

        notes = folder_pages(rel_dir, content_dir)
        subfolders = sorted(
            name
            for name in dirs
            if not name.startswith('.')
            and has_notes(content_dir / rel_dir / name)
        )
        if not notes and not subfolders:
            continue

        items = []
        for note in notes:
            meta, _ = parse_frontmatter(
                (content_dir / note).read_text(encoding='utf-8')
            )
            if exclude_drafts and is_draft(meta):
                continue
            out_dir = index.pages.get(
                normalise_key(strip_markdown_suffix(note.as_posix()))
            )
            if out_dir is None:
                continue
            items.append({
                'out_dir': out_dir,
                'title': meta_value(meta, 'title') or note.stem,
            })

        subfolder_paths = [(rel_dir / name).as_posix() for name in subfolders]

        if not items and not subfolder_paths:
            continue

        out_path = generated_dir / rel_dir / 'index.html'
        rendered = template.render(
            theme=config['theme'],
            content=render_folder_list(items, subfolder_paths, rel_dir),
            prefix='../' * len(rel_dir.parts),
            title=folder_title(rel_dir),
            lang=DEFAULT_LANG,
            author='',
            description=f'Notes in {rel_dir.as_posix()}',
            keywords='',
            canonical=site_url_for(config, rel_dir.as_posix()),
            og_image=og_image_for(config),
            katex_version=KATEX_VERSION,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding='utf-8')
        written.add((rel_dir / 'index.html').as_posix())
        count += 1

    return count


def build(config, template, content_dir=None, generated_dir=None, assets_dir=None):
    if content_dir is None:
        content_dir = CONTENT_DIR
    if generated_dir is None:
        generated_dir = GENERATED_DIR
    if assets_dir is None:
        assets_dir = ASSETS_DIR

    written = set()
    links = []
    skipped = []

    index = build_link_index(content_dir)
    assign_page_dirs(index, config, content_dir)
    exclude_drafts = config.get('exclude_drafts', True)

    for rel_root, file in iter_sources(content_dir):
        rel_path = rel_root / file

        if not file.lower().endswith(MARKDOWN_SUFFIXES):
            if is_excluded_asset(rel_path):
                skipped.append((rel_path.as_posix(), 'html is generated, not content'))
                continue
            copy_file(content_dir / rel_path, generated_dir / rel_path)
            written.add(rel_path.as_posix())
            continue

        with open(content_dir / rel_path, encoding='utf-8') as input_file:
            text = input_file.read()

        meta, body = parse_frontmatter(text)

        if exclude_drafts and is_draft(meta):
            skipped.append((rel_path.as_posix(), 'marked as draft/unpublished'))
            continue

        out_dir = index.pages.get(
            normalise_key(strip_markdown_suffix(rel_path.as_posix()))
        )
        if out_dir is None:
            skipped.append((rel_path.as_posix(), 'no output directory assigned'))
            continue

        out_path = generated_dir / out_dir / 'index.html'

        md = markdown.Markdown(
            extensions=MARKDOWN_EXTENSIONS + [katex_extension()],
            extension_configs=EXTENSION_CONFIGS,
        )
        md.inlinePatterns.register(
            WikilinkProcessor(
                WIKILINK_PATTERN, md, rel_root, links, index, out_dir, generated_dir
            ),
            'wikilink',
            175,
        )
        md.inlinePatterns.register(TaskProcessor(TASK_PATTERN, md), 'tasklist', 180)
        md.treeprocessors.register(
            AssetPathProcessor(md, rel_root, out_dir),
            'elanor-assets',
            1,
        )
        md.treeprocessors.register(EmbedProcessor(md), 'elanor-embed', 15)

        html_body = md.convert(body)

        title = meta_value(meta, 'title') or rel_path.stem
        lang = meta_value(meta, 'lang') or DEFAULT_LANG
        description = meta_value(meta, 'description') or first_paragraph(html_body)
        if len(description) > DESCRIPTION_LIMIT:
            description = description[:DESCRIPTION_LIMIT].rstrip() + '\u2026'

        rendered = template.render(
            theme=config['theme'],
            content=html_body,
            prefix='../' * len(Path(out_dir).parts),
            lang=lang,
            title=title,
            author=meta_value(meta, 'author'),
            description=description,
            keywords=meta_value(meta, 'keywords') or meta_value(meta, 'tags'),
            canonical=site_url_for(config, out_dir),
            og_image=og_image_for(config),
            katex_version=KATEX_VERSION,
        )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding='utf-8')
        written.add(out_path.relative_to(generated_dir).as_posix())

    folder_indexes = build_folder_indexes(
        config, template, written, links, index, content_dir, generated_dir
    )

    write_pygments_css(generated_dir)
    written.add('pygments.css')

    for asset in sorted(assets_dir.glob('favicon.*')):
        copy_file(asset, generated_dir / asset.name)
        written.add(asset.name)

    return written, links, skipped, folder_indexes


def report_skipped(skipped):
    if not skipped:
        return
    print('\nskipped:', file=sys.stderr)
    for rel_path, reason in sorted(skipped):
        print(f'  {rel_path} ({reason})', file=sys.stderr)


def report_broken_links(links, root_dir=None):
    if root_dir is None:
        root_dir = ROOT

    broken = {}
    for resolved, raw in links:
        if not resolved.is_file():
            broken.setdefault(resolved, set()).add(raw)

    if not broken:
        return

    print('\nbroken wikilinks:', file=sys.stderr)
    for resolved in sorted(broken):
        targets = ', '.join(sorted(f'[[{raw}]]' for raw in broken[resolved]))
        rel = resolved.relative_to(root_dir) if resolved.is_relative_to(root_dir) else resolved
        print(
            f'  {rel} <- {targets}',
            file=sys.stderr,
        )
