import os, json, markdown, re, shutil
from pathlib import Path
from assets import config as config_module
from jinja2 import Environment, FileSystemLoader
from markdown_katex import KatexExtension

def wikilink_replacer(text):
    def replacer(match):
        target = match.group(1)
        href = target + ".html"
        display = Path(target).stem
        return f'<a href="{href}">{display}</a>'
    return re.sub(r'\[\[(.*?)\]\]', replacer, text)

def normalize_wikilinks(text):
    text = re.sub(r'\[\[\./(.*?)\.md\]\]', r'[[\1]]', text)
    text = re.sub(r'\[\[(.*?)\.md\]\]', r'[[\1]]', text)
    return text

config_file_path = Path("./assets/config.json")
if not config_file_path.is_file():
    config_module.config()

with open(config_file_path, 'r') as config_file:
    config = json.load(config_file)

env = Environment(loader=FileSystemLoader("assets"))
template = env.get_template("template.html")

for root, _, files in os.walk('./content'):
    for file in files:
        if file.endswith(".md"):
            abs_path = Path(root) / file
            rel_path = abs_path.relative_to('./content')
            out_path = Path('./generated') / rel_path.with_suffix('.html')

            with open(abs_path, "r", encoding="utf-8") as input_file:
                text = input_file.read()

            text = normalize_wikilinks(text)
            text = wikilink_replacer(text)

            md = markdown.Markdown(
                extensions=[
                    'fenced_code',
                    'codehilite',
                    'markdown.extensions.tables',
                    'markdown.extensions.meta',
                    KatexExtension()
                ]
            )

            html_body = md.convert(text)
            meta = getattr(md, 'Meta', {})

            title = meta.get('title', [''])[0]
            author = meta.get('author', [''])[0]
            keywords = meta.get('keywords', [''])[0]
            description = meta.get('description', [''])[0]

            rendered = template.render(
                theme=config['theme'],
                content=html_body,
                title=title,
                author=author,
                description=description,
                keywords=keywords,
                og_image="https://github.com/syswraith/elanor/blob/main/assets/icon.png?raw=true"
            )

            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(rendered)

for root, _, files in os.walk('./content'):
    for file in files:
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            src_path = Path(root) / file
            rel_path = src_path.relative_to('./content')
            dest_path = Path('./generated') / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)


