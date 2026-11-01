import posixpath
import re
from urllib.parse import quote

from elanor.constants import DEFAULT_OG_IMAGE, MARKDOWN_SUFFIXES, PAGE_SUFFIXES


def slugify(text, separator='-'):
    # Collapse runs of separators so "Foo - Part 1" does not become
    # "foo---part-1".
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[\s_-]+', separator, text)
    return text.strip(separator)


def page_slug(title, stem):
    """URL slug for a note, derived from its title and falling back to its name.

    If slugify reduces a candidate to the empty string the next candidate is
    tried, falling back to 'untitled'.
    """
    for candidate in (title, stem):
        slug = slugify(str(candidate or ''))
        if slug:
            return slug
    return 'untitled'


def normalise_key(value):
    """Normalise a link target to a content-relative posix path, or ''."""
    value = value.strip().replace('\\', '/')
    while value.startswith('./'):
        value = value[2:]
    value = posixpath.normpath(value)
    if value in ('.', '/'):
        return ''
    return value.lstrip('/')


def quote_path(rel_path):
    return '/'.join(quote(part) for part in rel_path.split('/'))


def rel_href(out_key, source_key, trailing_slash=False):
    """Build an href from source_key (dir of the page) to out_key.

    source_key is the output directory the *current page* is served from, which
    is the directory holding its index.html, not the source folder. trailing_slash
    is for directory-style URLs: a page written to Blogs/post/index.html is
    reached as Blogs/post/, which is what GitHub Pages serves.
    """
    rel = posixpath.relpath(out_key, source_key or '.')

    if rel == '.':
        # Self-link: keep it inside the current directory rather than letting
        # an empty path collapse to the site root.
        return './' if trailing_slash else ''

    href = quote_path(rel)
    if trailing_slash:
        href = href.rstrip('/') + '/'
    return href


def split_wikilink(raw):
    raw, _, display = raw.partition('|')
    target, _, anchor = raw.partition('#')
    return target.strip(), anchor.strip(), display.strip()


def strip_markdown_suffix(target):
    lowered = target.lower()
    for suffix in MARKDOWN_SUFFIXES:
        if lowered.endswith(suffix):
            return target[:-len(suffix)]
    return target


def strip_page_suffix(target):
    """Drop a page suffix so [[note.md]] and [[note.html]] both resolve.

    Assets are matched separately against the original target, so this only
    affects how a link names a Markdown page.
    """
    lowered = target.lower()
    for suffix in PAGE_SUFFIXES:
        if lowered.endswith(suffix):
            return target[:-len(suffix)]
    return target


def site_url_for(config, out_dir):
    """Canonical URL for a page served from out_dir/index.html."""
    site_url = (config.get('site_url') or '').strip().rstrip('/')
    if not site_url:
        return ''
    rel_path = normalise_key(out_dir).strip('/')
    if not rel_path:
        return f'{site_url}/'
    return f'{site_url}/{quote_path(rel_path)}/'


def og_image_for(config):
    og_image = (config.get('og_image') or DEFAULT_OG_IMAGE).strip()
    if og_image.startswith(('http://', 'https://', '//')):
        return og_image

    site_url = (config.get('site_url') or '').strip().rstrip('/')
    if not site_url:
        return og_image
    return f'{site_url}/{og_image.lstrip("/")}'
