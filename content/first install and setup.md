---
title: Elanor
description: Elanor is a minimalistic static site generator for Markdown files. Written in Python.
author: syswraith
keywords: elanor,syswraith,github,static site generator,python,python3,classless,css,minimal,installation,setup
---

![Elanor icon](https://github.com/syswraith/elanor/blob/main/assets/icon.png?raw=true)


# Installation

1. Clone the github repo and `cd` to it
    ```sh
    git clone https://github.com/syswraith/elanor
    cd elanor
    ```
2. Make a virtual environment and activate it
    ```sh
    python3 -m venv venv && source ./venv/bin/activate
    ```
3. Install the required dependencies
    ```sh
    pip install -r requirements.txt
    ```


# Setup

Your markdown files go inside the `content` directory. You may use nested directories to store them. 
Also note that any wikilinks or image links that you include should be **relative** to the current directory.

Once you're done, run `python3 main.py`. This should generate all the relevent HTML file structure in the `generated` directory.
