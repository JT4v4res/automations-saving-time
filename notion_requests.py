import requests as reqs
import json
import time

emoji_list = ["✨", "💎", "🐞", "💿", "🦽"]

part_list = ["Stardust Crusaders", "Diamond is unbreakable", "Golden Wind", "Stone Ocean", "Steel Ball Run"]

headers = {'Authorization': 'Bearer your_secret_here',
           'Notion-Version': '2022-06-28',
           'Content-Type': 'application/json',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                         'Chrome/107.0.0.0 Safari/537.36'
           }

posted = []
images_posted = []

with open(f'./stands.json', 'r+') as infile:
    json_file = infile.read()

    json_dict = json.loads(json_file)

    c = 0
    for key, value in json_dict.items():
        part = part_list[c]

        # t = 0
        for key2, value2 in json_dict[key].items():
            if key2 not in posted:
                posted.append(key2)

                payload = {
                    "parent": {"database_id": "your_database_id"},
                    "cover": {
                        "type": "external",
                        "external": {
                            "url": f"{value2['page_cover']}",
                        },
                    },
                    "icon": {
                        "emoji": f"{emoji_list[c]}"
                    },
                    "children": [
                        {
                            "object": "block",
                            "type": "heading_2",
                            "heading_2": {
                                "rich_text": [{"type": "text", "text": {"content": f"{key + key2}"}}]
                            }
                        },
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": f"{value2['text']}",
                                        }
                                    }
                                ]
                            },
                        }, {
                            "object": "block",
                            "type": "image",
                            "image": {
                                "type": "external",
                                "external": {
                                    "url": f"{value2['page_cover'] if value2['page_cover'] not in images_posted else ''}"
                                }
                            },
                        }
                    ],
                    "properties": {
                        "Name": {
                            "title": [
                                {
                                    "text": {
                                        "content": f"{part} - {key2}"
                                    }
                                }
                            ]
                        }
                    }
                }

                r = reqs.post('https://api.notion.com/v1/pages', headers=headers, data=json.dumps(payload))

                print(r.text)

                print(f"posted {key2}")

                images_posted.append(value2['page_cover'])

        c += 1
