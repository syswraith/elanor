import os, json, markdown
from pathlib import Path
from assets import config as config_module
from jinja2 import Environment, FileSystemLoader

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

        html_body = markdown.markdown(
            text,
            extensions=[
                'fenced_code',
                'codehilite',
                'markdown.extensions.tables',
                'markdown.extensions.meta',
                'markdown.extensions.wikilinks'
            ],
            extension_configs={
                'markdown.extensions.wikilinks': {
                    'base_url': '',
                    'end_url': '',
                    'build_url': wikilink_url_builder
                }
            }
        )

        rendered = template.render(theme=config['theme'], content=html_body)

        with open(f"./generated/{file[:-3]}.html", "w", encoding="utf-8") as f:
            f.write(rendered)

