import json
import os
import posixpath
import re
import shutil
import sys
from html import unescape
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, quote, unquote, urlparse
from xml.etree import ElementTree

import frontmatter
import markdown
from jinja2 import Environment, FileSystemLoader
from markdown.inlinepatterns import InlineProcessor
from markdown.treeprocessors import Treeprocessor
from markdown_katex import KatexExtension
from pygments.formatters import HtmlFormatter

from assets import config as config_module

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / 'content'
GENERATED_DIR = ROOT / 'generated'
ASSETS_DIR = ROOT / 'assets'
CONFIG_PATH = ASSETS_DIR / 'config.json'
# Kept out of generated/ so it is never published to gh-pages.
MANIFEST_PATH = ROOT / '.elanor-manifest'

DEFAULT_OG_IMAGE = 'https://github.com/syswraith/elanor/blob/main/assets/icon.png?raw=true'
PYGMENTS_STYLE = 'default'
KATEX_VERSION = '0.16.8'
MARKDOWN_SUFFIXES = ('.md', '.markdown')
WIKILINK_PATTERN = r'\[\[([^\[\]\n]+)\]\]'
TASK_PATTERN = r'\[([ xX])\][ \t]+'
# Link text that opts a paragraph into the embed treatment.
EMBED_TRIGGER = 'embed'
# Embeds are built from an allowlist, never from fetched markup, so a video id
# only ever reaches an iframe src if it matches this exactly.
VIDEO_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{6,20}$')
YOUTUBE_HOSTS = (
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'music.youtube.com',
)
# Paths that carry the video id as a path segment, e.g. /shorts/ID.
YOUTUBE_PATH_PREFIXES = ('/embed/', '/v/', '/shorts/')


class LinkElement(ElementTree.Element):
    """An <a> whose href is already relative to the rendered page.

    resolve_wikilink builds hrefs from the page's output directory, whereas
    plain markdown links are relative to the source file, so the asset pass has
    to tell them apart. The flag lives on the Python object, so nothing is added
    to the published HTML.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_relative = True
FRONTMATTER_BLOCK = re.compile(
    r'\A---[ \t]*\r?\n.*?^---[ \t]*(?:\r?\n|\Z)',
    re.DOTALL | re.MULTILINE,
)
DESCRIPTION_LIMIT = 160
DEFAULT_LANG = 'en'

# frontmatter is parsed with python-frontmatter rather than markdown's meta
# extension, so YAML lists (tags) and real booleans (draft: false) survive.
MARKDOWN_EXTENSIONS = [
    'fenced_code',
    'codehilite',
    'markdown.extensions.tables',
    'markdown.extensions.toc',
]


def slugify(text, separator='-'):
    # Collapse runs of separators so "Foo - Part 1" does not become
    # "foo---part-1".
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[\s_-]+', separator, text)
    return text.strip(separator)


EXTENSION_CONFIGS = {
    'markdown.extensions.toc': {'slugify': slugify, 'separator': '-'},
}


def katex_extension():
    # The kwarg must go on the instance: markdown only consults
    # extension_configs for extensions registered by name, so a config entry
    # for 'markdown_katex' would be silently ignored here.
    return KatexExtension(insert_fonts_css=False)


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
    for suffix in MARKDOWN_SUFFIXES + ('.html', '.htm'):
        if target.lower().endswith(suffix):
            return target[:-len(suffix)]
    return target


def page_slug(title, stem):
    """URL slug for a note, derived from its title and falling back to its name.

    Non-ASCII characters are dropped by slugify, so a title that reduces to
    nothing falls back to the filename, then to 'untitled'.
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


