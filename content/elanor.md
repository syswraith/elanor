# Elanor: A Minimal Static Site Generator

Elanor is a blazing-fast, Python-powered static site generator built with simplicity and extensibility in mind. Designed to stay out of your way and just **generate**.

## 🚀 Features

- Markdown to HTML conversion  
- Clean URL generation (`about.md` → `about/index.html`)  
- Lightweight config with JSON  
- Custom templating with Jinja2  
- No JavaScript required  
- Built for GitHub Pages  

## 📸 Preview

![Elanor Preview](https://github.com/syswraith/elanor/blob/main/assets/icon.png?raw=true)

## 🛠 How It Works

1. Place your `.md` files in a content folder.
2. Configure base URL and theme settings in `assets/config.json`.
3. Run the build script:  
   ```bash
   python generate.py
   ```
4. Generated HTML will be output to the `generated/` directory.

## 🔧 Configuration

```json
{
  "base_url": "/",
  "theme": "bahunya",
  "title": "My Static Site"
}
```

## 📂 Folder Structure

```
elanor/
├── assets/
│   ├── config.json
│   └── themes/
├── content/
│   └── index.md
├── templates/
│   └── base.html
├── generate.py
└── generated/
```

## 🧠 Why Elanor?

| Feature         | Elanor               | Traditional SSGs       |
|----------------|----------------------|-------------------------|
| Config Format   | JSON                 | YAML/TOML               |
| Theme Loading   | CDN-based CSS        | Complex pipelines       |
| Learning Curve  | Low                  | Moderate/High           |
| Templating      | Jinja2 (Pythonic)    | Liquid/Custom DSL       |

## 🌐 Deploy

To GitHub Pages:
```bash
ghp-import -n -p -f generated
```

## ⚙️ Dependencies

- Python 3.7+  
- `markdown`  
- `jinja2`  

Install via:
```bash
pip install -r requirements.txt
```

## 📄 License

MIT. Use freely and contribute back if you break something and fix it :)

## 🔗 Links

- [GitHub Repository](https://github.com/syswraith/elanor)
- [Live Demo](https://syswraith.github.io/elanor)

---

> Made with Python. Styled with taste. Rendered with Elanor.

