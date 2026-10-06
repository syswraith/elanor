![Elanor icon](https://github.com/syswraith/elanor/blob/main/assets/icon.png)

```
Elanor is a minimalistic static site generator built for the Markdown I use.
Written in Python, it was conceived as a static site generator that uses
classless CSS to style content.

Requires Python 3.10+ and Node.js. Node is required by markdown-katex, which
renders math through the KaTeX CLI at build time.

Supports basic markdown, syntax highlighting, KaTeX, frontmatter, Obsidian-style
wikilinks, task lists, folder indexes and YouTube embeds. Embeds are written as
a link labelled `embed` on a line of its own:

    [embed](https://www.youtube.com/watch?v=dQw4w9WgXcQ)

The video id is read from the URL, so nothing is fetched at build time and builds
work offline. YouTube is the only supported provider; any other target is left as
a normal link.

For more documentation and demo, check the deployed version at 
https://syswraith.com/elanor

Elanor was named after Elanor Gardner- the first daughter of Samwise Gamgee,
to whom he gave the Red Book of Westmarch before he sailed away to Valinor.
```

```sh
python3 -m venv venv && source ./venv/bin/activate
pip install -r requirements.txt
python3 main.py
```
