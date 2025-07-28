import os, json, markdown
from pathlib import Path
from assets import config as config_module
from jinja2 import Environment, FileSystemLoader
from markdown_katex import KatexExtension

def wikilink_url_builder(label, base, end):
    if label.endswith('.md'):
        label = label[:-3] + '.html'
    else:
        label = label + '.html'
    return base + label + end

config_file_path = Path("./assets/config.json")
if not config_file_path.is_file():
    config_module.config()

with open(config_file_path, 'r') as config_file:
    config = json.load(config_file)

env = Environment(loader=FileSystemLoader("assets"))
template = env.get_template("template.html")

for file in os.listdir('./content'):
    if file.endswith(".md"):
        with open(f"./content/{file}", "r", encoding="utf-8") as input_file:
            text = input_file.read()

        md = markdown.Markdown(
            extensions=[
                'fenced_code',
                'codehilite',
                'markdown.extensions.tables',
                'markdown.extensions.meta',
                'markdown.extensions.wikilinks',
                KatexExtension()
            ],
            extension_configs={
                'markdown.extensions.wikilinks': {
                    'base_url': '',
                    'end_url': '',
                    'build_url': wikilink_url_builder
                }
            }
        )

        html_body = md.convert(text)
        meta = md.Meta

        title = meta.get('title', [''])[0]
        author = meta.get('author', [''])[0]
        keywords = meta.get('keywords', [''])[0]
        description = meta.get('description', [''])[0]

        rendered = template.render(
            theme = config['theme'],
            content = html_body,
            title = title,
            author = author,
            description = description,
            keywords = keywords,
            og_image = "https://github.com/syswraith/elanor/blob/main/assets/icon.png?raw=true"
        )

        with open(f"./generated/{file[:-3]}.html", "w", encoding="utf-8") as f:
            f.write(rendered)

