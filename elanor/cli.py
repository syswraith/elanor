import json
import sys

from jinja2 import Environment, FileSystemLoader

from assets import config as config_module
from elanor.builder import (
    build,
    report_broken_links,
    report_skipped,
)
from elanor.constants import (
    ASSETS_DIR,
    CONFIG_PATH,
    GENERATED_DIR,
    ROOT,
)
from elanor.frontmatter import clear_frontmatter_warnings
from elanor.fs import (
    prune,
    read_manifest,
    write_manifest,
)


def read_config(config_path=None, assets_dir=None):
    if config_path is None:
        config_path = CONFIG_PATH
    if assets_dir is None:
        assets_dir = ASSETS_DIR

    if not config_path.is_file():
        config_module.config(assets_dir)

    try:
        with open(config_path, encoding='utf-8') as config_file:
            config = json.load(config_file)
    except OSError as exc:
        sys.exit(f'error: could not read {config_path}: {exc}')
    except json.JSONDecodeError as exc:
        sys.exit(f'error: {config_path} is not valid JSON: {exc}')

    if not isinstance(config, dict):
        sys.exit(f'error: {config_path} must contain a JSON object')

    theme = config.get('theme')
    if not isinstance(theme, str) or not theme.strip():
        sys.exit(f'error: {config_path} is missing a "theme" entry')

    return config


def main():
    clear_frontmatter_warnings()
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