class LinkIndex:
    """Maps link targets onto pages, mirroring how Obsidian resolves them."""

    def __init__(self):
        self.pages = {}
        self.assets = set()
        self.by_name = {}
        self.by_alias = {}
        self.folders = set()

    def add_page(self, key, out_dir):
        """key is the link target; out_dir is where the page is written."""
        self.pages[key] = out_dir
        name = PurePosixPath(key).name.lower()
        # A duplicated basename is ambiguous, so refuse to guess.
        self.by_name[name] = None if name in self.by_name else key

    def add_asset(self, key):
        self.assets.add(key)

    def add_folder(self, key):
        self.folders.add(key)

    def is_folder(self, key):
        return key in self.folders

    def add_alias(self, alias, key):
        # Obsidian aliases may be written as /ctfs/ or ctf; index both the raw
        # value and its stripped form, and never let an alias shadow a page.
        for form in {normalise_key(alias), normalise_key(alias.strip('/'))}:
            if not form or form in self.pages:
                continue
            self.by_alias[form.lower()] = None if form.lower() in self.by_alias else key

    def lookup_name(self, name):
        return self.by_name.get(name.lower())

    def lookup_alias(self, alias):
        return self.by_alias.get(normalise_key(alias).lower())


def build_link_index():
    index = LinkIndex()

    for rel_root, dirs, files in os.walk(CONTENT_DIR):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        folder_key = normalise_key(Path(rel_root).relative_to(CONTENT_DIR).as_posix())
        if folder_key:
            index.add_folder(folder_key)

    for rel_root, file in iter_sources():
        key = normalise_key((rel_root / file).as_posix())
        if not key:
            continue
        if file.lower().endswith(MARKDOWN_SUFFIXES):
            index.add_page(normalise_key(strip_markdown_suffix(key)), None)
        else:
            index.add_asset(key)

    # Folders get a generated index unless the vault supplies its own, so
    # [[Braindev/]] has somewhere to point. Register those as pages up front:
    # the link index is built before anything is rendered.
    for folder in list(index.folders):
        if normalise_key(f'{folder}/index') in index.pages:
            continue
        index.add_page(normalise_key(f'{folder}/index'), folder)

    # Aliases let [[some other name]] reach a page, as in Obsidian.
    for rel_root, file in iter_sources():
        if not file.lower().endswith(MARKDOWN_SUFFIXES):
            continue
        key = normalise_key(strip_markdown_suffix(
            normalise_key((rel_root / file).as_posix())
        ))
        if not key:
            continue
        try:
            text = (CONTENT_DIR / rel_root / file).read_text(encoding='utf-8')
        except OSError:
            continue
        meta, _ = parse_frontmatter(text)
        for alias in meta_list(meta, 'alias', 'aliases'):
            index.add_alias(alias, key)

    return index


def assign_page_dirs(index, config):
    """Choose an output directory for every page, keeping URLs slugged.

    A note at content/Blogs/Hello World.md is written to
    generated/Blogs/hello-world/index.html and reached as /blogs/hello-world/,
    which is what GitHub Pages serves from a directory index.

    Two notes can slug to the same name, so collisions get a numeric suffix
    rather than overwriting each other.
    """
    exclude_drafts = config.get('exclude_drafts', True)
    taken = set(index.folders)
    assigned = {}

    for rel_root, file in iter_sources():
        if not file.lower().endswith(MARKDOWN_SUFFIXES):
            continue
        rel_path = rel_root / file
        key = normalise_key(strip_markdown_suffix(
            normalise_key(rel_path.as_posix())
        ))
        if not key:
            continue

        try:
            meta, _ = parse_frontmatter(
                (CONTENT_DIR / rel_path).read_text(encoding='utf-8')
            )
        except OSError:
            continue

        if exclude_drafts and is_draft(meta):
            # Leave it unassigned: links to it then resolve to nothing and the
            # broken-link report surfaces them, instead of pointing at a page
            # that was never written.
            continue

        # A note named index.md *is* its folder's landing page, so it keeps
        # the folder URL rather than getting an /index/ directory of its own.
        if rel_path.stem.lower() == 'index' and key.split('/')[-1].lower() == 'index':
            out_dir = rel_root.as_posix()
            if out_dir in taken and out_dir not in index.pages.values():
                continue
            assigned[key] = out_dir
            continue

        slug = page_slug(meta_value(meta, 'title'), rel_path.stem)
        base = posixpath.join(rel_root.as_posix(), slug) if rel_root.parts else slug
        candidate = normalise_key(base)
        suffix = 2
        while candidate in taken:
            candidate = normalise_key(f'{base}-{suffix}')
            suffix += 1
        taken.add(candidate)
        assigned[key] = candidate

    for key, out_dir in assigned.items():
        index.pages[key] = out_dir

    return assigned


