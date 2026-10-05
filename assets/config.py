import json
import os
import sys
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent
THEMES_FILE = ASSETS_DIR / 'themes.json'
CONFIG_FILE = ASSETS_DIR / 'config.json'

THEME_CHOICES = [
    ('site_url', 'Site URL (used for canonical/Open Graph links, blank to skip)'),
    ('og_image', 'Open Graph image URL or site-relative path (blank to skip)'),
]


def die(message):
    print(f'error: {message}', file=sys.stderr)
    raise SystemExit(1)


def load_themes():
    try:
        with open(THEMES_FILE, encoding='utf-8') as f:
            themes = json.load(f)
    except OSError as exc:
        die(f'could not read {THEMES_FILE}: {exc}')
    except json.JSONDecodeError as exc:
        die(f'{THEMES_FILE} is not valid JSON: {exc}')

    if not isinstance(themes, dict) or not themes:
        die(f'{THEMES_FILE} must be a non-empty object of id -> [name, url]')

    return themes


def prompt_theme(themes):
    env_choice = os.environ.get('ELANOR_THEME')
    if env_choice:
        if env_choice not in themes:
            die(
                f'ELANOR_THEME={env_choice!r} is not in {THEMES_FILE.name} '
                f'(valid: {", ".join(sorted(themes, key=int))})'
            )
        return env_choice

    print('Choose a theme:')
    for key in sorted(themes, key=int):
        print(f'  {key}: {themes[key][0]}')

    valid = ', '.join(sorted(themes, key=int))
    while True:
        try:
            choice = input('Your choice: ').strip()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            die('no theme chosen. Set ELANOR_THEME to build non-interactively.')

        if choice in themes:
            return choice

        print(f'  "{choice}" is not one of: {valid}', file=sys.stderr)


def prompt_value(label):
    try:
        return input(f'{label}: ').strip()
    except EOFError:
        return ''


def config(assets_dir=None):
    global ASSETS_DIR, THEMES_FILE, CONFIG_FILE

    if assets_dir is not None:
        assets_dir = Path(assets_dir)
        THEMES_FILE = assets_dir / THEMES_FILE.name
        CONFIG_FILE = assets_dir / CONFIG_FILE.name

    themes = load_themes()
    settings = {'theme': themes[prompt_theme(themes)][1]}

    if os.environ.get('ELANOR_THEME'):
        # Fully non-interactive: take the site defaults and let the user edit
        # assets/config.json by hand if they want canonical/OG overrides.
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
            f.write('\n')
        print(f'Wrote {CONFIG_FILE}')
        return settings

    for key, label in THEME_CHOICES:
        value = prompt_value(label)
        if value:
            settings[key] = value

    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
            f.write('\n')
    except OSError as exc:
        die(f'could not write {CONFIG_FILE}: {exc}')

    print(f'Wrote {CONFIG_FILE}')
    return settings


if __name__ == '__main__':
    config()
