import json

def config():
    with open('./assets/themes.json') as f: themes = json.load(f)

    print('Choose a theme:')
    for k in sorted(themes, key=int): print(f'{k}: {themes[k][0]}')

    choice = input('Your choice: ')
    if choice in themes:
        with open('./assets/config.json', 'w') as f:
            f.write(json.dumps({"theme": themes[choice][1]}))

