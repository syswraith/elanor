import re
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent.parent
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
PAGE_SUFFIXES = MARKDOWN_SUFFIXES + ('.html', '.htm')

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

FRONTMATTER_BLOCK = re.compile(
    r'\A---[ \t]*\r?\n.*?^---[ \t]*(?:\r?\n|\Z)',
    re.DOTALL | re.MULTILINE,
)
DESCRIPTION_LIMIT = 160
DEFAULT_LANG = 'en'

MARKDOWN_EXTENSIONS = [
    'fenced_code',
    'codehilite',
    'markdown.extensions.tables',
    'markdown.extensions.toc',
]
