import requests as reqs
import json
from bs4 import BeautifulSoup
import time

emoji_list = ["✨☄️", "💎🔨❌", "☀️⚖️🐞🐍", "🐬💿🔗⏰", "🏇🥏🦽"]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                         'Chrome/107.0.0.0 Safari/537.36'
           }

## Extraindo os links

page = reqs.get('https://jojowiki.com/List_of_Stands', headers=headers)

soup_links = BeautifulSoup(page.text, 'html.parser')

divs = soup_links.find_all('div', class_='diamond2')

visited = []

content_array = {}

part = 0

start = time.time()
for element in divs:
    if part > 4:
        break

    content_array[emoji_list[part]] = {}

    for a in element.find_all('a'):
        if a['href'] not in visited:
            print(f'Extracting content for {a['href']}')
            contents_page = reqs.get(f"https://jojowiki.com{a['href']}")


            soup = BeautifulSoup(contents_page.text, 'html.parser')

            stand_description = soup.find_all('div', class_='mw-parser-output')
            page_headers = soup.find('h1')
            paragrafos = soup.find_all('p', class_=False)
            img = soup.find('a', class_='image')

            if img is not None:
                img = img.find_next('a', class_='image')
                page_cover = img.img['src']

            c = 0
            text = ''
            for p in paragrafos:
                text += p.text

                c += 1

                if c >= 2:
                    break

            content_array[emoji_list[part]][page_headers.text] = {"text": text, "page_cover": page_cover if page_cover is not None else ''}
            visited = a['href']

    part += 1

print(f"Total time for extraction: {time.time() - start}")

json_file = json.dumps(content_array)

with open(f'./stands.json', 'w+') as outfile:
    outfile.write(json_file)