def resolve_wikilink(source_dir, raw, index, out_dir=''):
    """Resolve a wikilink target, returning (href, display, resolved_page).

    Tries, in order: relative to the containing file, relative to the content
    root, then by unique filename anywhere in the tree. That last rule is what
    Obsidian vaults assume, so links like [[Some Post]] keep working when the
    target lives in a subdirectory.

    resolved_page is the output file the link should point at, or None when the
    link is an anchor or an asset. None is also returned when the target cannot
    be resolved, in which case the caller leaves the wiki syntax as plain text.
    """
    target, anchor, display = split_wikilink(raw)
    target = normalise_key(target)
    source_key = normalise_key(source_dir.as_posix())
    page_dir = normalise_key(out_dir)

    # A sibling note written to the same slug should link to itself, not to
    # the site root, which is what an empty relpath collapses to.
    def href_between(target_dir):
        if not target_dir:
            return './' if page_dir else ''
        return rel_href(target_dir, page_dir, trailing_slash=True)

    if not target:
        # [[#section]] points back into the page it is written on.
        if not anchor:
            return None, None, None
        return '#' + slugify(anchor), display or anchor, None

    stem = normalise_key(strip_markdown_suffix(target))
    if not stem or stem.split('/')[0] == '..':
        return None, None, None

    def beside(rel):
        return normalise_key(posixpath.join(source_key, rel)) if source_key else rel

    # Lookups are by source path; the href is built from output directories.
    candidates = [beside(stem), stem]
    by_name = index.lookup_name(PurePosixPath(stem).name)
    if by_name:
        candidates.append(by_name)

    resolved_dir = None
    for candidate in candidates:
        candidate_dir = index.pages.get(candidate)
        if candidate_dir is not None:
            resolved_dir = candidate_dir
            break

    if resolved_dir is None:
        # Last resort: a frontmatter alias, e.g. [[/ctfs/]].
        aliased = index.lookup_alias(stem)
        if aliased:
            resolved_dir = index.pages.get(aliased)

    if resolved_dir is None:
        # [[Braindev/]] points at a folder's generated index page.
        for candidate in candidates:
            if index.is_folder(candidate):
                resolved_dir = candidate
                break

    if resolved_dir is None:
        # Assets keep their source paths, so href them from the page's own
        # output directory rather than from its source folder.
        asset_key = beside(target)
        if stem != normalise_key(target) or asset_key not in index.assets:
            return None, None, None
        label = display or PurePosixPath(asset_key).name
        return rel_href(asset_key, page_dir), label, None

    label = display or PurePosixPath(stem).name or stem
    href = href_between(resolved_dir)
    if anchor:
        href += '#' + slugify(anchor)

    return href, label, GENERATED_DIR / resolved_dir / 'index.html'


class WikilinkProcessor(InlineProcessor):
    """Expand [[wikilinks]] as real elements so link text stays markdown."""

    def __init__(self, pattern, md, source_dir, links, index, out_dir=''):
        super().__init__(pattern, md)
        self.source_dir = source_dir
        self.links = links
        self.index = index
        self.out_dir = out_dir

    def handleMatch(self, m, data):
        href, display, resolved = resolve_wikilink(
            self.source_dir, m.group(1), self.index, self.out_dir
        )
        if href is None:
            return None, None, None

        if resolved is not None:
            self.links.append((resolved, m.group(1).strip()))

        el = LinkElement('a')
        el.set('href', href)
        # Deliberately a plain str: the inline treeprocessor recurses into it so
        # [[**bold** page]] renders <strong>bold</strong>.
        el.text = display
        return el, m.start(0), m.end(0)


