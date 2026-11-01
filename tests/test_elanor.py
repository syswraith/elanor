import shutil
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from jinja2 import Template

from elanor.builder import (
    build,
    build_folder_indexes,
    render_folder_list,
)
from elanor.frontmatter import (
    clear_frontmatter_warnings,
    first_paragraph,
    is_draft,
    meta_list,
    meta_value,
    parse_frontmatter,
)
from elanor.fs import (
    folder_pages,
    folder_title,
    has_notes,
    is_excluded_asset,
    prune,
    read_manifest,
    write_manifest,
)
from elanor.index import (
    LinkIndex,
    assign_page_dirs,
    build_link_index,
    resolve_wikilink,
)
from elanor.processors import (
    video_id,
)
from elanor.utils import (
    normalise_key,
    og_image_for,
    page_slug,
    rel_href,
    site_url_for,
    slugify,
    split_wikilink,
    strip_markdown_suffix,
    strip_page_suffix,
)


class TestUtils(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify('Hello World!'), 'hello-world')
        self.assertEqual(slugify('Foo - Part 1'), 'foo-part-1')
        self.assertEqual(slugify('café'), 'café')

    def test_page_slug(self):
        self.assertEqual(page_slug('My Title', 'filename'), 'my-title')
        self.assertEqual(page_slug('', 'my_file'), 'my-file')
        self.assertEqual(page_slug('---', ''), 'untitled')

    def test_normalise_key(self):
        self.assertEqual(normalise_key(''), '')
        self.assertEqual(normalise_key('.'), '')
        self.assertEqual(normalise_key('/'), '')
        self.assertEqual(normalise_key('./path/to/note.md'), 'path/to/note.md')
        self.assertEqual(normalise_key('path\\to\\note.md'), 'path/to/note.md')

    def test_rel_href(self):
        self.assertEqual(rel_href('a/b', 'a', trailing_slash=True), 'b/')
        self.assertEqual(rel_href('a', 'a/b', trailing_slash=True), '../')
        self.assertEqual(rel_href('a', 'a', trailing_slash=True), './')
        self.assertEqual(rel_href('a', 'a', trailing_slash=False), '')

    def test_split_wikilink(self):
        self.assertEqual(split_wikilink('target#heading|Label'), ('target', 'heading', 'Label'))
        self.assertEqual(split_wikilink('target'), ('target', '', ''))
        self.assertEqual(split_wikilink('#heading'), ('', 'heading', ''))

    def test_strip_markdown_and_page_suffix(self):
        self.assertEqual(strip_markdown_suffix('note.md'), 'note')
        self.assertEqual(strip_markdown_suffix('note.markdown'), 'note')
        self.assertEqual(strip_markdown_suffix('note.html'), 'note.html')

        self.assertEqual(strip_page_suffix('note.md'), 'note')
        self.assertEqual(strip_page_suffix('note.markdown'), 'note')
        self.assertEqual(strip_page_suffix('note.html'), 'note')
        self.assertEqual(strip_page_suffix('note.htm'), 'note')
        self.assertEqual(strip_page_suffix('note.png'), 'note.png')

    def test_site_url_and_og_image(self):
        config = {'site_url': 'https://example.com/site/', 'og_image': 'assets/icon.png'}
        self.assertEqual(site_url_for(config, 'blog/post'), 'https://example.com/site/blog/post/')
        self.assertEqual(site_url_for(config, ''), 'https://example.com/site/')
        self.assertEqual(og_image_for(config), 'https://example.com/site/assets/icon.png')


class TestFrontmatter(unittest.TestCase):
    def test_parse_frontmatter_valid(self):
        text = '---\ntitle: Hello\ntags:\n  - python\n  - ssg\n---\n# Content'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta['title'], 'Hello')
        self.assertEqual(meta['tags'], ['python', 'ssg'])
        self.assertEqual(body.strip(), '# Content')

    def test_parse_frontmatter_invalid_yaml(self):
        clear_frontmatter_warnings()
        text = '---\ntitle: [unclosed list\n---\n# Fallback'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body.strip(), '# Fallback')

    def test_is_draft(self):
        self.assertTrue(is_draft({'draft': True}))
        self.assertTrue(is_draft({'draft': 'true'}))
        self.assertTrue(is_draft({'draft': 'yes'}))
        self.assertTrue(is_draft({'draft': '1'}))
        self.assertTrue(is_draft({'publish': False}))
        self.assertTrue(is_draft({'publish': 'false'}))
        self.assertFalse(is_draft({'draft': False}))
        self.assertFalse(is_draft({'publish': True}))
        self.assertFalse(is_draft({}))

    def test_meta_value_and_list(self):
        meta = {'title': 'Test', 'count': 42, 'tags': ['a', 'b']}
        self.assertEqual(meta_value(meta, 'title'), 'Test')
        self.assertEqual(meta_value(meta, 'count'), '42')
        self.assertEqual(meta_value(meta, 'tags'), 'a b')
        self.assertEqual(meta_list(meta, 'tags'), ['a', 'b'])


class TestIndexAndWikilinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.content_dir = Path(self.tmp) / 'content'
        self.content_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_subfolder_index_md_assigned_properly(self):
        """Fix verification: subfolder index.md was previously skipped in assign_page_dirs."""
        sub_dir = self.content_dir / 'guides'
        sub_dir.mkdir()
        (sub_dir / 'index.md').write_text('# Guides Landing\n', encoding='utf-8')
        (sub_dir / 'setup.md').write_text('# Setup\n', encoding='utf-8')

        index = build_link_index(self.content_dir)
        assigned = assign_page_dirs(index, {}, self.content_dir)

        self.assertIn('guides/index', assigned)
        self.assertEqual(assigned['guides/index'], 'guides')
        self.assertEqual(index.pages['guides/index'], 'guides')

    def test_resolve_wikilink_root_asset_from_subfolder(self):
        """Fix verification: root assets resolved correctly from subfolder pages."""
        index = LinkIndex()
        index.add_asset('images/diagram.png')
        index.add_page('guides/install', 'guides/install')

        source_dir = Path('guides')
        out_dir = 'guides/install'

        href, label, target = resolve_wikilink(source_dir, 'images/diagram.png', index, out_dir)
        self.assertEqual(href, '../../images/diagram.png')
        self.assertEqual(label, 'diagram.png')
        self.assertIsNone(target)

    def test_resolve_wikilink_page_and_alias(self):
        index = LinkIndex()
        index.add_page('about', 'about')
        index.add_alias('whoami', 'about')

        href, label, target = resolve_wikilink(Path('.'), 'whoami', index, '')
        self.assertEqual(href, 'about/')
        self.assertEqual(label, 'whoami')

    def test_resolve_wikilink_with_html_suffix(self):
        """Fix verification: strip_page_suffix allows [[note.html]] to resolve."""
        index = LinkIndex()
        index.add_page('note', 'note')

        href, label, target = resolve_wikilink(Path('.'), 'note.html', index, '')
        self.assertEqual(href, 'note/')


class TestSecurityAndProcessors(unittest.TestCase):
    def test_xss_in_render_folder_list(self):
        """Fix verification: folder names and titles must be escaped."""
        items = [{'out_dir': 'test', 'title': '<script>alert("xss")</script>'}]
        subfolders = ['<img src=x onerror=alert(1)>']
        html = render_folder_list(items, subfolders, Path('.'))

        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;', html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)

    def test_folder_title_safety(self):
        self.assertEqual(folder_title(Path('.')), 'Notes')
        self.assertEqual(folder_title(Path('my-folder')), 'My folder')
        self.assertEqual(folder_title(Path('-')), 'Notes')
        self.assertEqual(folder_title(Path('_')), 'Notes')

    def test_video_id(self):
        self.assertEqual(video_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ'), 'dQw4w9WgXcQ')
        self.assertEqual(video_id('https://youtu.be/dQw4w9WgXcQ'), 'dQw4w9WgXcQ')
        self.assertEqual(video_id('https://www.youtube.com/shorts/dQw4w9WgXcQ'), 'dQw4w9WgXcQ')
        self.assertIsNone(video_id('https://evil.com/watch?v=dQw4w9WgXcQ'))
        self.assertIsNone(video_id('https://www.youtube.com/watch?v=<script>'))


class TestEndToEndBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.content_dir = Path(self.tmp) / 'content'
        self.generated_dir = Path(self.tmp) / 'generated'
        self.assets_dir = Path(self.tmp) / 'assets'
        self.content_dir.mkdir(parents=True)
        self.assets_dir.mkdir(parents=True)

        (self.content_dir / 'index.md').write_text('# Home\nWelcome [[About]]', encoding='utf-8')
        (self.content_dir / 'about.md').write_text('# About\n[[sub/guide.md]]', encoding='utf-8')
        (self.content_dir / 'sub').mkdir()
        (self.content_dir / 'sub' / 'guide.md').write_text('# Sub Guide\nContent', encoding='utf-8')
        (self.content_dir / 'sub' / 'index.md').write_text('# Sub Index\nLanding', encoding='utf-8')

        self.template = Template(
            '<html><head><title>{{ title }}</title></head><body>{{ content }}</body></html>'
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_build_includes_subfolder_index(self):
        config = {'theme': 'test'}
        written, links, skipped, folder_indexes = build(
            config, self.template, self.content_dir, self.generated_dir, self.assets_dir
        )

        self.assertIn('index.html', written)
        self.assertIn('about/index.html', written)
        self.assertIn('sub/guide/index.html', written)
        # Verify sub/index.html was built!
        self.assertIn('sub/index.html', written)
        self.assertTrue((self.generated_dir / 'sub' / 'index.html').is_file())


if __name__ == '__main__':
    unittest.main()
