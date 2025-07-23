import os
import json
import markdown
from pathlib import Path
from assets import config as config_module


def wikilink_url_builder(label, base, end):
    if label.endswith('.md'):
        label = label[:-3] + '.html'
    else:
        label = label + '.html'
    return base + label + end

config_file_path = Path("./assets/config.json")

if config_file_path.is_file(): pass
else: config_module.config()

with open(config_file_path, 'r') as config_file:
    config = json.load(config_file)

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

        html = f'''<html>
                <head>
                  <meta name="viewport" content="width=device-width, initial-scale=1">
                  <link rel="stylesheet" href="pygments.css" type="text/css">
                  <link rel="stylesheet" href="{config['theme']}" type="text/css">
                </head>
                <body>
                {html_body}
                </body>
                </html>'''

        with open(f"./generated/{file[:-3]}.html", "w", encoding="utf-8") as f:
            f.write(html)

