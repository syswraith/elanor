import os
import shutil
from pathlib import Path

from elanor.constants import CONTENT_DIR, GENERATED_DIR, MANIFEST_PATH, MARKDOWN_SUFFIXES, ROOT


def iter_sources(content_dir=None):
    if content_dir is None:
        content_dir = CONTENT_DIR
    if not content_dir.is_dir():
        return

    for root, dirs, files in os.walk(content_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        rel_root = Path(root).relative_to(content_dir)

        for file in sorted(files):
            if file.startswith('.'):
                continue
            yield rel_root, file


def copy_file(src_path, dest_path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest_path)
    return dest_path


def is_excluded_asset(rel_path):
    # Elanor owns the .html extension: a stray one in content is a build
    # artifact, not something to republish next to the generated page.
    return rel_path.suffix.lower() in ('.html', '.htm')


def has_notes(directory):
    """True when a directory holds Markdown directly or in any subdirectory."""
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


def folder_pages(rel_dir, content_dir=None):
    """Markdown notes directly inside a content folder, in a stable order.

    Used to generate an index.html for folders that lack one so that
    [[Braindev/]] style links land somewhere real.
    """
    if content_dir is None:
        content_dir = CONTENT_DIR
    source = content_dir / rel_dir
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
    name = rel_dir.name.replace('-', ' ').replace('_', ' ').strip()
    return (name[:1].upper() + name[1:]) if name else 'Notes'


def read_manifest(manifest_path=None):
    if manifest_path is None:
        manifest_path = MANIFEST_PATH
    if not manifest_path.is_file():
        return set()
    return {
        line.strip()
        for line in manifest_path.read_text(encoding='utf-8').splitlines()
        if line.strip()
    }


def write_manifest(written, manifest_path=None):
    if manifest_path is None:
        manifest_path = MANIFEST_PATH
    manifest_path.write_text(
        ''.join(f'{rel_path}\n' for rel_path in sorted(written)),
        encoding='utf-8',
    )


def prune(previous, current, generated_dir=None, root_dir=None):
    if generated_dir is None:
        generated_dir = GENERATED_DIR
    if root_dir is None:
        root_dir = ROOT

    stale = sorted(previous - current)
    for rel_path in stale:
        stale_path = generated_dir / rel_path
        if stale_path.is_file():
            stale_path.unlink()
            print(f'removed stale {stale_path.relative_to(root_dir)}')

    for root, dirs, files in os.walk(generated_dir, topdown=False):
        if Path(root) == generated_dir:
            continue
        if not dirs and not files:
            Path(root).rmdir()
