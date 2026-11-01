import re
import sys
from html import unescape

import frontmatter

from elanor.constants import FRONTMATTER_BLOCK

_FRONTMATTER_WARNINGS = set()


def clear_frontmatter_warnings():
    _FRONTMATTER_WARNINGS.clear()


def parse_frontmatter(text):
    """Split YAML frontmatter off the body, tolerating malformed input.

    python-frontmatter raises on invalid YAML, but one broken note should not
    abort the build. On failure, strip the frontmatter block by hand so the
    raw YAML does not leak into the rendered page.
    """
    try:
        metadata, body = frontmatter.parse(text)
        return metadata or {}, body
    except Exception as error:
        # The same note is parsed up to three times per build (link index,
        # folder index, render), so warn once per distinct message.
        warn = f'invalid frontmatter: {error}'
        if warn not in _FRONTMATTER_WARNINGS:
            _FRONTMATTER_WARNINGS.add(warn)
            print(f'  ! {warn}', file=sys.stderr)

    # Locate the block by hand: --- (or ...) on the first line, --- to close.
    match = FRONTMATTER_BLOCK.match(text)
    if not match:
        return {}, text
    return {}, text[match.end():].lstrip('\n')


def meta_value(meta, key, default=''):
    """Read a frontmatter value as display text.

    YAML hands back real types: lists (tags), bools, dates and even the
    occasional nested mapping. Flatten all of them to a string.
    """
    if key not in meta:
        return default

    value = meta[key]
    if value is None:
        return default
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (list, tuple, set)):
        parts = [str(item).strip() for item in value]
        return ' '.join(part for part in parts if part)
    if isinstance(value, dict):
        return ' '.join(f'{k} {v}'.strip() for k, v in value.items())

    return str(value).strip()


def meta_list(meta, *keys):
    """Collect list-valued frontmatter (aliases, tags) as a list of strings."""
    values = []
    for key in keys:
        value = meta.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            values.extend(str(item).strip() for item in value)
        else:
            values.append(str(value).strip())
    return [item for item in values if item]


def is_draft(meta):
    """True when frontmatter marks a file as not-for-publication."""
    if meta.get('draft') is True:
        return True
    if meta.get('publish') is False:
        return True
    # Accept the string forms Obsidian's UI writes.
    if meta_value(meta, 'draft').strip().lower() in ('true', 'yes', '1'):
        return True
    return meta_value(meta, 'publish').strip().lower() in ('false', 'no', '0')


def first_paragraph(html_body):
    match = re.search(r'<p>(.*?)</p>', html_body, re.DOTALL)
    if not match:
        return ''
    # Unescape here and let Jinja do the escaping exactly once.
    text = unescape(re.sub(r'<[^>]+>', '', match.group(1)))
    return ' '.join(text.split())