class AssetPathProcessor(Treeprocessor):
    """Re-point relative image and asset paths at the page's output directory.

    Markdown resolves ![](images/x.png) relative to the file that wrote it, but
    a note is served from <slug>/index.html, one level deeper than its source
    folder. Rewrite the path so it still lands on the copied asset.
    """

    ATTRS = (('img', 'src'), ('source', 'src'), ('video', 'src'), ('audio', 'src'))

    def __init__(self, md, source_dir, page_dir):
        super().__init__(md)
        self.source_dir = source_dir
        self.page_dir = page_dir

    def rewrite(self, element, attr):
        value = element.get(attr)
        if not value or value.startswith(('http://', 'https://', '//', 'data:', '#')):
            return

        key = value.split('#')[0].split('?')[0]
        if not key:
            return

        # The source may already be percent-encoded; decode before rebuilding so
        # the path is not encoded twice.
        asset_key = normalise_key(
            posixpath.join(self.source_dir.as_posix(), unquote(key))
            if self.source_dir.parts else unquote(key)
        )
        suffix = value[len(key):]
        element.set(attr, rel_href(asset_key, self.page_dir) + suffix)

    def run(self, root):
        for tag, attr in self.ATTRS:
            for element in root.iter(tag):
                self.rewrite(element, attr)

        # Plain [markdown](notes/other.md) links are also relative to the
        # source file. Wikilinks are already absolute-from-page, so they are
        # tagged and skipped here.
        for element in root.iter('a'):
            if getattr(element, 'page_relative', False):
                continue
            href = element.get('href')
            if not href or href.startswith(
                ('http://', 'https://', '//', 'mailto:', '#')
            ):
                continue
            self.rewrite(element, 'href')


class TaskProcessor(InlineProcessor):
    """Render `- [x]` / `- [ ]` list items as real checkboxes."""

    def handleMatch(self, m, data):
        # Only at the very start of a list item, so prose like "[x] means
        # checked" is left alone.
        if m.start(0) != 0:
            return None, None, None

        el = ElementTree.Element('input')
        el.set('type', 'checkbox')
        el.set('disabled', 'disabled')
        if m.group(1).lower() == 'x':
            el.set('checked', 'checked')
        el.set('class', 'task-list-item-checkbox')

        return el, m.start(0), m.end(0)


def video_id(url):
    """The video id of a supported provider URL, or None.

    Only YouTube is supported. Nothing is fetched: the id is read out of the URL
    so builds stay offline and deterministic. Returning None for anything
    unrecognised is what lets an unknown [embed] target fall back to a plain
    link.
    """
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None

    if parsed.scheme not in ('http', 'https'):
        return None

    host = parsed.netloc.lower().split(':')[0]
    candidate = None

    if host == 'youtu.be':
        # youtu.be/<id>, optionally followed by a timestamp segment.
        candidate = parsed.path.lstrip('/').split('/')[0]
    elif host in YOUTUBE_HOSTS:
        if parsed.path == '/watch':
            candidate = parse_qs(parsed.query).get('v', [None])[0]
        else:
            for prefix in YOUTUBE_PATH_PREFIXES:
                if parsed.path.startswith(prefix):
                    candidate = parsed.path[len(prefix):].split('/')[0]
                    break

    # Validate before it is ever placed in an attribute. Anything that is not a
    # bare video id is treated as unsupported rather than embedded.
    if candidate and VIDEO_ID_PATTERN.match(candidate):
        return candidate
    return None


