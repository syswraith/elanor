import json


configs = {}

with open('assets/themes.json', 'r') as themes_file:
    themes = json.load(themes_file)


print('Choose a theme: ')
for theme in themes.keys():
    print(f'{theme}: {themes[theme][0]}')

theme_choice = input("Your choice: ")

if theme_choice in themes.keys():
    configs["theme"] = themes[theme][1]

with open('config.json', 'w') as config_file:
    config_file.write(json.dumps(configs))
    
