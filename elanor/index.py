import os
import posixpath
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from elanor.constants import CONTENT_DIR, GENERATED_DIR, MARKDOWN_SUFFIXES
from elanor.frontmatter import is_draft, meta_list, meta_value, parse_frontmatter
from elanor.fs import iter_sources
from elanor.utils import (
    normalise_key,
    page_slug,
    rel_href,
    slugify,
    split_wikilink,
    strip_markdown_suffix,
    strip_page_suffix,
)


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


def build_link_index(content_dir=None):
    if content_dir is None:
        content_dir = CONTENT_DIR

    index = LinkIndex()

    for rel_root, dirs, files in os.walk(content_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        folder_key = normalise_key(Path(rel_root).relative_to(content_dir).as_posix())
        if folder_key:
            index.add_folder(folder_key)

    for rel_root, file in iter_sources(content_dir):
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
    for rel_root, file in iter_sources(content_dir):
        if not file.lower().endswith(MARKDOWN_SUFFIXES):
            continue
        key = normalise_key(strip_markdown_suffix(
            normalise_key((rel_root / file).as_posix())
        ))
        if not key:
            continue
        try:
            text = (content_dir / rel_root / file).read_text(encoding='utf-8')
        except OSError:
            continue
        meta, _ = parse_frontmatter(text)
        for alias in meta_list(meta, 'alias', 'aliases'):
            index.add_alias(alias, key)

    return index


def assign_page_dirs(index, config, content_dir=None):
    """Choose an output directory for every page, keeping URLs slugged.

    A note at content/Blogs/Hello World.md is written to
    generated/Blogs/hello-world/index.html and reached as /blogs/hello-world/,
    which is what GitHub Pages serves from a directory index.

    Two notes can slug to the same name, so collisions get a numeric suffix
    rather than overwriting each other.
    """
    if content_dir is None:
        content_dir = CONTENT_DIR

    exclude_drafts = config.get('exclude_drafts', True)
    taken = set(index.folders)
    assigned = {}

    for rel_root, file in iter_sources(content_dir):
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
                (content_dir / rel_path).read_text(encoding='utf-8')
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
            if out_dir in assigned.values():
                continue
            assigned[key] = out_dir
            taken.add(out_dir)
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


def resolve_wikilink(source_dir, raw, index, out_dir='', generated_dir=None):
    """Resolve a wikilink target, returning (href, display, resolved_page).

    Tries, in order: relative to the containing file, relative to the content
    root, then by unique filename anywhere in the tree. That last rule is what
    Obsidian vaults assume, so links like [[Some Post]] keep working when the
    target lives in a subdirectory.

    resolved_page is the output file the link should point at, or None when the
    link is an anchor or an asset. None is also returned when the target cannot
    be resolved, in which case the caller leaves the wiki syntax as plain text.
    """
    if generated_dir is None:
        generated_dir = GENERATED_DIR

    target, anchor, display = split_wikilink(raw)
    target = normalise_key(target)
    source_key = normalise_key(source_dir.as_posix())
    page_dir = normalise_key(out_dir)

    def href_between(target_dir):
        if not target_dir:
            return './' if page_dir else ''
        return rel_href(target_dir, page_dir, trailing_slash=True)

    if not target:
        # [[#section]] points back into the page it is written on.
        if not anchor:
            return None, None, None
        return '#' + slugify(anchor), display or anchor, None

    stem = normalise_key(strip_page_suffix(target))
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
        asset_cand = beside(target)
        if asset_cand not in index.assets:
            asset_cand = normalise_key(target)
        if stem == normalise_key(target) and asset_cand in index.assets:
            label = display or PurePosixPath(asset_cand).name
            return rel_href(asset_cand, page_dir), label, None
        return None, None, None

    label = display or PurePosixPath(stem).name or stem
    href = href_between(resolved_dir)
    if anchor:
        href += '#' + slugify(anchor)

    return href, label, generated_dir / resolved_dir / 'index.html'