class EmbedProcessor(Treeprocessor):
    """Turn `[embed](url)` paragraphs into responsive player iframes.

    Runs at priority 15: after the inline processors (20) have already turned
    the directive into an <a>, but before the asset pass (1), so the paragraph
    is replaced before anything tries to rewrite its href.

    The trigger is the ordinary markdown link syntax, so the built-in link
    processor handles escaping and autolinks. This only needs to recognise a
    paragraph whose entire content is one link labelled `embed`.

    Elements are built directly instead of stashing raw HTML, so the serializer
    escapes every attribute and no fetched or user markup bypasses escaping.
    """

    def run(self, root):
        # Collect first, then mutate: iter() is lazy, so inserting or removing
        # children while walking would corrupt the traversal.
        targets = []
        for parent in root.iter():
            for child in parent:
                target = self.match(child)
                if target is not None:
                    targets.append((parent, child, target))

        for parent, paragraph, video in targets:
            index = list(parent).index(paragraph)
            parent.remove(paragraph)
            parent.insert(index, self.build_embed(video))

    def match(self, paragraph):
        """Return the video id if paragraph is an embed directive, else None."""
        if paragraph.tag != 'p':
            return None

        children = list(paragraph)
        if len(children) != 1 or children[0].tag != 'a':
            return None

        link = children[0]
        if ''.join(link.itertext()).strip().lower() != EMBED_TRIGGER:
            return None

        # Reject "[embed](url) and some prose": the anchor has to be the whole
        # paragraph, so surrounding text keeps the link intact.
        if (paragraph.text or '').strip() or (link.tail or '').strip():
            return None

        return video_id(link.get('href') or '')

    def build_embed(self, video):
        # <figure> rather than a div, so figcaption is valid inside it.
        wrapper = ElementTree.Element('figure')
        wrapper.set('class', 'embed')

        # The ratio is held by an inner box so the caption can sit below the
        # player instead of overlapping it.
        stage = ElementTree.SubElement(wrapper, 'div')
        stage.set('class', 'embed-frame')

        frame = ElementTree.SubElement(stage, 'iframe')
        frame.set('src', f'https://www.youtube-nocookie.com/embed/{video}')
        # The title is what a screen reader announces for the frame, so it has
        # to name the content rather than repeat the word "video".
        frame.set('title', 'YouTube video player')
        frame.set('loading', 'lazy')
        frame.set('allow', 'accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture')
        frame.set('allowfullscreen', 'allowfullscreen')
        frame.set('referrerpolicy', 'strict-origin-when-cross-origin')

        caption = ElementTree.SubElement(wrapper, 'figcaption')
        link = ElementTree.SubElement(caption, 'a')
        link.set('href', f'https://www.youtube.com/watch?v={video}')
        link.set('rel', 'noopener noreferrer')
        link.set('target', '_blank')
        link.text = 'Watch on YouTube'

        return wrapper


def read_config():
    if not CONFIG_PATH.is_file():
        config_module.config(ASSETS_DIR)

    try:
        with open(CONFIG_PATH, encoding='utf-8') as config_file:
            config = json.load(config_file)
    except OSError as exc:
        sys.exit(f'error: could not read {CONFIG_PATH}: {exc}')
    except json.JSONDecodeError as exc:
        sys.exit(f'error: {CONFIG_PATH} is not valid JSON: {exc}')

    if not isinstance(config, dict):
        sys.exit(f'error: {CONFIG_PATH} must contain a JSON object')

    theme = config.get('theme')
    if not isinstance(theme, str) or not theme.strip():
        sys.exit(f'error: {CONFIG_PATH} is missing a "theme" entry')

    return config


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


_FRONTMATTER_WARNINGS = set()


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


def first_paragraph(html_body):
    match = re.search(r'<p>(.*?)</p>', html_body, re.DOTALL)
    if not match:
        return ''
    # Unescape here and let Jinja do the escaping exactly once.
    text = unescape(re.sub(r'<[^>]+>', '', match.group(1)))
    return ' '.join(text.split())


def write_pygments_css():
    formatter = HtmlFormatter(style=PYGMENTS_STYLE)
    # Scoped to .codehilite: pygmentize emits bare `.c`/`.k`/`.err` selectors
    # that leak onto every element on the page and override the classless theme.
    (GENERATED_DIR / 'pygments.css').write_text(
        formatter.get_style_defs('.codehilite') + '\n', encoding='utf-8'
    )


def copy_file(src_path, dest_path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest_path)
    return dest_path


def iter_sources():
    if not CONTENT_DIR.is_dir():
        return

    for root, dirs, files in os.walk(CONTENT_DIR):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        rel_root = Path(root).relative_to(CONTENT_DIR)

        for file in sorted(files):
            if file.startswith('.'):
                continue
            yield rel_root, file


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


def is_excluded_asset(rel_path):
    # Elanor owns the .html extension: a stray one in content is a build
    # artifact, not something to republish next to the generated page.
    return rel_path.suffix.lower() in ('.html', '.htm')


