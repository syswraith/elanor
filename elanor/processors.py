import posixpath
from urllib.parse import parse_qs, unquote, urlparse
from xml.etree import ElementTree

from markdown.inlinepatterns import InlineProcessor
from markdown.treeprocessors import Treeprocessor
from markdown_katex import KatexExtension

from elanor.constants import (
    EMBED_TRIGGER,
    VIDEO_ID_PATTERN,
    YOUTUBE_HOSTS,
    YOUTUBE_PATH_PREFIXES,
)
from elanor.index import LinkElement, resolve_wikilink
from elanor.utils import normalise_key, rel_href, slugify

EXTENSION_CONFIGS = {
    'markdown.extensions.toc': {'slugify': slugify, 'separator': '-'},
}


def katex_extension():
    # The kwarg must go on the instance: markdown only consults
    # extension_configs for extensions registered by name, so a config entry
    # for 'markdown_katex' would be silently ignored here.
    return KatexExtension(insert_fonts_css=False)


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


class WikilinkProcessor(InlineProcessor):
    """Expand [[wikilinks]] as real elements so link text stays markdown."""

    def __init__(self, pattern, md, source_dir, links, index, out_dir='', generated_dir=None):
        super().__init__(pattern, md)
        self.source_dir = source_dir
        self.links = links
        self.index = index
        self.out_dir = out_dir
        self.generated_dir = generated_dir

    def handleMatch(self, m, data):
        href, display, resolved = resolve_wikilink(
            self.source_dir, m.group(1), self.index, self.out_dir, self.generated_dir
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
        wrapper = ElementTree.Element('figure')
        wrapper.set('class', 'embed')

        stage = ElementTree.SubElement(wrapper, 'div')
        stage.set('class', 'embed-frame')

        frame = ElementTree.SubElement(stage, 'iframe')
        frame.set('src', f'https://www.youtube-nocookie.com/embed/{video}')
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