def prune(previous, current):
    stale = sorted(previous - current)
    for rel_path in stale:
        stale_path = GENERATED_DIR / rel_path
        if stale_path.is_file():
            stale_path.unlink()
            print(f'removed stale {stale_path.relative_to(ROOT)}')

    for root, dirs, files in os.walk(GENERATED_DIR, topdown=False):
        if Path(root) == GENERATED_DIR:
            continue
        if not dirs and not files:
            Path(root).rmdir()


def has_notes(directory):
    """True when a directory holds Markdown directly or one level down."""
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return False

    for path in entries:
        if path.is_file() and not path.name.startswith('.') \
                and path.name.lower().endswith(MARKDOWN_SUFFIXES):
            return True
    return any(
        path.is_dir() and not path.name.startswith('.') and has_notes(path)
        for path in entries
    )


def folder_pages(rel_dir):
    """Markdown notes directly inside a content folder, in a stable order.

    Used to generate an index.html for folders that lack one so that
    [[Braindev/]] style links land somewhere real.
    """
    source = CONTENT_DIR / rel_dir
    if not source.is_dir():
        return []
    return [
        rel_dir / path.name
        for path in sorted(source.iterdir())
        if not path.name.startswith('.') and path.is_file()
        and path.name.lower().endswith(MARKDOWN_SUFFIXES)
    ]


def folder_title(rel_dir):
    if not rel_dir.parts:
        return 'Notes'
    name = rel_dir.name.replace('-', ' ').replace('_', ' ')
    return name[:1].upper() + name[1:]


def render_folder_list(items, subfolders, rel_dir):
    """Build the folder landing page body.

    Returns HTML rather than markdown so it cannot be re-parsed, and is marked
    safe by the template.
    """
    # A folder index lives at <folder>/index.html, so relative links are built from
    # the folder itself.
    source = rel_dir.as_posix()
    parts = []

    if subfolders:
        parts.append('<h2>Folders</h2>')
        parts.append('<ul>')
        for folder in subfolders:
            href = rel_href(folder, source, trailing_slash=True)
            parts.append(f'<li><a href="{href}">{PurePosixPath(folder).name}/</a></li>')
        parts.append('</ul>')

    parts.append('<h2>Notes</h2>')
    parts.append('<ul>')
    for note in items:
        href = rel_href(note['out_dir'], source, trailing_slash=True)
        parts.append(f'<li><a href="{href}">{note["title"]}</a></li>')
    parts.append('</ul>')

    return '\n'.join(parts)


def build_folder_indexes(config, template, written, links, index):
    """Generate index.html for every content folder that has no index note.

    A folder without an index still needs a landing page: GitHub Pages serves
    /Braindev/ from Braindev/index.html, and vault wikilinks like
    [[Braindev/|Braindev]] depend on it.

    Asset-only folders (images/, .obsidian/) are skipped: they hold no notes,
    so a listing would be empty and only add noise to the output.
    """
    exclude_drafts = config.get('exclude_drafts', True)
    count = 0

    for rel_root, dirs, files in os.walk(CONTENT_DIR):
        rel_dir = Path(rel_root).relative_to(CONTENT_DIR)
        if any(name.startswith('.') for name in files):
            continue
        if any(file.lower() == 'index.md' for file in files):
            # The vault provides its own landing page; leave it alone.
            continue

        notes = folder_pages(rel_dir)
        subfolders = sorted(
            name
            for name in dirs
            if not name.startswith('.')
            # Skip image and config folders: no notes live there, so an index
            # page would just be an empty list.
            and has_notes(CONTENT_DIR / rel_dir / name)
        )
        if not notes and not subfolders:
            # Nothing to list: no notes here and no note-bearing subfolders.
            continue

        items = []
        for note in notes:
            meta, _ = parse_frontmatter(
                (CONTENT_DIR / note).read_text(encoding='utf-8')
            )
            if exclude_drafts and is_draft(meta):
                continue
            out_dir = index.pages.get(
                normalise_key(strip_markdown_suffix(note.as_posix()))
            )
            if out_dir is None:
                # A draft that was skipped, so it is not in the index.
                continue
            items.append({
                'out_dir': out_dir,
                'title': meta_value(meta, 'title') or note.stem,
            })

        subfolder_paths = [(rel_dir / name).as_posix() for name in subfolders]

        if not items and not subfolder_paths:
            continue

        out_path = GENERATED_DIR / rel_dir / 'index.html'
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


def build(config, template):
    written = set()
    links = []
    skipped = []

    index = build_link_index()
    assign_page_dirs(index, config)
    exclude_drafts = config.get('exclude_drafts', True)

    for rel_root, file in iter_sources():
        rel_path = rel_root / file

        if not file.lower().endswith(MARKDOWN_SUFFIXES):
            if is_excluded_asset(rel_path):
                skipped.append((rel_path.as_posix(), 'html is generated, not content'))
                continue
            copy_file(CONTENT_DIR / rel_path, GENERATED_DIR / rel_path)
            written.add(rel_path.as_posix())
            continue

        with open(CONTENT_DIR / rel_path, encoding='utf-8') as input_file:
            text = input_file.read()

        meta, body = parse_frontmatter(text)

        if exclude_drafts and is_draft(meta):
            skipped.append((rel_path.as_posix(), 'marked as draft/unpublished'))
            continue

        out_dir = index.pages.get(
            normalise_key(strip_markdown_suffix(rel_path.as_posix()))
        )
        if out_dir is None:
            # Draft, or a slug that lost its directory to a collision.
            skipped.append((rel_path.as_posix(), 'no output directory assigned'))
            continue

        out_path = GENERATED_DIR / out_dir / 'index.html'

        md = markdown.Markdown(
            extensions=MARKDOWN_EXTENSIONS + [katex_extension()],
            extension_configs=EXTENSION_CONFIGS,
        )
        md.inlinePatterns.register(
            WikilinkProcessor(
                WIKILINK_PATTERN, md, rel_root, links, index, out_dir
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
        # Above the asset pass so the directive's paragraph is replaced before
        # anything rewrites its href.
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
            # The page is written to out_dir/index.html, so climbing back to
            # generated/ takes one step per component of out_dir.
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
        written.add(out_path.relative_to(GENERATED_DIR).as_posix())

    folder_indexes = build_folder_indexes(config, template, written, links, index)

    write_pygments_css()
    written.add('pygments.css')

    for asset in sorted(ASSETS_DIR.glob('favicon.*')):
        copy_file(asset, GENERATED_DIR / asset.name)
        written.add(asset.name)

    return written, links, skipped, folder_indexes


def report_skipped(skipped):
    if not skipped:
        return
    print('\nskipped:')
    for rel_path, reason in sorted(skipped):
        print(f'  {rel_path} ({reason})', file=sys.stderr)


def report_broken_links(links):
    broken = {}
    for resolved, raw in links:
        if not resolved.is_file():
            broken.setdefault(resolved, set()).add(raw)

    if not broken:
        return

    print('\nbroken wikilinks:', file=sys.stderr)
    for resolved in sorted(broken):
        targets = ', '.join(sorted(f'[[{raw}]]' for raw in broken[resolved]))
        print(
            f'  {resolved.relative_to(ROOT)} <- {targets}',
            file=sys.stderr,
        )


def read_manifest():
    if not MANIFEST_PATH.is_file():
        return set()
    return {
        line.strip()
        for line in MANIFEST_PATH.read_text(encoding='utf-8').splitlines()
        if line.strip()
    }


def write_manifest(written):
    MANIFEST_PATH.write_text(
        ''.join(f'{rel_path}\n' for rel_path in sorted(written)),
        encoding='utf-8',
    )


def main():
    config = read_config()

    # autoescape matters here: title/description/author land inside attribute
    # values, and frontmatter is attacker-adjacent input.
    env = Environment(loader=FileSystemLoader(str(ASSETS_DIR)), autoescape=True)
    template = env.get_template('template.html')

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    previous = read_manifest()

    written, links, skipped, folder_indexes = build(config, template)

    prune(previous, written)
    write_manifest(written)
    report_skipped(skipped)
    report_broken_links(links)

    detail = f' ({folder_indexes} folder index)' if folder_indexes else ''
    print(f'built {len(written)} file(s){detail} into {GENERATED_DIR.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
